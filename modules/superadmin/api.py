from flask import Blueprint, jsonify, request, session, current_app
from shared import db_connect, config, tokenManger
from modules.organizations.models import Organization
from modules.organizations.config import OrganizationSettings
from modules.auth.decoraters import superadmin_required
from modules.auth.url_utils import validate_callback_url, sanitize_domain_list

superadmin_blueprint = Blueprint("superadmin", __name__)

@superadmin_blueprint.route("/check", methods=["GET"])
@superadmin_required
def check_superadmin():
    """Check if user has superadmin privileges"""
    try:
        print(f"🔍 [DEBUG] check_superadmin endpoint called")
        
        # Get the token from Authorization header
        auth_header = request.headers.get("Authorization")
        print(f"🔍 [DEBUG] Authorization header: {auth_header}")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            print(f"❌ [DEBUG] Invalid Authorization header format")
            return jsonify({"error": "Authorization header required"}), 401
        
        token = auth_header.split(" ")[1]
        print(f"🔍 [DEBUG] Extracted token: {token[:20]}...")
        
        # Decode the token to get user information
        print(f"🔍 [DEBUG] Decoding token...")
        token_data = tokenManger.decode_token(token)
        if not token_data:
            print(f"❌ [DEBUG] Failed to decode token")
            return jsonify({"error": "Invalid token"}), 401
        
        print(f"🔍 [DEBUG] Token data: {token_data}")
        
        # Get Discord ID from token
        user_discord_id = token_data.get('discord_id')
        if not user_discord_id:
            print(f"❌ [DEBUG] Token missing Discord ID")
            return jsonify({"error": "Token missing Discord ID"}), 401
        
        superadmin_id = config.SUPERADMIN_USER_ID
        print(f"🔍 [DEBUG] Superadmin ID from config: {superadmin_id}")
        
        print(f"🔍 [DEBUG] Comparing user_discord_id: {user_discord_id} with superadmin_id: {superadmin_id}")
        print(f"🔍 [DEBUG] String comparison: '{str(user_discord_id)}' == '{str(superadmin_id)}'")
        
        # Check if user's ID matches the superadmin ID
        if str(user_discord_id) == str(superadmin_id):
            print(f"✅ [DEBUG] User is superadmin - returning True")
            return jsonify({"is_superadmin": True}), 200
        else:
            print(f"❌ [DEBUG] User is not superadmin - returning False")
            return jsonify({"is_superadmin": False}), 403
            
    except Exception as e:
        print(f"❌ [DEBUG] Error in check_superadmin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error checking superadmin status: {str(e)}"}), 500

@superadmin_blueprint.route("/dashboard", methods=["GET"])
@superadmin_required
def get_dashboard():
    """Get SuperAdmin dashboard data"""
    try:
        print(f"🔍 [DEBUG] get_dashboard endpoint called")
        
        # Get the auth bot from Flask app context
        print(f"🔍 [DEBUG] Getting auth bot from Flask app context...")
        auth_bot = current_app.auth_bot if hasattr(current_app, 'auth_bot') else None
        if not auth_bot:
            print(f"❌ [DEBUG] Auth bot not found in Flask app context!")
            return jsonify({"error": "Bot not available"}), 503
        
        if not auth_bot.is_ready():
            print(f"❌ [DEBUG] Auth bot is not ready!")
            return jsonify({"error": "Bot not available"}), 503
        
        print(f"✅ [DEBUG] Auth bot is ready")
        
        # Get all guilds where the bot is a member
        guilds = auth_bot.guilds
        print(f"🔍 [DEBUG] Bot is in {len(guilds)} guilds")
        
        # Get existing organizations from the database
        print(f"🔍 [DEBUG] Getting organizations from database...")
        db = next(db_connect.get_db())
        existing_orgs = db.query(Organization).all()
        print(f"🔍 [DEBUG] Found {len(existing_orgs)} existing organizations")
        
        existing_guild_ids = {org.guild_id for org in existing_orgs}
        print(f"🔍 [DEBUG] Existing guild IDs: {existing_guild_ids}")
        
        # Filter guilds to show only those not already added
        available_guilds = []
        for guild in guilds:
            if str(guild.id) not in existing_guild_ids:
                available_guilds.append({
                    "id": str(guild.id),
                    "name": guild.name,
                    "icon": {
                        "url": str(guild.icon.url) if guild.icon else None
                    }
                })
        
        print(f"🔍 [DEBUG] Found {len(available_guilds)} available guilds")
        
        # Get officer's organizations - check which orgs the current user is an officer of
        print(f"🔍 [DEBUG] Getting officer organizations...")
        officer_orgs = []
        officer_id = session.get('user', {}).get('discord_id')
        print(f"🔍 [DEBUG] Officer ID from session: {officer_id}")
        
        if officer_id:
            for org in existing_orgs:
                try:
                    guild = auth_bot.get_guild(int(org.guild_id))
                    if guild and guild.get_member(int(officer_id)):
                        officer_orgs.append(org)
                        print(f"🔍 [DEBUG] User is officer in organization: {org.name}")
                except (ValueError, AttributeError) as e:
                    print(f"🔍 [DEBUG] Error checking organization {org.name}: {e}")
                    # Skip if guild_id is invalid or guild not found
                    continue
        
        print(f"🔍 [DEBUG] User is officer in {len(officer_orgs)} organizations")
        
        # Get OAuth status for all organizations
        oauth_status = []
        for org in existing_orgs:
            oauth_info = {
                "id": org.id,
                "name": org.name,
                "prefix": org.prefix,
                "oauth_enabled": org.oauth_enabled,
                "has_callback_url": bool(org.oauth_callback_url),
                "allowed_domains_count": len(org.allowed_domains) if org.allowed_domains else 0,
                "storefront_enabled": org.storefront_enabled
            }
            oauth_status.append(oauth_info)
        
        response_data = {
            "available_guilds": available_guilds,
            "existing_orgs": [org.to_dict() for org in existing_orgs],
            "officer_orgs": [org.to_dict() for org in officer_orgs],
            "oauth_status": oauth_status
        }
        
        print(f"✅ [DEBUG] Dashboard data prepared successfully")
        return jsonify(response_data)
    except Exception as e:
        print(f"❌ [DEBUG] Error in get_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@superadmin_blueprint.route("/guild_roles/<guild_id>", methods=["GET"])
@superadmin_required
def get_guild_roles(guild_id):
    """Get all roles from a specific guild"""
    try:
        print(f"🔍 [DEBUG] get_guild_roles endpoint called for guild_id: {guild_id}")
        
        # Get the auth bot from Flask app context
        print(f"🔍 [DEBUG] Getting auth bot from Flask app context...")
        auth_bot = current_app.auth_bot if hasattr(current_app, 'auth_bot') else None
        if not auth_bot:
            print(f"❌ [DEBUG] Auth bot not found in Flask app context!")
            return jsonify({"error": "Bot not available"}), 503
        
        if not auth_bot.is_ready():
            print(f"❌ [DEBUG] Auth bot is not ready!")
            return jsonify({"error": "Bot not available"}), 503
        
        print(f"✅ [DEBUG] Auth bot is ready")
        
        # Convert guild_id to int for comparison
        try:
            guild_id_int = int(guild_id)
            print(f"🔍 [DEBUG] Converted guild_id to int: {guild_id_int}")
        except ValueError:
            print(f"❌ [DEBUG] Invalid guild ID format: {guild_id}")
            return jsonify({"error": "Invalid guild ID format"}), 400
        
        # Get the guild
        print(f"🔍 [DEBUG] Getting guild with ID: {guild_id_int}")
        guild = auth_bot.get_guild(guild_id_int)
        if not guild:
            print(f"❌ [DEBUG] Guild not found for ID: {guild_id_int}")
            return jsonify({"error": "Guild not found"}), 404
        
        print(f"✅ [DEBUG] Found guild: {guild.name}")
        
        # Get all roles from the guild
        print(f"🔍 [DEBUG] Getting roles from guild...")
        roles = []
        for role in guild.roles:
            # Skip @everyone role and bot roles
            if role.name != "@everyone" and not role.managed:
                roles.append({
                    "id": str(role.id),
                    "name": role.name,
                    "color": str(role.color),
                    "position": role.position,
                    "permissions": role.permissions.value
                })
                print(f"🔍 [DEBUG] Added role: {role.name} (ID: {role.id})")
        
        # Sort roles by position (highest first)
        roles.sort(key=lambda x: x["position"], reverse=True)
        
        print(f"✅ [DEBUG] Found {len(roles)} roles for guild {guild.name}")
        return jsonify({"roles": roles})
    except Exception as e:
        print(f"❌ [DEBUG] Error in get_guild_roles: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@superadmin_blueprint.route("/update_officer_role/<int:org_id>", methods=["PUT"])
@superadmin_required
def update_officer_role(org_id):
    """Update the officer role ID for an organization"""
    try:
        print(f"🔍 [DEBUG] update_officer_role endpoint called for org_id: {org_id}")
        
        # Get the request data
        data = request.get_json()
        print(f"🔍 [DEBUG] Request data: {data}")
        
        if not data or 'officer_role_id' not in data:
            print(f"❌ [DEBUG] Missing officer_role_id in request data")
            return jsonify({"error": "officer_role_id is required"}), 400
        
        officer_role_id = data['officer_role_id']
        print(f"🔍 [DEBUG] Officer role ID: {officer_role_id}")
        
        # Get the auth bot from Flask app context
        print(f"🔍 [DEBUG] Getting auth bot from Flask app context...")
        auth_bot = current_app.auth_bot if hasattr(current_app, 'auth_bot') else None
        if not auth_bot:
            print(f"❌ [DEBUG] Auth bot not found in Flask app context!")
            return jsonify({"error": "Bot not available"}), 503
        
        if not auth_bot.is_ready():
            print(f"❌ [DEBUG] Auth bot is not ready!")
            return jsonify({"error": "Bot not available"}), 503
        
        print(f"✅ [DEBUG] Auth bot is ready")
        
        # Get the organization from database
        print(f"🔍 [DEBUG] Getting organization from database...")
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            print(f"❌ [DEBUG] Organization not found for ID: {org_id}")
            return jsonify({"error": "Organization not found"}), 404
        
        print(f"✅ [DEBUG] Found organization: {org.name} (Guild ID: {org.guild_id})")
        
        # Verify the role exists in the guild
        try:
            print(f"🔍 [DEBUG] Getting guild for verification...")
            guild = auth_bot.get_guild(int(org.guild_id))
            if not guild:
                print(f"❌ [DEBUG] Guild not found for ID: {org.guild_id}")
                return jsonify({"error": "Guild not found"}), 404
            
            print(f"✅ [DEBUG] Found guild: {guild.name}")
            
            # If officer_role_id is provided, verify it exists
            if officer_role_id:
                print(f"🔍 [DEBUG] Verifying role exists in guild...")
                role = guild.get_role(int(officer_role_id))
                if not role:
                    print(f"❌ [DEBUG] Role not found in guild for ID: {officer_role_id}")
                    return jsonify({"error": "Role not found in guild"}), 404
                
                print(f"✅ [DEBUG] Found role: {role.name}")
            else:
                print(f"🔍 [DEBUG] No officer role ID provided (clearing role)")
                
        except (ValueError, AttributeError) as e:
            print(f"❌ [DEBUG] Error verifying role: {e}")
            return jsonify({"error": f"Invalid role ID format: {str(e)}"}), 400
        
        # Update the officer role ID
        print(f"🔍 [DEBUG] Updating officer role ID in database...")
        org.officer_role_id = officer_role_id
        db.commit()
        
        print(f"✅ [DEBUG] Officer role updated successfully")
        
        return jsonify({
            "message": f"Officer role updated successfully for {org.name}",
            "organization": org.to_dict()
        })
    except Exception as e:
        print(f"❌ [DEBUG] Error in update_officer_role: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@superadmin_blueprint.route("/add_org/<guild_id>", methods=["POST"])
@superadmin_required
def add_organization(guild_id):
    """Add a new organization to the system"""
    try:
        # Get the auth bot from Flask app context
        auth_bot = current_app.auth_bot if hasattr(current_app, 'auth_bot') else None
        if not auth_bot or not auth_bot.is_ready():
            return jsonify({"error": "Bot not available"}), 503
        
        # Convert guild_id to int for comparison with guild.id
        try:
            guild_id_int = int(guild_id)
        except ValueError:
            return jsonify({"error": "Invalid guild ID format"}), 400
        
        # Find the guild
        guild = next((g for g in auth_bot.guilds if g.id == guild_id_int), None)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404
        
        # Create prefix from guild name
        prefix = guild.name.lower().replace(' ', '_').replace('-', '_')
        
        # Create new organization with default settings
        settings = OrganizationSettings()
        new_org = Organization(
            name=guild.name,
            guild_id=str(guild.id),
            prefix=prefix,
            description=f"Discord server: {guild.name}",
            icon_url=str(guild.icon.url) if guild.icon else None,
            config=settings.to_dict()
        )
        
        # Save to database
        db = next(db_connect.get_db())
        db.add(new_org)
        db.commit()
        
        return jsonify({"message": f"Organization {guild.name} added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@superadmin_blueprint.route("/remove_org/<int:org_id>", methods=["DELETE"])
@superadmin_required
def remove_organization(org_id):
    """Remove an organization from the system"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        org_name = org.name
        db.delete(org)
        db.commit()
        
        return jsonify({"message": f"Organization {org_name} removed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close() 


@superadmin_blueprint.route("/organizations/<int:org_id>/oauth", methods=["PUT"])
@superadmin_required
def update_organization_oauth(org_id):
    """Update OAuth settings for an organization"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data required"}), 400
        
        # Validate required fields
        required_fields = ['oauth_enabled', 'oauth_callback_url']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Missing required fields: {required_fields}"}), 400
        
        # Validate callback URL if provided
        if data['oauth_callback_url']:
            is_valid, error_msg = validate_callback_url(data['oauth_callback_url'])
            if not is_valid:
                return jsonify({"error": f"Invalid callback URL: {error_msg}"}), 400
        
        # Validate and sanitize allowed domains
        allowed_domains = []
        if 'allowed_domains' in data and isinstance(data['allowed_domains'], list):
            allowed_domains = sanitize_domain_list(data['allowed_domains'])
        
        # Get organization from database
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        
        # Update OAuth settings
        org.oauth_enabled = data['oauth_enabled']
        org.oauth_callback_url = data['oauth_callback_url']
        org.allowed_domains = allowed_domains
        
        # Generate OAuth state secret if enabling OAuth
        if data['oauth_enabled'] and not org.oauth_state_secret:
            import secrets
            org.oauth_state_secret = secrets.token_urlsafe(32)
        
        db.commit()
        
        return jsonify({
            "message": f"OAuth settings updated successfully for {org.name}",
            "organization": org.to_dict()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()


@superadmin_blueprint.route("/organizations/<int:org_id>/oauth", methods=["GET"])
@superadmin_required
def get_organization_oauth(org_id):
    """Get OAuth settings for an organization"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        
        oauth_settings = {
            "oauth_enabled": org.oauth_enabled,
            "oauth_callback_url": org.oauth_callback_url,
            "allowed_domains": org.allowed_domains,
            "oauth_state_secret": org.oauth_state_secret
        }
        
        return jsonify(oauth_settings)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()


@superadmin_blueprint.route("/organizations/<int:org_id>/domains", methods=["PUT"])
@superadmin_required
def update_organization_domains(org_id):
    """Update allowed domains for an organization"""
    try:
        data = request.get_json()
        if not data or 'allowed_domains' not in data:
            return jsonify({"error": "allowed_domains field required"}), 400
        
        if not isinstance(data['allowed_domains'], list):
            return jsonify({"error": "allowed_domains must be a list"}), 400
        
        # Validate and sanitize domains
        allowed_domains = sanitize_domain_list(data['allowed_domains'])
        
        # Get organization from database
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        
        # Update allowed domains
        org.allowed_domains = allowed_domains
        db.commit()
        
        return jsonify({
            "message": f"Allowed domains updated successfully for {org.name}",
            "allowed_domains": allowed_domains
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()


@superadmin_blueprint.route("/organizations/<int:org_id>/callback", methods=["PUT"])
@superadmin_required
def update_organization_callback(org_id):
    """Update OAuth callback URL for an organization"""
    try:
        data = request.get_json()
        if not data or 'oauth_callback_url' not in data:
            return jsonify({"error": "oauth_callback_url field required"}), 400
        
        callback_url = data['oauth_callback_url']
        
        # Validate callback URL
        is_valid, error_msg = validate_callback_url(callback_url)
        if not is_valid:
            return jsonify({"error": f"Invalid callback URL: {error_msg}"}), 400
        
        # Get organization from database
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        
        # Update callback URL
        org.oauth_callback_url = callback_url
        db.commit()
        
        return jsonify({
            "message": f"Callback URL updated successfully for {org.name}",
            "oauth_callback_url": callback_url
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()


@superadmin_blueprint.route("/organizations/<int:org_id>/oauth/test", methods=["POST"])
@superadmin_required
def test_organization_oauth(org_id):
    """Test OAuth configuration for an organization"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        
        # Check OAuth configuration
        oauth_config = {
            "oauth_enabled": org.oauth_enabled,
            "has_callback_url": bool(org.oauth_callback_url),
            "has_allowed_domains": bool(org.allowed_domains),
            "domains_count": len(org.allowed_domains) if org.allowed_domains else 0,
            "has_state_secret": bool(org.oauth_state_secret)
        }
        
        # Validate callback URL if present
        if org.oauth_callback_url:
            is_valid, error_msg = validate_callback_url(org.oauth_callback_url)
            oauth_config["callback_url_valid"] = is_valid
            if not is_valid:
                oauth_config["callback_url_error"] = error_msg
        
        # Validate domains if present
        if org.allowed_domains:
            from modules.auth.url_utils import is_valid_domain
            valid_domains = []
            invalid_domains = []
            
            for domain in org.allowed_domains:
                if is_valid_domain(domain):
                    valid_domains.append(domain)
                else:
                    invalid_domains.append(domain)
            
            oauth_config["valid_domains"] = valid_domains
            oauth_config["invalid_domains"] = invalid_domains
            oauth_config["all_domains_valid"] = len(invalid_domains) == 0
        
        return jsonify({
            "organization": org.name,
            "oauth_config": oauth_config
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()


@superadmin_blueprint.route("/organizations/oauth/summary", methods=["GET"])
@superadmin_required
def get_oauth_summary():
    """Get summary of OAuth configurations across all organizations"""
    try:
        db = next(db_connect.get_db())
        organizations = db.query(Organization).all()
        
        oauth_summary = {
            "total_organizations": len(organizations),
            "oauth_enabled_count": 0,
            "oauth_configured_count": 0,
            "organizations_with_domains": 0,
            "organizations_with_callbacks": 0,
            "organizations_details": []
        }
        
        for org in organizations:
            org_oauth_info = {
                "id": org.id,
                "name": org.name,
                "prefix": org.prefix,
                "oauth_enabled": org.oauth_enabled,
                "oauth_callback_url": org.oauth_callback_url,
                "allowed_domains": org.allowed_domains,
                "storefront_enabled": org.storefront_enabled,
                "is_active": org.is_active
            }
            
            oauth_summary["organizations_details"].append(org_oauth_info)
            
            if org.oauth_enabled:
                oauth_summary["oauth_enabled_count"] += 1
            
            if org.oauth_enabled and org.oauth_callback_url and org.allowed_domains:
                oauth_summary["oauth_configured_count"] += 1
            
            if org.allowed_domains:
                oauth_summary["organizations_with_domains"] += 1
            
            if org.oauth_callback_url:
                oauth_summary["organizations_with_callbacks"] += 1
        
        return jsonify(oauth_summary)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()