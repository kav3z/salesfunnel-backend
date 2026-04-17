"""
Application configuration settings.
Loads environment variables and provides configuration for the entire application.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Settings
    APP_NAME: str = "SalesFunnel Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_VERSION: str = "v1"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Paystaack
    PAYSTACK_API_URL: str = "https://api.paystack.co"
    PAYSTACK_SECRET_KEY: str = "some-secret-key"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./salesfunnel.db"
    
    # Security & Authentication
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 900
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # File Upload Settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [".jpg", ".jpeg", ".png", ".pdf"]
    
    # Email Configuration (Future)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@salesfunnel.com"
    
    # Notification Settings
    ENABLE_EMAIL_NOTIFICATIONS: bool = False
    ENABLE_SMS_NOTIFICATIONS: bool = False
    
    # Cloudinary
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    CLOUDINARY_CLOUD_NAME: str
    
    # Admin Settings
    ADMIN_EMAIL: str = "admin@salesfunnel.com"
    ADMIN_PASSWORD: str = "change-this-password"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings() # type: ignore


# Create a global settings instance for easy import
settings = get_settings()
