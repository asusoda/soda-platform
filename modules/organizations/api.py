from flask import Blueprint, jsonify, request
from shared import db_connect
from modules.organizations.models import Organization
from modules.auth.decoraters import auth_required
import re

organizations_blueprint = Blueprint("organizations", __name__)

@organizations_blueprint.route("/", methods=["GET"])
@auth_required
def get_organizations():
    """Get all organizations the user has access to"""
    try:
        db = next(db_connect.get_db())
        organizations = db.query(Organization).filter_by(is_active=True).all()
        
        return jsonify([org.to_dict() for org in organizations])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>", methods=["GET"])
@auth_required
def get_organization(org_id):
    """Get specific organization details"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        return jsonify(org.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/stats", methods=["GET"])
@auth_required
def get_organization_stats(org_id):
    """Get organization statistics"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        # Return mock stats for now - implement actual stats logic later
        stats = {
            "totalMembers": 25,
            "totalPoints": 1250,
            "activeEvents": 3,
            "monthlyPoints": 340
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/activity", methods=["GET"])
@auth_required
def get_organization_activity(org_id):
    """Get recent organization activity"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        # Return mock activity for now - implement actual activity logic later
        activity = [
            {
                "user_name": "John Doe",
                "description": "Attended weekly meeting",
                "points": 10,
                "timestamp": "2025-07-24T12:00:00Z"
            },
            {
                "user_name": "Jane Smith", 
                "description": "Completed project milestone",
                "points": 25,
                "timestamp": "2025-07-23T15:30:00Z"
            }
        ]
        
        return jsonify(activity)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/settings", methods=["PUT"])
@auth_required
def update_organization_settings(org_id):
    """Update organization settings"""
    try:
        data = request.get_json()
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        # Update organization settings
        if 'config' in data:
            org.config = data['config']
        if 'prefix' in data:
            new_prefix = data['prefix'].strip()
            
            # Validate prefix format
            if not new_prefix or len(new_prefix) < 2:
                return jsonify({"error": "Prefix must be at least 2 characters"}), 400
            if len(new_prefix) > 20:
                return jsonify({"error": "Prefix must be 20 characters or less"}), 400
            if not re.match(r'^[a-z0-9_-]+$', new_prefix):
                return jsonify({"error": "Prefix can only contain lowercase letters, numbers, hyphens, and underscores"}), 400
            
            # Check if prefix is already taken by another organization
            existing_org = db.query(Organization).filter_by(prefix=new_prefix).first()
            if existing_org and existing_org.id != org_id:
                return jsonify({"error": "Prefix is already taken by another organization"}), 400
            
            org.prefix = new_prefix
        if 'description' in data:
            org.description = data['description']
        if 'officer_role_id' in data:
            org.officer_role_id = data['officer_role_id']
        if 'points_per_message' in data:
            org.points_per_message = data['points_per_message']
        if 'points_cooldown' in data:
            org.points_cooldown = data['points_cooldown']
            
        db.commit()
        return jsonify({"message": "Settings updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/calendar", methods=["PUT"])
@auth_required
def update_organization_calendar_settings(org_id):
    """Update organization calendar settings"""
    try:
        data = request.get_json()
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        # Update calendar-related settings
        if 'notion_database_id' in data:
            org.notion_database_id = data['notion_database_id'].strip() if data['notion_database_id'] else None
        if 'calendar_sync_enabled' in data:
            org.calendar_sync_enabled = bool(data['calendar_sync_enabled'])
        if 'google_calendar_id' in data:
            org.google_calendar_id = data['google_calendar_id'].strip() if data['google_calendar_id'] else None
            
        db.commit()
        return jsonify({"message": "Calendar settings updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/calendar", methods=["GET"])
@auth_required
def get_organization_calendar_settings(org_id):
    """Get organization calendar settings"""
    try:
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        
        if not org:
            return jsonify({"error": "Organization not found"}), 404
            
        calendar_settings = {
            "notion_database_id": org.notion_database_id,
            "calendar_sync_enabled": org.calendar_sync_enabled,
            "google_calendar_id": org.google_calendar_id,
            "last_sync_at": org.last_sync_at.isoformat() if org.last_sync_at else None
        }
        
        return jsonify(calendar_settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@organizations_blueprint.route("/<int:org_id>/roles", methods=["GET"])
@auth_required
def get_organization_roles(org_id):
    """Get Discord roles for the organization"""
    try:
        # Return mock roles for now - implement actual Discord role fetching later
        roles = [
            {"id": "123456789", "name": "Officer"},
            {"id": "987654321", "name": "Member"},
            {"id": "456789123", "name": "Admin"}
        ]
        
        return jsonify(roles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500 

@organizations_blueprint.route("/<int:org_id>/ocp-sync", methods=["PUT"])
@auth_required
def update_organization_ocp_sync(org_id):
    """Update OCP sync enabled status for an organization."""
    try:
        data = request.get_json()
        db = next(db_connect.get_db())
        org = db.query(Organization).filter_by(id=org_id, is_active=True).first()
        if not org:
            return jsonify({"error": "Organization not found"}), 404
        if 'ocp_sync_enabled' in data:
            org.ocp_sync_enabled = bool(data['ocp_sync_enabled'])
        db.commit()
        return jsonify({"message": "OCP sync setting updated successfully", "ocp_sync_enabled": org.ocp_sync_enabled})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# OAuth Configuration endpoints
@organizations_blueprint.route("/<int:org_id>/oauth", methods=["PUT"])
@auth_required
def update_organization_oauth_settings(org_id):
    """Update organization OAuth callback URL and storefront settings"""
    from shared import config
    import re
    
    data = request.get_json()
    
    db = next(db_connect.get_db())
    try:
        organization = db.query(Organization).filter_by(
            id=org_id, 
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        # Update OAuth and storefront settings
        if 'oauth_callback_url' in data:
            callback_url = data['oauth_callback_url']
            if callback_url and not validate_callback_url(callback_url):
                return jsonify({"error": "Invalid callback URL"}), 400
            organization.oauth_callback_url = callback_url
        
        if 'storefront_enabled' in data:
            organization.storefront_enabled = bool(data['storefront_enabled'])
        
        if 'public_storefront' in data:
            organization.public_storefront = bool(data['public_storefront'])
        
        if 'allowed_domains' in data:
            organization.allowed_domains = data['allowed_domains']
        
        if 'points_spending_enabled' in data:
            organization.points_spending_enabled = bool(data['points_spending_enabled'])
        
        if 'theme_config' in data:
            organization.theme_config = data['theme_config']
        
        if 'logo_url' in data:
            organization.logo_url = data['logo_url']
        
        db.commit()
        
        # Return the login URL if callback is configured
        login_url = None
        if organization.oauth_callback_url and organization.storefront_enabled:
            login_url = f"{config.API_URL}/api/auth/partner/login/{organization.prefix}"
        
        return jsonify({
            "message": "OAuth settings updated successfully",
            "oauth_callback_url": organization.oauth_callback_url,
            "storefront_enabled": organization.storefront_enabled,
            "login_url": login_url,
            "org_prefix": organization.prefix
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@organizations_blueprint.route("/<int:org_id>/oauth", methods=["GET"])
@auth_required
def get_organization_oauth_settings(org_id):
    """Get organization OAuth settings"""
    from shared import config
    
    db = next(db_connect.get_db())
    try:
        organization = db.query(Organization).filter_by(
            id=org_id, 
            is_active=True
        ).first()
        
        if not organization:
            return jsonify({"error": "Organization not found"}), 404
        
        login_url = None
        if organization.oauth_callback_url and organization.storefront_enabled:
            login_url = f"{config.API_URL}/api/auth/partner/login/{organization.prefix}"
        
        return jsonify({
            "oauth_callback_url": organization.oauth_callback_url,
            "storefront_enabled": organization.storefront_enabled,
            "public_storefront": organization.public_storefront,
            "allowed_domains": organization.allowed_domains,
            "points_spending_enabled": organization.points_spending_enabled,
            "points_enabled": organization.points_enabled,
            "points_earning_rules": organization.points_earning_rules,
            "theme_config": organization.theme_config,
            "logo_url": organization.logo_url,
            "login_url": login_url,
            "org_prefix": organization.prefix
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


def validate_callback_url(url):
    """Validate callback URL format and security"""
    import re
    
    if not url:
        return False
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Security checks
    if url.startswith('http://') and 'localhost' not in url and '127.0.0.1' not in url:
        # Only allow http for localhost/dev, require https for production
        return False
    
    return True