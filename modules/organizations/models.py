from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from modules.utils.base import Base

class Organization(Base):
    """Model representing a Discord organization/guild."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(20), nullable=False, unique=True)  # URL-friendly prefix for the organization
    
    guild_id = Column(String(50), nullable=False, unique=True)
    description = Column(String(500))
    icon_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default=dict)  # Store organization-specific settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    officer_role_id = Column(String(50), nullable=True)  # Changed to String since Discord role IDs are strings
    points_per_message = Column(Integer, default=1)  # Default points per message
    points_cooldown = Column(Integer, default=60)  # Default cooldown in seconds
    ocp_sync_enabled = Column(Boolean, default=False)  # Added for OCP multi-org sync
    
    # Calendar-related fields
    google_calendar_id = Column(String(255), nullable=True)  # Google Calendar ID for this org
    notion_database_id = Column(String(255), nullable=True)  # Notion database ID for this org
    calendar_sync_enabled = Column(Boolean, default=False)  # Whether calendar sync is enabled
    last_sync_at = Column(DateTime, nullable=True)  # Last successful sync timestamp
    
    # Partner Integration Fields
    storefront_enabled = Column(Boolean, default=False)  # Enable partner storefront
    public_storefront = Column(Boolean, default=False)  # Allow non-Discord members
    oauth_callback_url = Column(String(500), nullable=True)  # OAuth callback URL for partner sites
    allowed_domains = Column(JSON, default=list)  # CORS domains for embeds and OAuth
    custom_domain = Column(String(255), nullable=True)  # Custom storefront domain
    oauth_enabled = Column(Boolean, default=False)  # Enable OAuth for this organization
    oauth_state_secret = Column(String(255), nullable=True)  # Secret for OAuth state validation
    
    # Points Configuration for Partners
    points_enabled = Column(Boolean, default=True)  # Enable points system
    points_earning_rules = Column(JSON, default=dict)  # Rules for earning points
    points_spending_enabled = Column(Boolean, default=True)  # Allow spending points
    
    # Branding
    theme_config = Column(JSON, default=dict)  # Custom styling for embeds
    logo_url = Column(String(255), nullable=True)  # Organization logo URL

    def __repr__(self):
        return f"<Organization(name='{self.name}', guild_id='{self.guild_id}')>"

    def to_dict(self):
        """Convert organization to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "guild_id": self.guild_id,
            "description": self.description,
            "icon_url": self.icon_url,
            "is_active": self.is_active,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "officer_role_id": self.officer_role_id,
            "points_per_message": self.points_per_message,
            "points_cooldown": self.points_cooldown,
            "google_calendar_id": self.google_calendar_id,
            "notion_database_id": self.notion_database_id,
            "calendar_sync_enabled": self.calendar_sync_enabled,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            # Partner Integration Fields
            "storefront_enabled": self.storefront_enabled,
            "public_storefront": self.public_storefront,
            "oauth_callback_url": self.oauth_callback_url,
            "allowed_domains": self.allowed_domains,
            "custom_domain": self.custom_domain,
            "oauth_enabled": self.oauth_enabled,
            "oauth_state_secret": self.oauth_state_secret,
            # Points Configuration
            "points_enabled": self.points_enabled,
            "points_earning_rules": self.points_earning_rules,
            "points_spending_enabled": self.points_spending_enabled,
            # Branding
            "theme_config": self.theme_config,
            "logo_url": self.logo_url
        }

class OrganizationConfig(Base):
    """Model for organization-specific configurations."""
    __tablename__ = "organization_configs"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    organization = relationship("Organization", backref="configurations")

    def __repr__(self):
        return f"<OrganizationConfig(org_id={self.organization_id}, key='{self.key}')>"

    def to_dict(self):
        """Convert config to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
class Officer(Base):
    """Model for organization officers."""
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    organization = relationship("Organization", backref="officers")