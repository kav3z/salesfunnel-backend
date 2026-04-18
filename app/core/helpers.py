# local imports
from app.core.config import settings
from app.models.audit_log import AuditLog
from app.core.database import get_db

# external imports
import pytz
from datetime import datetime
import cloudinary
from cloudinary import CloudinaryImage
import cloudinary.uploader
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException, status

load_dotenv()

config = cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def validate_file_type(allowed_ext, docs):
        for file, name in docs:
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{name} filename is missing"
                )
            file_ext = file.filename.split(".")[-1].lower()
            if file_ext not in allowed_ext:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{name} must be PDF, JPG, JPEG, or PNG"
                )
            
async def save_upload_file(upload_file: UploadFile, user_id: str, file_type: str, upload_dir: str) -> str:
    """Save uploaded file to Cloudinary and return the URL"""
    if not upload_file.filename:
        raise ValueError("Upload file must have a filename")
    
    public_id = f"{file_type}_{user_id}"
    
    # Upload file to Cloudinary
    result = cloudinary.uploader.upload(
        upload_file.file,
        folder=upload_dir,
        public_id=public_id,
        resource_type="auto",
        unique_filename=False,
        overwrite=True
    )
    
    # Use the full public_id from the response (includes folder path)
    full_public_id = result['public_id']
    cloudinary_url = CloudinaryImage(full_public_id).build_url()
    
    return cloudinary_url

def get_lagos_time():
    """Get current time in Lagos timezone without tzinfo"""
    return datetime.now(pytz.timezone('Africa/Lagos')).replace(tzinfo=None)

def audit_action(
    user_id, 
    user_email, 
    action_type, 
    entity_type, 
    entity_id, 
    old_value, 
    new_value,
    ip_address,
    user_agent,
    extra_data: Optional[dict] = None
):
    # Create a new session for this background task
    db_generator = get_db()
    db = next(db_generator)
    try:
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data=extra_data,
            )
            db.add(audit_log)
            db.commit()
            print("successfully audited")
        except Exception as e:
            print(f"Error during audit logging: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            db.rollback()  # Rollback in case of error
    finally:
        db.close()
        db_generator.close()