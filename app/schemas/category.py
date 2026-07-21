from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category Name")

class CategoryCreate(CategoryBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Beverages"
            }
        }
    )

class CategoryRead(CategoryBase):
    id: uuid.UUID
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "c11d71c9-e9e4-49d8-96be-8248f20d5a33",
                "name": "Beverages"
            }
        }
    )

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated Category Name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Soft Drinks & Beverages"
            }
        }
    )
