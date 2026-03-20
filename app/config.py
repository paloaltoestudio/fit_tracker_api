import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./fit_tracker.db"
    )

    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Resend email API
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "noreply@yourdomain.com")

    # Frontend URL (used in password reset links)
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Registration protection (if set, required in POST /register)
    registration_code: str = os.getenv("REGISTRATION_CODE", "")

    # MCP server
    mcp_api_key: str = os.getenv("MCP_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
