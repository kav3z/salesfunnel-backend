# internal imports 
from app.models.user import UserRole

# external imports
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    role: UserRole


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str
    role: UserRole
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str