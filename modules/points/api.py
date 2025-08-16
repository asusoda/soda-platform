import csv
from flask import Flask, jsonify, request, Blueprint
from sqlalchemy.orm import Session
from modules.auth.decoraters import auth_required
from modules.utils.db import DBConnect
from modules.points.models import User, Points
from shared import db_connect, tokenManger
from io import StringIO
from sqlalchemy import func
import threading

points_blueprint = Blueprint(
    "points", __name__, template_folder=None, static_folder=None
)

def get_or_create_user(discord_id, organization_id, username=None):
    """
    Get existing user or create new user and add them to the organization.
    This is called when a guild member accesses member endpoints.
    """
    db = next(db_connect.get_db())
    try:
        from modules.points.models import UserOrganizationMembership
        
        # Check if user already exists by discord_id
        user = db.query(User).filter_by(discord_id=discord_id).first()
        
        if user:
            # Check if user is already a member of this organization
            membership = db.query(UserOrganizationMembership).filter_by(
                user_id=user.id,
                organization_id=organization_id,
                is_active=True
            ).first()
            
            if not membership:
                # Add user to this organization
                new_membership = UserOrganizationMembership(
                    user_id=user.id,
                    organization_id=organization_id
                )
                db.add(new_membership)
                db.commit()
                print(f"✅ [DEBUG] Added existing user {user.id} to organization {organization_id}")
            
            return user
        
        # Create new user with discord_id
        import uuid
        new_user = User(
            discord_id=discord_id,
            username=username or f"User_{discord_id}",
            name=username or f"User_{discord_id}",
            uuid=str(uuid.uuid4()),
            asu_id="N/A",
            academic_standing="N/A",
            major="N/A"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Add membership to organization
        membership = UserOrganizationMembership(
            user_id=new_user.id,
            organization_id=organization_id
        )
        db.add(membership)
        db.commit()
        
        print(f"✅ [DEBUG] Created new user {new_user.id} for discord_id {discord_id} in org {organization_id}")
        return new_user
        
    except Exception as e:
        print(f"❌ [DEBUG] Error creating user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def link_or_create_user(organization_id, user_data, discord_id=None):
    """
    Link existing user account or create new user for member store access.
    Handles account linking based on ASU ID, email, or username.
    """
    db = next(db_connect.get_db())
    try:
        from modules.points.models import UserOrganizationMembership
        existing_user = None
        
        # Try to find existing user by ASU ID first (most reliable)
        if user_data.get('asu_id') and user_data['asu_id'] != 'N/A':
            existing_user = db.query(User).filter_by(asu_id=user_data['asu_id']).first()
        
        # If not found by ASU ID, try email
        if not existing_user and user_data.get('email'):
            existing_user = db.query(User).filter_by(email=user_data['email']).first()
        
        # If not found by email, try username
        if not existing_user and user_data.get('username'):
            existing_user = db.query(User).filter_by(username=user_data['username']).first()
        
        if existing_user:
            # Link discord_id to existing account if provided and not already linked
            if discord_id and not existing_user.discord_id:
                existing_user.discord_id = discord_id
                db.commit()
                print(f"✅ [DEBUG] Linked discord_id {discord_id} to existing user {existing_user.id}")
            
            # Check if user is already a member of this organization
            membership = db.query(UserOrganizationMembership).filter_by(
                user_id=existing_user.id,
                organization_id=organization_id,
                is_active=True
            ).first()
            
            if not membership:
                # Add user to this organization
                new_membership = UserOrganizationMembership(
                    user_id=existing_user.id,
                    organization_id=organization_id
                )
                db.add(new_membership)
                db.commit()
                print(f"✅ [DEBUG] Added existing user {existing_user.id} to organization {organization_id}")
            
            return existing_user
        
        # Create new user if no existing account found
        import uuid
        new_user = User(
            discord_id=discord_id,
            username=user_data.get('username', f"User_{discord_id or 'unknown'}"),
            name=user_data.get('name', user_data.get('username', 'Unknown')),
            email=user_data.get('email'),
            asu_id=user_data.get('asu_id', 'N/A'),
            academic_standing=user_data.get('academic_standing', 'N/A'),
            major=user_data.get('major', 'N/A'),
            uuid=str(uuid.uuid4())
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Add membership to organization
        membership = UserOrganizationMembership(
            user_id=new_user.id,
            organization_id=organization_id
        )
        db.add(membership)
        db.commit()
        
        print(f"✅ [DEBUG] Created new user {new_user.id} for org {organization_id}")
        return new_user
        
    except Exception as e:
        print(f"❌ [DEBUG] Error linking/creating user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


@points_blueprint.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Points"}), 200

@points_blueprint.route("/member_login", methods=["POST"])
def member_login():
    """
    Member login endpoint for public store access.
    Links or creates user account based on provided information.
    """
    data = request.json
    
    # Validate required fields
    required_fields = ['organization_prefix']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    
    # Get organization
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        organization = db.query(Organization).filter_by(
            prefix=data['organization_prefix'],
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Extract user data
        user_data = {
            'name': data.get('name'),
            'username': data.get('username'),
            'email': data.get('email'),
            'asu_id': data.get('asu_id'),
            'academic_standing': data.get('academic_standing'),
            'major': data.get('major')
        }
        
        # Get discord_id from session if available
        from flask import session
        discord_id = session.get('discord_id')
        
        # Link or create user
        user = link_or_create_user(organization.id, user_data, discord_id)
        
        if not user:
            return jsonify({"error": "Failed to create or link user account"}), 500
        
        # Store user info in session for member access
        session['member_user_id'] = user.id
        session['member_org_id'] = organization.id
        
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "asu_id": user.asu_id,
                "discord_linked": bool(user.discord_id)
            },
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "prefix": organization.prefix
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@points_blueprint.route("/member_profile", methods=["GET"])
def get_member_profile():
    """
    Get member profile with organization memberships and points.
    """
    organization_prefix = request.args.get('organization_prefix')
    if not organization_prefix:
        return jsonify({"error": "organization_prefix is required"}), 400
    
    # Get member user from session
    from flask import session
    member_user_id = session.get('member_user_id')
    member_org_id = session.get('member_org_id')
    
    if not member_user_id:
        return jsonify({"error": "Member not logged in"}), 401
    
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        from modules.points.models import UserOrganizationMembership
        
        # Get organization
        organization = db.query(Organization).filter_by(
            prefix=organization_prefix,
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Get user
        user = db.query(User).filter_by(id=member_user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user's organization memberships
        memberships = db.query(UserOrganizationMembership).filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        # Get organizations user is a member of
        org_data = []
        total_points_all_orgs = 0
        current_org_points = 0
        
        for membership in memberships:
            org = db.query(Organization).filter_by(id=membership.organization_id).first()
            if org:
                # Get points for this organization
                org_points = db.query(func.sum(Points.points)).filter_by(
                    user_id=user.id,
                    organization_id=org.id
                ).scalar() or 0
                
                org_data.append({
                    'id': org.id,
                    'name': org.name,
                    'prefix': org.prefix,
                    'description': org.description,
                    'points': org_points,
                    'is_current': org.id == organization.id
                })
                
                total_points_all_orgs += org_points
                if org.id == organization.id:
                    current_org_points = org_points
        
        return jsonify({
            "user": {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "asu_id": user.asu_id,
                "academic_standing": user.academic_standing,
                "major": user.major,
                "discord_linked": bool(user.discord_id),
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "current_organization": {
                "id": organization.id,
                "name": organization.name,
                "prefix": organization.prefix,
                "points": current_org_points
            },
            "organizations": org_data,
            "total_points_all_orgs": total_points_all_orgs
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@points_blueprint.route("/add_user", methods=["POST"])
@auth_required
def add_user():
    data = request.json
    db = next(db_connect.get_db())
    try:
        # Validate required fields
        if not data.get("organization_id"):
            return jsonify({"error": "organization_id is required"}), 400
            
        # Use the existing link_or_create_user function for multi-org support
        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'name': data.get('name'),
            'asu_id': data.get('asu_id', 'N/A'),
            'academic_standing': data.get('academic_standing', 'N/A'),
            'major': data.get('major', 'N/A')
        }
        
        db_user = link_or_create_user(
            data["organization_id"], 
            user_data, 
            data.get("discord_id")
        )
        
        if not db_user:
            return jsonify({"error": "Failed to create user"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
    return jsonify(
        {
            "id": db_user.id,
            "uuid": db_user.uuid,
            "name": db_user.name,
            "email": db_user.email,
            "discord_id": db_user.discord_id,
            "username": db_user.username,
        }
    ), 201


@points_blueprint.route("/add_points", methods=["POST"])
@auth_required
def add_points():
    data = request.json
    db = next(db_connect.get_db())
    try:
        # Validate required fields
        if not data.get("organization_id"):
            return jsonify({"error": "organization_id is required"}), 400
        
        # Check if the user exists by discord_id
        user = db.query(User).filter_by(discord_id=data["user_discord_id"]).first()
        if not user:
            return jsonify({"error": "User does not exist"}), 404

        # Add points to the user
        point = Points(
            points=data["points"],
            user_id=user.id,
            organization_id=data["organization_id"],
        )
        db.add(point)
        db.commit()
        db.refresh(point)
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
    return jsonify(
        {
            "id": point.id,
            "points": point.points,
            "user_id": point.user_id,
            "organization_id": point.organization_id,
            "last_updated": point.last_updated.isoformat() if point.last_updated else None,
        }
    ), 201


@points_blueprint.route("/get_users", methods=["GET"])
@auth_required
def get_users():
    db = next(db_connect.get_db())
    try:
        users = db.query(User).all()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
    return jsonify(
        [
            {
                "uuid": user.uuid,
                "name": user.name,
                "email": user.email,
                "academic_standing": user.academic_standing,
                "asu_id": user.asu_id,
                "major": user.major,
            }
            for user in users
        ]
    ), 200



@points_blueprint.route("/get_points", methods=["GET"])
@auth_required
def get_points():
    db = next(db_connect.get_db())
    try:
        # Get organization_id from query parameters
        organization_id = request.args.get('organization_id')
        
        if not organization_id:
            return jsonify({"error": "organization_id parameter is required"}), 400
        
        # Filter points by organization
        points = db.query(Points).filter_by(organization_id=organization_id).all()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
    return jsonify(
        [
            {
                "id": point.id,
                "points": point.points,
                "last_updated": point.last_updated.isoformat() if point.last_updated else None,
                "user_id": point.user_id,
                "organization_id": point.organization_id,
            }
            for point in points
        ]
    ), 200



@points_blueprint.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    token = None
    show_email = False  # Default to showing UUID unless authentication succeeds

    # Extract token from Authorization header
    if "Authorization" in request.headers:
        token = request.headers["Authorization"].split(" ")[1]  # Get the token part

    # If the token is present, validate it
    if token:
        try:
            # Check if the token is valid and not expired
            if tokenManger.is_token_valid(token) and not tokenManger.is_token_expired(token):
                show_email = True  # If valid, set to show email
            elif tokenManger.is_token_expired(token):
                return jsonify({"message": "Token is expired!"}), 403  # Expired token
        except Exception as e:
            return jsonify({"message": str(e)}), 401  # Token is invalid or some error occurred

    # Get organization_id from query parameters
    organization_id = request.args.get('organization_id')
    if not organization_id:
        return jsonify({"error": "organization_id parameter is required"}), 400

    db = next(db_connect.get_db())
    try:
        leaderboard = (
            db.query(
                User.name,
                User.email,  # Include both email and UUID in the query
                User.uuid,
                func.coalesce(func.sum(Points.points), 0).label("total_points"),
            )
            .outerjoin(Points)
            .filter(Points.organization_id == organization_id)  # Filter by organization
            .group_by(User.email, User.uuid, User.name)  # Group by email and UUID for uniqueness
            .order_by(
                func.sum(Points.points).desc(), User.name.asc()
            )
            .all()
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

    # Return the result based on whether the token is valid or not
    return jsonify(
        [
            {
                "name": name,
                "identifier": email if show_email else uuid,  # Show email if token is valid, else UUID
                "points": total_points
            }
            for name, email, uuid, total_points in leaderboard
        ]
    ), 200


@points_blueprint.route("/uploadEventCSV", methods=["POST"])
@auth_required
def upload_event_csv():
    if 'file' not in request.files or 'event_name' not in request.form or 'event_points' not in request.form:
        return jsonify({"error": "Missing required fields"}), 400

    file = request.files['file']
    event_name = request.form['event_name']
    event_points = int(request.form['event_points'])

    # Check file extension
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400

    # Read the file content
    file_content = file.stream.read().decode('utf-8')

    # Start a new thread to process the CSV in the background
    background_thread = threading.Thread(target=process_csv_in_background, args=(file_content, event_name, event_points))
    background_thread.start()

    # Return an immediate response while the CSV is being processed
    return jsonify({"message": "File is being processed in the background."}), 202


@points_blueprint.route("/getUserPoints", methods=["GET"])
@auth_required
def get_user_points():
    discord_id = request.args.get('discord_id')
    organization_id = request.args.get('organization_id')
    
    if not discord_id:
        return jsonify({"error": "discord_id parameter is missing"}), 400
    
    if not organization_id:
        return jsonify({"error": "organization_id parameter is missing"}), 400

    db = next(db_connect.get_db())
    try:
        # Check if the user exists
        user = db.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            return jsonify({"error": "User does not exist"}), 404  # Not Found status code

        # Query all points earned by the user in the specific organization
        points_records = db.query(Points).filter_by(
            user_id=user.id, 
            organization_id=organization_id
        ).all()
        
        if not points_records:
            return jsonify({"message": "No points earned by this user in this organization"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

    return jsonify(
        [
            {
                "id": record.id,
                "points": record.points,
                "organization_id": record.organization_id,
                "last_updated": record.last_updated.isoformat() if record.last_updated else None
            }
            for record in points_records
        ]
    ), 200


@points_blueprint.route("/getUserTotalPoints", methods=["GET"])
@auth_required
def get_user_total_points():
    discord_id = request.args.get('discord_id')
    organization_id = request.args.get('organization_id')
    
    if not discord_id:
        return jsonify({"error": "discord_id parameter is missing"}), 400
    
    if not organization_id:
        return jsonify({"error": "organization_id parameter is missing"}), 400

    db = next(db_connect.get_db())
    try:
        # Check if the user exists
        user = db.query(User).filter_by(discord_id=discord_id).first()
        if not user:
            return jsonify({"error": "User does not exist"}), 404

        # Calculate total points for the user in the specific organization
        total_points = db.query(func.sum(Points.points)).filter_by(
            user_id=user.id, 
            organization_id=organization_id
        ).scalar() or 0.0

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

    return jsonify({
        "user_id": user.id,
        "discord_id": user.discord_id,
        "username": user.username,
        "organization_id": organization_id,
        "total_points": total_points
    }), 200

    
@points_blueprint.route("/assignPoints", methods=["POST"])
@points_blueprint.route("/assign_points", methods=["POST"])  # Add alias for frontend compatibility
@auth_required
def assign_points():
    data = request.json
    db = next(db_connect.get_db())
    try:
        # Validate required fields
        if not data.get("user_identifier"):
            return jsonify({"error": "user_identifier is required"}), 400
        if not data.get("organization_id"):
            return jsonify({"error": "organization_id is required"}), 400

        user_identifier = data["user_identifier"]
        organization_id = data["organization_id"]
        
        # Try to find user by email first (since it's more common)
        user = db.query(User).filter_by(email=user_identifier).first()
        
        # If not found by email, try UUID
        if not user:
            user = db.query(User).filter_by(uuid=user_identifier).first()
        
        # If not found by UUID, try username
        if not user:
            user = db.query(User).filter_by(username=user_identifier).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user is a member of this organization
        from modules.points.models import UserOrganizationMembership
        membership = db.query(UserOrganizationMembership).filter_by(
            user_id=user.id,
            organization_id=organization_id,
            is_active=True
        ).first()
        
        if not membership:
            return jsonify({"error": "User is not a member of this organization"}), 400

        # Add points to the user
        point = Points(
            points=data["points"],
            user_id=user.id,
            organization_id=organization_id
        )
        db.add(point)
        db.commit()
        db.refresh(point)
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
    return jsonify(
        {
            "id": point.id,
            "points": point.points,
            "user_id": point.user_id,
            "organization_id": point.organization_id,
            "last_updated": point.last_updated.isoformat() if point.last_updated else None,
        }
    ), 201




@points_blueprint.route("/delete_points", methods=["DELETE"])
@auth_required
def delete_points_by_event():
    data = request.json
    if not data or "user_email" not in data or "event" not in data:
        return jsonify({"error": "user_email and event are required"}), 400

    db = next(db_connect.get_db())
    try:
        # Find the points entry by user email and event name
        points_entry = db.query(Points).filter_by(
            user_email=data["user_email"],
            event=data["event"]
        ).first()
        
        if not points_entry:
            return jsonify({"error": "Points entry not found"}), 404
            
        # Delete the points entry
        db.delete(points_entry)
        db.commit()
        
        return jsonify({
            "message": "Points deleted successfully",
            "deleted_points": {
                "points": points_entry.points,
                "event": points_entry.event,
                "timestamp": points_entry.timestamp,
                "awarded_by_officer": points_entry.awarded_by_officer,
                "user_email": points_entry.user_email
            }
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


def process_csv_in_background(file_content, event_name, event_points):
    csv_file = StringIO(file_content)

    # Skip the first 5 lines and read the content from the 6th line
    for _ in range(5):
        next(csv_file)

    # Now read the CSV starting from the 6th row which contains the headers
    csv_reader = csv.DictReader(csv_file)

    db = next(db_connect.get_db())
    success_count = 0
    errors = []

    try:
        for row in csv_reader:
            email = row.get('Campus Email')
            name = row.get('First Name') + ' ' + row.get('Last Name')
            asu_id = 'N/A'
            marked_by = row.get('Marked By')

            if not email or not name or not marked_by:
                errors.append(f"Missing required fields in row: {row}")
                continue  # Skip this row if any field is missing

            # Check if user exists
            user = db.query(User).filter_by(email=email).first()

            if not user:
                # Create user if doesn't exist
                user = User(
                    email=email,
                    name=name,
                    asu_id=asu_id,
                    academic_standing="N/A",
                    major="N/A"
                )
                db_user = db_connect.create_user(db, user)
                user_email = db_user.email
            else:
                user_email = user.email

            # Add points for the event
            point = Points(
                points=event_points,
                event=event_name,
                awarded_by_officer=marked_by,
                user_email=user_email
            )
            db_connect.create_point(db, point)
            success_count += 1

    except Exception as e:
        errors.append(str(e))
    finally:
        db.close()

    # Log the result of the processing (optional: you can store this to a DB or file)
    print(f"Processed {success_count} users. Errors: {errors}")

# Organization-prefix based endpoints
@points_blueprint.route("/<string:org_prefix>/users", methods=["POST"])
@auth_required
def add_user_to_org(org_prefix):
    """Add a user to a specific organization"""
    data = request.json
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        
        # Get organization by prefix
        organization = db.query(Organization).filter_by(
            prefix=org_prefix,
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Use the existing link_or_create_user function
        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'name': data.get('name'),
            'asu_id': data.get('asu_id', 'N/A'),
            'academic_standing': data.get('academic_standing', 'N/A'),
            'major': data.get('major', 'N/A')
        }
        
        user = link_or_create_user(
            organization.id, 
            user_data, 
            data.get("discord_id")
        )
        
        if not user:
            return jsonify({"error": "Failed to create or link user"}), 500
            
        return jsonify({
            "message": "User added to organization successfully",
            "user": {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "discord_linked": bool(user.discord_id)
            },
            "organization": {
                "name": organization.name,
                "prefix": organization.prefix
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@points_blueprint.route("/<string:org_prefix>/assign_points", methods=["POST"])
@auth_required
def assign_points_to_org(org_prefix):
    """Assign points to a user in a specific organization"""
    data = request.json
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        from modules.points.models import UserOrganizationMembership
        
        # Get organization by prefix
        organization = db.query(Organization).filter_by(
            prefix=org_prefix,
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Validate required fields
        if not data.get("user_identifier"):
            return jsonify({"error": "user_identifier is required"}), 400
        if not data.get("points"):
            return jsonify({"error": "points is required"}), 400

        user_identifier = data["user_identifier"]
        
        # Try to find user by email first, then UUID, then username
        user = db.query(User).filter_by(email=user_identifier).first()
        if not user:
            user = db.query(User).filter_by(uuid=user_identifier).first()
        if not user:
            user = db.query(User).filter_by(username=user_identifier).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user is a member of this organization
        membership = db.query(UserOrganizationMembership).filter_by(
            user_id=user.id,
            organization_id=organization.id,
            is_active=True
        ).first()
        
        if not membership:
            return jsonify({"error": "User is not a member of this organization"}), 400

        # Add points to the user
        point = Points(
            points=float(data["points"]),
            user_id=user.id,
            organization_id=organization.id
        )
        db.add(point)
        db.commit()
        db.refresh(point)
        
        return jsonify({
            "message": "Points assigned successfully",
            "points": {
                "id": point.id,
                "points": point.points,
                "user_id": point.user_id,
                "organization_id": point.organization_id,
                "last_updated": point.last_updated.isoformat() if point.last_updated else None
            },
            "user": {
                "name": user.name,
                "email": user.email
            },
            "organization": {
                "name": organization.name,
                "prefix": organization.prefix
            }
        }), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@points_blueprint.route("/<string:org_prefix>/users/<string:user_identifier>/points", methods=["GET"])
@auth_required
def get_user_points_in_org(org_prefix, user_identifier):
    """Get user's points in a specific organization"""
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        from modules.points.models import UserOrganizationMembership
        
        # Get organization by prefix
        organization = db.query(Organization).filter_by(
            prefix=org_prefix,
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Find user
        user = db.query(User).filter_by(email=user_identifier).first()
        if not user:
            user = db.query(User).filter_by(uuid=user_identifier).first()
        if not user:
            user = db.query(User).filter_by(username=user_identifier).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user is a member of this organization
        membership = db.query(UserOrganizationMembership).filter_by(
            user_id=user.id,
            organization_id=organization.id,
            is_active=True
        ).first()
        
        if not membership:
            return jsonify({"error": "User is not a member of this organization"}), 400

        # Get user's points in this organization
        total_points = db.query(func.sum(Points.points)).filter_by(
            user_id=user.id,
            organization_id=organization.id
        ).scalar() or 0
        
        # Get points history
        points_records = db.query(Points).filter_by(
            user_id=user.id,
            organization_id=organization.id
        ).order_by(Points.last_updated.desc()).all()
        
        return jsonify({
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "username": user.username
            },
            "organization": {
                "name": organization.name,
                "prefix": organization.prefix
            },
            "total_points": total_points,
            "points_history": [{
                "id": record.id,
                "points": record.points,
                "last_updated": record.last_updated.isoformat() if record.last_updated else None
            } for record in points_records]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()