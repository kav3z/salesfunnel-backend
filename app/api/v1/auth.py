# Local imports
from app.models.user import User
from app.schemas.user import *
from app.core.dependencies import get_current_user, DBSession
from app.core.security import create_access_token, authenticate_user, hash_password, verify_password

# External imports
from sqlmodel import select
from typing import Annotated
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


v1_auth = APIRouter(prefix="/v1/auth", tags=['v1_auth'])

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

db_dependency = DBSession


@v1_auth.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(
    db: db_dependency,
    create_user_request: UserCreate,
    background_tasks: BackgroundTasks
):
    """Register a new user (wholesaler or distributor)"""
    # Check if user already exists
    existing_user = db.exec(
        select(User).where(User.email == create_user_request.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    
    # Create new user
    new_user = User(
        email=create_user_request.email,
        password_hash=hash_password(create_user_request.password),
        full_name=create_user_request.full_name,
        phone=create_user_request.phone, 
        role=create_user_request.role,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        phone=new_user.phone,
        role=new_user.role,
        is_active=new_user.is_active
    )


@v1_auth.post("/token", response_model=Token)
async def login_for_access_token(
    db: db_dependency,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """Login endpoint - username field should contain email"""
    # OAuth2PasswordRequestForm uses 'username' field, but we use it for email
    user = authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )
    
    # Create access token
    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        user_role=user.role.value,
        full_name=user.full_name,
        is_active=user.is_active,
        expires_delta=timedelta(minutes=60)
    )
    
    return {"access_token": token, "token_type": "bearer"}


@v1_auth.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information"""
    user_id = current_user.id 
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active
    )


@v1_auth.patch("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    current_password: str,
    new_password: str,
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """Update user password"""
    user_id = current_user.id
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    
    db.add(user)
    db.commit()
    
    return {"detail": "Password successfully updated"}

