"""Configuration management"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "sqlite:///./finance_recon.db"
    
    # OAuth (Auth0)
    auth0_domain: Optional[str] = None
    auth0_client_id: Optional[str] = None
    auth0_client_secret: Optional[str] = None
    auth0_audience: Optional[str] = None
    
    # OAuth (Supabase)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # Server
    mcp_server_url: str = "https://your-server.com"
    secret_key: str = Field(default="dev-only-not-for-production")
    widget_base_url: Optional[str] = None
    
    # CORS - comma-separated list of allowed origins
    allowed_origins: str = "https://chatgpt.com"
    
    # Cursor Agent integration
    cursor_api_key: Optional[str] = None  # Optional, for headless mode
    cursor_agent_path: str = "cursor-agent"  # Default: "cursor-agent", can be full path
    categorization_batch_size: int = 20
    categorization_max_workers: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    def validate_production_settings(self) -> None:
        """Validate settings for production use. Call during startup."""
        is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
        if is_production and "dev-only" in self.secret_key.lower():
            raise ValueError(
                "SECRET_KEY must be set to a secure value in production. "
                "Set the SECRET_KEY environment variable."
            )


settings = Settings()
