from typing import Optional
from sqlmodel import SQLModel
import uuid

class CategoryBase(SQLModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: uuid.UUID
    
    class Config:
        from_attributes = True

class CategoryUpdate(SQLModel):
    name: Optional[str] = None
