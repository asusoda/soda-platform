"""
URL parsing and domain validation utilities for authentication system.
Handles domain validation, callback URL parsing, and state parameter management.
"""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional, Dict, List, Tuple
import logging
logger = logging.getLogger(__name__)


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to parse
        
    Returns:
        The domain (e.g., 'example.com') or None if invalid
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        
        # Remove port if present
        domain = parsed.netloc.split(':')[0]
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain.lower()
    except Exception as e:
        logger.error(f"Error extracting domain from URL {url}: {e}")
        return None


def is_valid_domain(domain: str) -> bool:
    """
    Validate if a domain string is properly formatted.
    
    Args:
        domain: Domain string to validate
        
    Returns:
        True if valid domain format, False otherwise
    """
    if not domain:
        return False
    
    # Basic domain validation regex
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    
    return bool(re.match(domain_pattern, domain))


def validate_callback_url(callback_url: str) -> Tuple[bool, str]:
    """
    Validate a callback URL for security and format.
    
    Args:
        callback_url: The callback URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not callback_url:
        return False, "Callback URL is required"
    
    try:
        parsed = urlparse(callback_url)
        
        # Must have scheme
        if not parsed.scheme:
            return False, "Callback URL must include scheme (http:// or https://)"
        
        # Only allow HTTP and HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False, "Callback URL must use HTTP or HTTPS scheme"
        
        # Must have netloc (domain)
        if not parsed.netloc:
            return False, "Callback URL must include a valid domain"
        
        # Extract and validate domain
        domain = extract_domain_from_url(callback_url)
        if not domain:
            return False, "Invalid domain in callback URL"
        
        if not is_valid_domain(domain):
            return False, "Invalid domain format in callback URL"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating callback URL {callback_url}: {e}")
        return False, f"Error validating callback URL: {str(e)}"


def is_domain_authorized(origin_domain: str, allowed_domains: List[str]) -> bool:
    """
    Check if a domain is authorized for authentication.
    
    Args:
        origin_domain: The domain making the request
        allowed_domains: List of domains allowed for this organization
        
    Returns:
        True if domain is authorized, False otherwise
    """
    if not origin_domain or not allowed_domains:
        return False
    
    # Normalize the origin domain
    origin_domain = origin_domain.lower().strip()
    
    # Check if origin domain matches any allowed domain
    for allowed_domain in allowed_domains:
        allowed_domain = allowed_domain.lower().strip()
        
        # Exact match
        if origin_domain == allowed_domain:
            return True
        
        # Subdomain match (e.g., app.example.com matches example.com)
        if origin_domain.endswith('.' + allowed_domain):
            return True
    
    return False


def build_oauth_state(organization_id: int, origin_domain: str, additional_data: Dict = None) -> str:
    """
    Build OAuth state parameter with organization and domain information.
    
    Args:
        organization_id: ID of the organization
        origin_domain: Domain where the request originated
        additional_data: Additional data to include in state
        
    Returns:
        Encoded state string
    """
    import base64
    import json
    
    state_data = {
        'org_id': organization_id,
        'origin_domain': origin_domain,
        'timestamp': int(time.time())
    }
    
    if additional_data:
        state_data.update(additional_data)
    
    # Encode as base64 for URL safety
    state_json = json.dumps(state_data)
    state_encoded = base64.urlsafe_b64encode(state_json.encode()).decode()
    
    return state_encoded


def parse_oauth_state(state: str) -> Optional[Dict]:
    """
    Parse OAuth state parameter to extract organization and domain information.
    
    Args:
        state: The state parameter from OAuth callback
        
    Returns:
        Dictionary with state data or None if invalid
    """
    import base64
    import json
    import time
    
    try:
        # Decode base64
        state_decoded = base64.urlsafe_b64decode(state.encode()).decode()
        state_data = json.loads(state_decoded)
        
        # Validate required fields
        required_fields = ['org_id', 'origin_domain', 'timestamp']
        if not all(field in state_data for field in required_fields):
            logger.warning(f"OAuth state missing required fields: {state_data}")
            return None
        
        # Check if state is not too old (e.g., 10 minutes)
        current_time = int(time.time())
        if current_time - state_data['timestamp'] > 600:  # 10 minutes
            logger.warning(f"OAuth state too old: {current_time - state_data['timestamp']} seconds")
            return None
        
        return state_data
        
    except Exception as e:
        logger.error(f"Error parsing OAuth state {state}: {e}")
        return None


def build_callback_url_with_params(base_url: str, params: Dict) -> str:
    """
    Build a callback URL with query parameters.
    
    Args:
        base_url: Base callback URL
        params: Parameters to add as query string
        
    Returns:
        Complete callback URL with parameters
    """
    if not base_url:
        return ""
    
    try:
        parsed = urlparse(base_url)
        
        # Parse existing query parameters
        existing_params = parse_qs(parsed.query)
        
        # Add new parameters
        for key, value in params.items():
            existing_params[key] = [str(value)]
        
        # Build new query string
        new_query = urlencode(existing_params, doseq=True)
        
        # Reconstruct URL
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return new_url
        
    except Exception as e:
        logger.error(f"Error building callback URL with params: {e}")
        return base_url


def extract_origin_from_request(request) -> Optional[str]:
    """
    Extract origin domain from Flask request.
    
    Args:
        request: Flask request object
        
    Returns:
        Origin domain or None if not available
    """
    # Try Origin header first (for CORS requests)
    origin = request.headers.get('Origin')
    if origin:
        return extract_domain_from_url(origin)
    
    # Try Referer header as fallback
    referer = request.headers.get('Referer')
    if referer:
        return extract_domain_from_url(referer)
    
    # Try X-Forwarded-Host header (for proxied requests)
    forwarded_host = request.headers.get('X-Forwarded-Host')
    if forwarded_host:
        return extract_domain_from_url(f"https://{forwarded_host}")
    
    # Try Host header as last resort
    host = request.headers.get('Host')
    if host:
        return extract_domain_from_url(f"https://{host}")
    
    return None


def sanitize_domain_list(domains: List[str]) -> List[str]:
    """
    Sanitize and validate a list of domains.
    
    Args:
        domains: List of domain strings
        
    Returns:
        List of valid, normalized domains
    """
    if not domains:
        return []
    
    sanitized = []
    for domain in domains:
        if isinstance(domain, str):
            domain = domain.strip().lower()
            if domain and is_valid_domain(domain):
                sanitized.append(domain)
    
    return sanitized


# Import time module for timestamp functionality
import time
