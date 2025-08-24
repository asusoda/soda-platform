from flask import request, jsonify, Blueprint, redirect, current_app, session, make_response
from shared import config, tokenManger
from modules.auth.decoraters import auth_required, error_handler
from modules.auth.url_utils import (
    extract_origin_from_request, 
    is_domain_authorized, 
    build_oauth_state, 
    parse_oauth_state,
    build_callback_url_with_params
)
import requests
from modules.utils.logging_config import logger, get_logger
from datetime import datetime

auth_blueprint = Blueprint("auth", __name__, template_folder=None, static_folder=None)
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI
GUILD_ID = 762811961238618122

logger.info(f"Auth API using CLIENT_ID: {CLIENT_ID} and REDIRECT_URI: {REDIRECT_URI}")

@auth_blueprint.route("/login", methods=["GET"])
def login():
    logger.info(f"Redirecting to Discord OAuth login for client_id: {CLIENT_ID} and REDIRECT_URI: {REDIRECT_URI}")
    return redirect(
        f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    )

@auth_blueprint.route("/validToken", methods=["GET"])
@auth_required
def validToken():
    token = request.headers.get("Authorization").split(" ")[
        1
    ]
    if tokenManger.is_token_valid(token):
        return jsonify({"status": "success", "valid": True, "expired": False}), 200
    else:
        return jsonify({"status": "error", "valid": False}), 401

@auth_blueprint.route("/callback", methods=["GET"])
def callback():
    # Get the auth bot from Flask app context (the one actually running in thread)
    auth_bot = current_app.auth_bot if hasattr(current_app, 'auth_bot') else None
    if not auth_bot or not auth_bot.is_ready():
        logger.error("Auth bot is not available or not ready for /callback")
        return jsonify({"error": "Authentication service temporarily unavailable. Bot not ready."}), 503

    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        logger.warning("No authorization code provided in /callback")
        return jsonify({"error": "No authorization code provided"}), 400
    
    # Check if this is a partner OAuth flow by looking at session data
    partner_org_prefix = session.get('partner_org_prefix')
    partner_org_id = session.get('partner_org_id')
    partner_callback_url = session.get('partner_callback_url')
    
    # Validate state parameter for partner flows
    if partner_org_prefix and state:
        # Parse the OAuth state to get organization and domain information
        state_data = parse_oauth_state(state)
        if not state_data:
            logger.warning(f"Invalid OAuth state for partner flow: {partner_org_prefix}")
            return jsonify({"error": "Invalid OAuth state"}), 400
        
        # Verify the state matches the session data
        if state_data.get('org_id') != partner_org_id:
            logger.warning(f"OAuth state org_id mismatch for partner flow: {partner_org_prefix}")
            return jsonify({"error": "Invalid OAuth state"}), 400
    
    logger.info("Received authorization code, exchanging for token.")
    token_response = requests.post(
        "https://discord.com/api/v10/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_response_data = token_response.json()

    if "access_token" in token_response_data:
        access_token = token_response_data["access_token"]
        logger.info("Access token received, fetching user info.")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        user_response = requests.get(
            "https://discord.com/api/v10/users/@me", headers=headers
        )
        user_info = user_response.json()
        user_id = user_info["id"]
        username = user_info.get("username", "Unknown")
        
        # Check if this is a partner OAuth flow
        if partner_org_prefix:
            # Partner OAuth flow - redirect to partner's callback URL
            logger.info(f"Processing partner OAuth callback for org: {partner_org_prefix}")
            return handle_partner_callback(user_id, username, partner_org_prefix, partner_org_id, partner_callback_url)
        else:
            # Regular SoDA OAuth flow (existing logic)
            officer_guilds = auth_bot.check_officer(user_id, config.SUPERADMIN_USER_ID)
            print(f"Officer guilds: {officer_guilds}")
            if officer_guilds:  # If user is officer in at least one organization
                name = auth_bot.get_name(user_id)
                # Generate token pair with both access and refresh tokens
                access_token, refresh_token = tokenManger.generate_token_pair(
                    username=name, 
                    discord_id=user_id, 
                    access_exp_minutes=30, 
                    refresh_exp_days=7
                )
                # Store user info in session with officer guilds
                session['user'] = {
                    'username': name,
                    'discord_id': user_id,
                    'role': 'officer',
                    'officer_guilds': officer_guilds  # Store the list of guild IDs where user is officer
                }
                session['token'] = access_token
                session['refresh_token'] = refresh_token
                # Redirect to React frontend with both tokens
                frontend_url = f"{config.CLIENT_URL}/auth/?access_token={access_token}&refresh_token={refresh_token}"
                return redirect(frontend_url)
            else:
                full_url = f"{config.CLIENT_URL}/auth/?error=Unauthorized Access"
                return redirect(full_url)
    else:
        logger.error(f"Failed to retrieve access token from Discord: {token_response_data}")
        return jsonify({"error": "Failed to retrieve access token"}), 400


@auth_blueprint.route("/refresh", methods=["POST"])
def refresh_token():
    """
    Refresh access token using refresh token.
    """
    try:
        data = request.get_json()
        if not data or 'refresh_token' not in data:
            return jsonify({"error": "Refresh token required"}), 400
        
        refresh_token = data['refresh_token']
        
        # Generate new access token
        new_access_token = tokenManger.refresh_access_token(refresh_token)
        
        if new_access_token:
            return jsonify({
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": 1800  # 30 minutes in seconds
            }), 200
        else:
            return jsonify({"error": "Invalid or expired refresh token"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_blueprint.route("/revoke", methods=["POST"])
@auth_required
def revoke_token():
    """
    Revoke refresh token (logout).
    """
    try:
        data = request.get_json()
        if not data or 'refresh_token' not in data:
            return jsonify({"error": "Refresh token required"}), 400
        
        refresh_token = data['refresh_token']
        
        # Revoke the refresh token
        if tokenManger.revoke_refresh_token(refresh_token):
            # Also blacklist the current access token
            current_token = request.headers.get("Authorization").split(" ")[1]
            tokenManger.delete_token(current_token)
            
            return jsonify({"message": "Token revoked successfully"}), 200
        else:
            return jsonify({"error": "Invalid refresh token"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_blueprint.route("/validateToken", methods=["GET"])
def valid_token():
    token = request.headers.get("Authorization").split(" ")[
        1
    ]
    if tokenManger.is_token_valid(token):
        if tokenManger.is_token_expired(token):
            logger.info(f"Token is valid but expired.")
            return jsonify(
                {"status": "success", "valid": True, "expired": True}
            ), 200
        else:
            logger.info(f"Token is valid and not expired.")
            return jsonify(
                {"status": "success", "valid": True, "expired": False}
            ), 200
    else:
        logger.warning(f"Token validation failed (invalid).")
        return jsonify(
            {"status": "error", "valid": False, "message": "Token is invalid"}
        ), 401


@auth_blueprint.route("/appToken", methods=["GET"])
@auth_required
@error_handler
def get_app_token():
    token = request.headers.get("Authorization").split(" ")[1]
    appname = request.args.get("appname")
    if not appname:
        return jsonify({"error": "appname query parameter is required"}), 400
    
    username = tokenManger.retrieve_username(token)
    if not username:
         return jsonify({"error": "Invalid user token"}), 401

    logger.info(f"Generating app token for user {username}, app: {appname}")
    app_token_value = tokenManger.genreate_app_token(username, appname)
    return jsonify({"app_token": app_token_value}), 200


@auth_blueprint.route("/name", methods=["GET"])
@auth_required
def get_name():
    autorisation = request.headers.get("Authorization").split(" ")[1]

    return jsonify({"name": tokenManger.retrieve_username(autorisation)}), 200


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    """
    Logout endpoint that revokes refresh token.
    """
    try:
        data = request.get_json()
        if data and 'refresh_token' in data:
            # Revoke refresh token
            tokenManger.revoke_refresh_token(data['refresh_token'])
        
        # Also blacklist current access token if provided
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
            tokenManger.delete_token(token)
        
        # Clear session
        session.clear()
        
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_blueprint.route("/success")
def success():
    return "You have successfully logged in with Discord! (This is a generic success page)"


# Partner OAuth endpoints
@auth_blueprint.route("/partner/login/<string:org_prefix>", methods=["GET"])
def partner_login(org_prefix):
    """Initiate Discord OAuth for partner organization"""
    from shared import db_connect
    
    # Extract origin domain from request
    origin_domain = extract_origin_from_request(request)
    if not origin_domain:
        logger.warning("Partner login attempted without origin domain")
        return jsonify({"error": "Origin domain could not be determined"}), 400
    
    # Validate organization prefix and get org info
    db = next(db_connect.get_db())
    try:
        from modules.organizations.models import Organization
        organization = db.query(Organization).filter_by(
            prefix=org_prefix,
            is_active=True,
            storefront_enabled=True,
            oauth_enabled=True
        ).first()
        
        if not organization:
            logger.warning(f"Partner login attempted for invalid org prefix: {org_prefix}")
            return jsonify({"error": "Organization not found, storefront not enabled, or OAuth not enabled"}), 404
        
        if not organization.oauth_callback_url:
            logger.warning(f"Partner login attempted for org without callback URL: {org_prefix}")
            return jsonify({"error": "OAuth callback URL not configured for this organization"}), 400
        
        # Check if origin domain is authorized
        if not organization.allowed_domains or not is_domain_authorized(origin_domain, organization.allowed_domains):
            logger.warning(f"Unauthorized domain {origin_domain} attempted login for org {org_prefix}")
            return jsonify({"error": "Domain not authorized for this organization"}), 403
        
        logger.info(f"Starting partner OAuth flow for organization: {org_prefix} from domain: {origin_domain}")
        
        # Build OAuth state with organization and domain information
        oauth_state = build_oauth_state(
            organization_id=organization.id,
            origin_domain=origin_domain
        )
        
        # Store partner context in session for callback
        session['partner_org_prefix'] = org_prefix
        session['partner_org_id'] = organization.id
        session['partner_callback_url'] = organization.oauth_callback_url
        session['origin_domain'] = origin_domain
        
        # Redirect to Discord OAuth with state parameter
        discord_auth_url = (
            f"https://discord.com/oauth2/authorize?"
            f"client_id={CLIENT_ID}&"
            f"redirect_uri={REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=identify%20guilds&"
            f"state={oauth_state}"
        )
        
        logger.info(f"Redirecting to Discord OAuth for partner org {org_prefix}")
        return redirect(discord_auth_url)
        
    except Exception as e:
        logger.error(f"Error in partner login for {org_prefix}: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        db.close()


def handle_partner_callback(discord_id, username, org_prefix, org_id, callback_url):
    """Handle OAuth callback for partner organizations"""
    from shared import db_connect
    
    try:
        # We already have the callback URL from session, but validate the organization still exists
        db = next(db_connect.get_db())
        try:
            from modules.organizations.models import Organization
            organization = db.query(Organization).filter_by(
                id=org_id,
                prefix=org_prefix,
                is_active=True
            ).first()
            
            if not organization:
                logger.error(f"Organization not found during partner callback: {org_prefix}")
                return redirect_to_error(callback_url, "Invalid organization")
        finally:
            db.close()
        
        # Get or create partner member
        partner_member = get_or_create_partner_member(
            discord_id=discord_id,
            username=username,
            organization_id=org_id,
            auth_provider='discord'
        )
        
        if not partner_member:
            logger.error(f"Failed to create partner member for {discord_id} in org {org_prefix}")
            return redirect_to_error(callback_url, "Failed to create member")
        
        # Generate partner session token
        session_token = generate_partner_session_token(partner_member, org_id)
        
        # Redirect to partner callback URL with session token
        # Using the callback_url stored in session when user started OAuth flow
        final_callback_url = build_callback_url_with_params(
            base_url=callback_url,
            params={
                'session_token': session_token,
                'member_id': partner_member.id,
                'points_balance': partner_member.current_points,
                'org_prefix': org_prefix,
                'success': 'true'
            }
        )
        
        # Clear partner session data
        session.pop('partner_org_prefix', None)
        session.pop('partner_org_id', None)
        session.pop('partner_callback_url', None)
        session.pop('oauth_state', None)
        
        logger.info(f"Redirecting partner member to: {final_callback_url}")
        return redirect(final_callback_url)
        
    except Exception as e:
        logger.error(f"Partner callback error for {org_prefix}: {e}")
        error_url = build_callback_url_with_params(
            base_url=callback_url,
            params={'error': 'authentication_failed', 'success': 'false'}
        )
        return redirect(error_url)


def get_or_create_partner_member(discord_id, username, organization_id, auth_provider='discord'):
    """Get existing partner member or create new one"""
    from shared import db_connect
    from modules.points.models import PartnerMember
    
    db = next(db_connect.get_db())
    try:
        # Check if partner member already exists by discord_id
        partner_member = db.query(PartnerMember).filter_by(
            discord_id=discord_id,
            organization_id=organization_id
        ).first()
        
        if partner_member:
            # Update last activity and username if needed
            partner_member.updated_at = datetime.utcnow()
            if partner_member.username != username:
                partner_member.username = username
            db.commit()
            logger.info(f"Found existing partner member: {partner_member.id}")
            return partner_member
        
        # Create new partner member
        import uuid
        partner_member = PartnerMember(
            discord_id=discord_id,
            organization_id=organization_id,
            email=f"{discord_id}@discord.temp",  # Temporary email, can be updated later
            name=username,
            username=username,
            auth_provider=auth_provider
        )
        
        db.add(partner_member)
        db.commit()
        db.refresh(partner_member)
        
        logger.info(f"Created new partner member: {partner_member.id} for discord_id {discord_id} in org {organization_id}")
        return partner_member
        
    except Exception as e:
        logger.error(f"Error creating partner member: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def generate_partner_session_token(partner_member, organization_id):
    """Generate a session token for partner member"""
    from modules.points.models import PartnerSession
    from shared import db_connect
    import secrets
    from datetime import datetime, timedelta
    
    # Generate secure session token
    session_token = secrets.token_urlsafe(32)
    
    # Create session record
    db = next(db_connect.get_db())
    try:
        # Clean up expired sessions for this member
        db.query(PartnerSession).filter(
            PartnerSession.partner_member_id == partner_member.id,
            PartnerSession.expires_at < datetime.utcnow()
        ).delete()
        
        # Create new session
        partner_session = PartnerSession(
            session_id=session_token,
            partner_member_id=partner_member.id,
            organization_id=organization_id,
            points_balance=partner_member.current_points,
            expires_at=datetime.utcnow() + timedelta(hours=24)  # 24 hour session
        )
        
        db.add(partner_session)
        db.commit()
        
        logger.info(f"Generated session token for partner member: {partner_member.id}")
        return session_token
        
    except Exception as e:
        logger.error(f"Error generating partner session token: {e}")
        db.rollback()
        return None
    finally:
        db.close()





def redirect_to_error(callback_url, error_message):
    """Redirect to callback URL with error message"""
    if callback_url:
        error_url = build_callback_url_with_params(callback_url, {'error': error_message, 'success': 'false'})
        return redirect(error_url)
    else:
        return jsonify({"error": error_message}), 400
