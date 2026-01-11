from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class ProductBase(BaseModel):
    """Base product schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    price_per_case: Decimal = Field(..., gt=0, decimal_places=2, description="Price per case")
    stock_quantity: int = Field(default=0, ge=0, description="Available stock quantity")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    image_url: Optional[str] = Field(None, description="Product image URL")
    is_available: bool = Field(default=True, description="Product availability status")


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    sku: str = Field(..., min_length=1, max_length=50, description="Stock Keeping Unit")


class ProductUpdate(BaseModel):
    """Schema for updating an existing product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_case: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class ProductResponse(BaseModel):
    """Schema for product response"""
    id: UUID
    sku: str
    name: str
    description: Optional[str]
    price_per_case: Decimal
    stock_quantity: int
    distributor_id: UUID
    category: Optional[str]
    image_url: Optional[str]
    is_available: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list response"""
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
