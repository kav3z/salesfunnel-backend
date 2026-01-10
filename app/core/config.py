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
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./salesfunnel.db"
    
    # Security & Authentication
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
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
    
    # SMS Configuration (Future)
    SMS_PROVIDER: Optional[str] = None
    SMS_API_KEY: Optional[str] = None
    SMS_FROM: Optional[str] = None
    
    # Notification Settings
    ENABLE_EMAIL_NOTIFICATIONS: bool = False
    ENABLE_SMS_NOTIFICATIONS: bool = False
    
    # Business Rules
    ORDER_FULFILLMENT_HOURS: int = 2
    PAYMENT_VERIFICATION_TIMEOUT_MINUTES: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    # Redis Configuration (optional)
    REDIS_URL: Optional[str] = None
    
    # Monitoring (optional)
    SENTRY_DSN: Optional[str] = None
    
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
    return Settings()


# Create a global settings instance for easy import
settings = get_settings()
