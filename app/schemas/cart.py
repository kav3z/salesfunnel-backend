from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class CartItemAdd(BaseModel):
    """Schema for adding a product to cart"""
    product_id: UUID = Field(..., description="Product UUID to add to cart")
    quantity: int = Field(..., gt=0, description="Quantity to add")


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    product_id: UUID = Field(..., description="Product UUID to update")
    quantity: int = Field(..., gt=0, description="New quantity")


class CartItemRemove(BaseModel):
    """Schema for removing a product from cart"""
    product_id: UUID = Field(..., description="Product UUID to remove")


class CartItemResponse(BaseModel):
    """Schema for cart item response"""
    cart_item_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    product_image_url: Optional[str]
    distributor_id: UUID
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    added_at: datetime
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Schema for full cart response"""
    id: UUID
    wholesaler_id: UUID
    items: List[CartItemResponse]
    total_items: int
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
