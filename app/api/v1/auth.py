# Local imports
from app.schemas.user import *
from app.schemas.wholesaler import WholesalerResponse
from app.schemas.distributor import DistributorResponse
from app.models.user import User, UserRole
from app.models.wholesaler_profile import WholesalerProfile
from app.models.distributor_profile import DistributorProfile
from app.schemas.user import *
from app.schemas.wholesaler import WholesalerResponse
from app.schemas.distributor import DistributorResponse
from app.core.dependencies import get_current_user, DBSession
from app.core.security import create_access_token, authenticate_user, hash_password, verify_password

# External imports
import os
import shutil
from sqlmodel import select
from typing import Annotated, List, Optional
from datetime import timedelta, datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr


v1_auth = APIRouter(prefix="/v1/auth", tags=['v1_auth'])

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

db_dependency = DBSession

# Directory for uploaded documents
WHOLESALER_UPLOAD_DIR = "uploads/wholesaler_documents"
DISTRIBUTOR_UPLOAD_DIR = "uploads/distributor_documents"
os.makedirs(WHOLESALER_UPLOAD_DIR, exist_ok=True)
os.makedirs(DISTRIBUTOR_UPLOAD_DIR, exist_ok=True)


async def save_upload_file(upload_file: UploadFile, user_id: str, file_type: str, upload_dir: str) -> str:
    """Save uploaded file and return the file path"""
    if not upload_file.filename:
        raise ValueError("Upload file must have a filename")
    
    file_extension = upload_file.filename.split(".")[-1]
    filename = f"{user_id}_{file_type}_{uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path


@v1_auth.post("/token", response_model=Token)
async def login_for_access_token(
    db: db_dependency,
    login_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Authenticate user with email and password.
    
    Returns:
        Token: Access token and token type
    """
    user = authenticate_user(login_data.username, login_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    token = create_access_token(
        email=user.email,
        user_id=str(user.id),
        user_role=user.role.value,
        is_active=user.is_active,
        full_name=user.full_name,
        expires_delta=timedelta(minutes=30)
    )
    
    return Token(
        user_id=str(user.id),
        access_token=token,
        token_type="bearer",
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


@v1_auth.post("/register-wholesaler", status_code=status.HTTP_201_CREATED, response_model=WholesalerResponse)
async def register_wholesaler(
    db: db_dependency,
    background_tasks: BackgroundTasks,
    # Form data fields
    password: str = Form(..., min_length=8, max_length=72),
    business_name: str = Form(..., min_length=2, max_length=255),
    cac_registration_number: str = Form(..., min_length=5, max_length=50),
    business_address: str = Form(..., min_length=10, max_length=500),
    business_phone: str = Form(..., min_length=10, max_length=20),
    business_email: str = Form(...),
    tin: str = Form(..., min_length=5, max_length=50),
    owner_full_name: str = Form(..., min_length=2, max_length=255),
    owner_phone: str = Form(..., min_length=10, max_length=20),
    owner_email: str = Form(...),
    bank_name: str = Form(..., min_length=2, max_length=100),
    account_name: str = Form(..., min_length=2, max_length=255),
    account_number: str = Form(..., min_length=10, max_length=20),
    # File uploads
    cac_certificate: UploadFile = File(..., description="CAC Certificate"),
    tin_certificate: UploadFile = File(..., description="TIN Certificate"),
    utility_bill: UploadFile = File(..., description="Utility Bill or Proof of Address"),
):
    """
    Register a new wholesaler with complete business information and documents.
    
    Required Documents:
    - CAC Certificate
    - TIN Certificate  
    - Utility Bill (Proof of Address)
    """
    
    # Check if user already exists (by business email or owner email)
    existing_user = db.exec(
        select(User).where(
            (User.email == business_email) | (User.email == owner_email)
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if CAC number already exists
    existing_cac = db.exec(
        select(WholesalerProfile).where(
            WholesalerProfile.cac_registration_number == cac_registration_number
        )
    ).first()
    
    if existing_cac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAC Registration Number already registered"
        )
    
    # Check if TIN already exists
    existing_tin = db.exec(
        select(WholesalerProfile).where(WholesalerProfile.tin == tin)
    ).first()
    
    if existing_tin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TIN already registered"
        )
    
    # Validate file types
    allowed_extensions = {"pdf", "jpg", "jpeg", "png"}
    for file, name in [
        (cac_certificate, "CAC Certificate"),
        (tin_certificate, "TIN Certificate"),
        (utility_bill, "Utility Bill")
    ]:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name} filename is missing"
            )
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name} must be PDF, JPG, JPEG, or PNG"
            )
    
    # Create User account
    new_user = User(
        email=owner_email,
        password_hash=hash_password(password),
        full_name=owner_full_name,
        phone=owner_phone,
        role=UserRole.WHOLESALER,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Save uploaded documents
    try:
        cac_certificate_path = await save_upload_file(
            cac_certificate, str(new_user.id), "cac_certificate", WHOLESALER_UPLOAD_DIR
        )
        tin_certificate_path = await save_upload_file(
            tin_certificate, str(new_user.id), "tin_certificate", WHOLESALER_UPLOAD_DIR
        )
        utility_bill_path = await save_upload_file(
            utility_bill, str(new_user.id), "utility_bill", WHOLESALER_UPLOAD_DIR
        )
    except Exception as e:
        # Rollback user creation if file upload fails
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload documents: {str(e)}"
        )
    
    # Create Wholesaler Profile
    wholesaler_profile = WholesalerProfile(
        user_id=new_user.id,
        business_name=business_name,
        cac_registration_number=cac_registration_number,
        business_address=business_address,
        business_phone=business_phone,
        business_email=business_email,
        tin=tin,
        owner_full_name=owner_full_name,
        owner_phone=owner_phone,
        owner_email=owner_email,
        bank_name=bank_name,
        account_name=account_name,
        account_number=account_number,
        cac_certificate_url=cac_certificate_path,
        tin_certificate_url=tin_certificate_path,
        utility_bill_url=utility_bill_path,
        is_verified=False
    )
    
    db.add(wholesaler_profile)
    db.commit()
    db.refresh(wholesaler_profile)
    
    # TODO: Add background task to send verification email
    # background_tasks.add_task(send_verification_email, owner_email, business_name)
    
    return WholesalerResponse(
        id=str(wholesaler_profile.id),
        user_id=str(wholesaler_profile.user_id),
        business_name=wholesaler_profile.business_name,
        cac_registration_number=wholesaler_profile.cac_registration_number,
        business_address=wholesaler_profile.business_address,
        business_phone=wholesaler_profile.business_phone,
        business_email=wholesaler_profile.business_email,
        tin=wholesaler_profile.tin,
        owner_full_name=wholesaler_profile.owner_full_name,
        owner_phone=wholesaler_profile.owner_phone,
        owner_email=wholesaler_profile.owner_email,
        bank_name=wholesaler_profile.bank_name,
        account_name=wholesaler_profile.account_name,
        account_number=wholesaler_profile.account_number,
        is_verified=wholesaler_profile.is_verified,
        cac_certificate_url=wholesaler_profile.cac_certificate_url,
        tin_certificate_url=wholesaler_profile.tin_certificate_url,
        utility_bill_url=wholesaler_profile.utility_bill_url
    )


@v1_auth.post("/register-distributor", status_code=status.HTTP_201_CREATED, response_model=DistributorResponse)
async def register_distributor(
    db: db_dependency,
    background_tasks: BackgroundTasks,
    # Form data fields
    password: str = Form(..., min_length=8, max_length=72),
    business_name: str = Form(..., min_length=2, max_length=255),
    cac_registration_number: str = Form(..., min_length=5, max_length=50),
    business_address: str = Form(..., min_length=10, max_length=500),
    business_phone: str = Form(..., min_length=10, max_length=20),
    business_email: str = Form(...),
    tin: str = Form(..., min_length=5, max_length=50),
    owner_full_name: str = Form(..., min_length=2, max_length=255),
    owner_phone: str = Form(..., min_length=10, max_length=20),
    owner_email: str = Form(...),
    bank_name: str = Form(..., min_length=2, max_length=100),
    account_name: str = Form(..., min_length=2, max_length=255),
    account_number: str = Form(..., min_length=10, max_length=20),
    # File uploads
    cac_certificate: UploadFile = File(..., description="CAC Certificate"),
    tin_certificate: UploadFile = File(..., description="TIN Certificate"),
    utility_bill: UploadFile = File(..., description="Utility Bill or Proof of Address"),
):
    """
    Register a new distributor with complete business information and documents.
    
    Required Documents:
    - CAC Certificate
    - TIN Certificate  
    - Utility Bill (Proof of Address)
    """
    
    # Check if user already exists (by business email or owner email)
    existing_user = db.exec(
        select(User).where(
            (User.email == business_email) | (User.email == owner_email)
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if CAC number already exists in distributor profiles
    existing_cac = db.exec(
        select(DistributorProfile).where(
            DistributorProfile.cac_registration_number == cac_registration_number
        )
    ).first()
    
    if existing_cac:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAC Registration Number already registered"
        )
    
    # Check if TIN already exists in distributor profiles
    existing_tin = db.exec(
        select(DistributorProfile).where(DistributorProfile.tin == tin)
    ).first()
    
    if existing_tin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TIN already registered"
        )
    
    # Validate file types
    allowed_extensions = {"pdf", "jpg", "jpeg", "png"}
    for file, name in [
        (cac_certificate, "CAC Certificate"),
        (tin_certificate, "TIN Certificate"),
        (utility_bill, "Utility Bill")
    ]:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name} filename is missing"
            )
        
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{name} must be PDF, JPG, JPEG, or PNG"
            )
    
    # Create User account
    new_user = User(
        email=owner_email,
        password_hash=hash_password(password),
        full_name=owner_full_name,
        phone=owner_phone,
        role=UserRole.DISTRIBUTOR,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Save uploaded documents
    try:
        cac_certificate_path = await save_upload_file(
            cac_certificate, str(new_user.id), "cac_certificate", DISTRIBUTOR_UPLOAD_DIR
        )
        tin_certificate_path = await save_upload_file(
            tin_certificate, str(new_user.id), "tin_certificate", DISTRIBUTOR_UPLOAD_DIR
        )
        utility_bill_path = await save_upload_file(
            utility_bill, str(new_user.id), "utility_bill", DISTRIBUTOR_UPLOAD_DIR
        )
    except Exception as e:
        # Rollback user creation if file upload fails
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload documents: {str(e)}"
        )
    
    # Create Distributor Profile
    distributor_profile = DistributorProfile(
        user_id=new_user.id,
        business_name=business_name,
        cac_registration_number=cac_registration_number,
        business_address=business_address,
        business_phone=business_phone,
        business_email=business_email,
        tin=tin,
        owner_full_name=owner_full_name,
        owner_phone=owner_phone,
        owner_email=owner_email,
        bank_name=bank_name,
        account_name=account_name,
        account_number=account_number,
        cac_certificate_url=cac_certificate_path,
        tin_certificate_url=tin_certificate_path,
        utility_bill_url=utility_bill_path,
        is_verified=False
    )
    
    db.add(distributor_profile)
    db.commit()
    db.refresh(distributor_profile)
    
    # TODO: Add background task to send verification email
    # background_tasks.add_task(send_verification_email, owner_email, business_name)
    
    return DistributorResponse(
        id=str(distributor_profile.id),
        user_id=str(distributor_profile.user_id),
        business_name=distributor_profile.business_name,
        cac_registration_number=distributor_profile.cac_registration_number,
        business_address=distributor_profile.business_address,
        business_phone=distributor_profile.business_phone,
        business_email=distributor_profile.business_email,
        tin=distributor_profile.tin,
        owner_full_name=distributor_profile.owner_full_name,
        owner_phone=distributor_profile.owner_phone,
        owner_email=distributor_profile.owner_email,
        bank_name=distributor_profile.bank_name,
        account_name=distributor_profile.account_name,
        account_number=distributor_profile.account_number,
        is_verified=distributor_profile.is_verified,
        cac_certificate_url=distributor_profile.cac_certificate_url,
        tin_certificate_url=distributor_profile.tin_certificate_url,
        utility_bill_url=distributor_profile.utility_bill_url
    )


@v1_auth.get("/users/profile", response_model=UserProfileResponse)
async def get_user_profile(
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's complete profile information.
    
    Returns user info along with wholesaler or distributor profile if applicable.
    """
    user_id = current_user.id
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Build base response
    response = UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
    
    # Get wholesaler profile if user is a wholesaler
    if user.role == UserRole.WHOLESALER:
        wholesaler_profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        
        if wholesaler_profile:
            response.wholesaler_profile = WholesalerProfileData(
                id=str(wholesaler_profile.id),
                business_name=wholesaler_profile.business_name,
                cac_registration_number=wholesaler_profile.cac_registration_number,
                business_address=wholesaler_profile.business_address,
                business_phone=wholesaler_profile.business_phone,
                business_email=wholesaler_profile.business_email,
                tin=wholesaler_profile.tin,
                owner_full_name=wholesaler_profile.owner_full_name,
                owner_phone=wholesaler_profile.owner_phone,
                owner_email=wholesaler_profile.owner_email,
                bank_name=wholesaler_profile.bank_name,
                account_name=wholesaler_profile.account_name,
                account_number=wholesaler_profile.account_number,
                is_verified=wholesaler_profile.is_verified,
                cac_certificate_url=wholesaler_profile.cac_certificate_url,
                tin_certificate_url=wholesaler_profile.tin_certificate_url,
                utility_bill_url=wholesaler_profile.utility_bill_url
            )
    
    # Get distributor profile if user is a distributor
    elif user.role == UserRole.DISTRIBUTOR:
        distributor_profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        
        if distributor_profile:
            response.distributor_profile = DistributorProfileData(
                id=str(distributor_profile.id),
                business_name=distributor_profile.business_name,
                cac_registration_number=distributor_profile.cac_registration_number,
                business_address=distributor_profile.business_address,
                business_phone=distributor_profile.business_phone,
                business_email=distributor_profile.business_email,
                tin=distributor_profile.tin,
                owner_full_name=distributor_profile.owner_full_name,
                owner_phone=distributor_profile.owner_phone,
                owner_email=distributor_profile.owner_email,
                bank_name=distributor_profile.bank_name,
                account_name=distributor_profile.account_name,
                account_number=distributor_profile.account_number,
                is_verified=distributor_profile.is_verified,
                cac_certificate_url=distributor_profile.cac_certificate_url,
                tin_certificate_url=distributor_profile.tin_certificate_url,
                utility_bill_url=distributor_profile.utility_bill_url
            )
    
    return response


@v1_auth.put("/users/profile", response_model=UserProfileResponse)
async def update_user_profile(
    db: db_dependency,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile information.
    
    Can update basic user info and business profile details.
    """
    user_id = current_user.id
    user = db.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update basic user info
    if profile_update.full_name is not None:
        user.full_name = profile_update.full_name
    if profile_update.phone is not None:
        user.phone = profile_update.phone
    
    user.updated_at = datetime.utcnow()
    db.add(user)
    
    # Update wholesaler profile if applicable
    if user.role == UserRole.WHOLESALER and profile_update.wholesaler_profile is not None:
        wholesaler_profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        
        if wholesaler_profile:
            update_data = profile_update.wholesaler_profile
            
            if update_data.business_name is not None:
                wholesaler_profile.business_name = update_data.business_name
            if update_data.business_address is not None:
                wholesaler_profile.business_address = update_data.business_address
            if update_data.business_phone is not None:
                wholesaler_profile.business_phone = update_data.business_phone
            if update_data.business_email is not None:
                wholesaler_profile.business_email = update_data.business_email
            if update_data.owner_full_name is not None:
                wholesaler_profile.owner_full_name = update_data.owner_full_name
            if update_data.owner_phone is not None:
                wholesaler_profile.owner_phone = update_data.owner_phone
            if update_data.owner_email is not None:
                wholesaler_profile.owner_email = update_data.owner_email
            if update_data.bank_name is not None:
                wholesaler_profile.bank_name = update_data.bank_name
            if update_data.account_name is not None:
                wholesaler_profile.account_name = update_data.account_name
            if update_data.account_number is not None:
                wholesaler_profile.account_number = update_data.account_number
            
            wholesaler_profile.updated_at = datetime.utcnow()
            db.add(wholesaler_profile)
    
    # Update distributor profile if applicable
    elif user.role == UserRole.DISTRIBUTOR and profile_update.distributor_profile is not None:
        distributor_profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        
        if distributor_profile:
            update_data = profile_update.distributor_profile
            
            if update_data.business_name is not None:
                distributor_profile.business_name = update_data.business_name
            if update_data.business_address is not None:
                distributor_profile.business_address = update_data.business_address
            if update_data.business_phone is not None:
                distributor_profile.business_phone = update_data.business_phone
            if update_data.business_email is not None:
                distributor_profile.business_email = update_data.business_email
            if update_data.owner_full_name is not None:
                distributor_profile.owner_full_name = update_data.owner_full_name
            if update_data.owner_phone is not None:
                distributor_profile.owner_phone = update_data.owner_phone
            if update_data.owner_email is not None:
                distributor_profile.owner_email = update_data.owner_email
            if update_data.bank_name is not None:
                distributor_profile.bank_name = update_data.bank_name
            if update_data.account_name is not None:
                distributor_profile.account_name = update_data.account_name
            if update_data.account_number is not None:
                distributor_profile.account_number = update_data.account_number
            
            distributor_profile.updated_at = datetime.utcnow()
            db.add(distributor_profile)
    
    db.commit()
    
    # Return updated profile
    return await get_user_profile(db, current_user)

