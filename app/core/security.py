# internal imports
from .config import settings

# external imports
import bcrypt
from app.models.user import User
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status
from sqlmodel import Session, select



# Password hashing context


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    password_bytes = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    password_bytes = plain_password[:72].encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def authenticate_user(email: str, password: str, db: Session) -> User | None:
    """Authenticate user by email and password"""
    user = db.exec(select(User).where(User.email == email)).first()
    
    if not user:
        return None
    
    # Truncate password before verification
    truncated_password = password[:72]
    
    if not verify_password(truncated_password, user.password_hash):
        return None
    
    return user


def create_access_token(user_id: str, email: str, user_role: str, full_name: str, expires_delta: timedelta, is_active: bool):
    """Create JWT access token with user information"""
    encode = {
        "user_id": user_id,
        "email": email,
        "role": user_role,
        "full_name": full_name,
        "is_active": is_active
    }
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires}) # type: ignore
    return jwt.encode(encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
