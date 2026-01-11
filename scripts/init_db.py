# Database initialization script
# - Create all tables
# - Run initial migrations
# - Create admin user

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.core.database import engine, create_db_and_tables
from app.models.user import User, UserRole
from app.core.security import hash_password
from datetime import datetime, timezone


def create_admin_user(session: Session, email: str, password: str, full_name: str) -> User:
    """
    Create an admin user if it doesn't exist.
    
    Args:
        session: Database session
        email: Admin email
        password: Admin password (will be hashed)
        full_name: Admin full name
    
    Returns:
        User: The created or existing admin user
    """
    # Check if admin already exists
    existing_admin = session.exec(
        select(User).where(User.email == email)
    ).first()
    
    if existing_admin:
        print(f"Admin user with email {email} already exists.")
        return existing_admin
    
    # Create new admin user
    admin_user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
        phone="00000000",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)
    
    print(f"Admin user created successfully: {email}")
    return admin_user


def init_admin():
    # Create admin user
    with Session(engine) as session:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@salesfunnel.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "System Administrator")
        
        create_admin_user(
            session=session,
            email=admin_email,
            password=admin_password,
            full_name=admin_name
        )
    
    print("Database initialization completed.")


if __name__ == "__main__":
    init_admin()
