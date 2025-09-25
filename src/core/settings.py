from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./budget_tracker.db"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Longer for convenience
    
    # Email verification token (shorter expiry)
    EMAIL_TOKEN_EXPIRE_HOURS: int = 24
    
    # Security
    BCRYPT_ROUNDS: int = 12
    
    # Inactive user threshold (days)
    INACTIVE_THRESHOLD_DAYS: int = 7
    
    # Google SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Budget Tracker"
    
    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"

settings = Settings()