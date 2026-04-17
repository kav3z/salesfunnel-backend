from app.core.config import settings

import cloudinary
from cloudinary import CloudinaryImage
import cloudinary.uploader
import os
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
