# Local imports
from app.schemas.user import UserResponse, UserProfileResponse, WholesalerProfileData, DistributorProfileData
from app.schemas.order import OrderResponse, OrderDetailResponse, OrderItemResponse, OrderListResponse, OrderStatusUpdate
from app.schemas.admin import (
    AdminUserResponse,
    AdminUserListResponse,
    AdminOrderResponse,
    AdminOrderListResponse,
    OrderStatusOverride
)
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product
from app.models.wholesaler_profile import WholesalerProfile
from app.models.distributor_profile import DistributorProfile
from app.core.dependencies import get_current_user, DBSession

# External imports
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from math import ceil
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, func


v1_admin = APIRouter(prefix="/v1/admin", tags=['v1_admin'])

db_dependency = DBSession



def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@v1_admin.get("/users", response_model=AdminUserListResponse, status_code=status.HTTP_200_OK)
async def get_all_users(
    db: db_dependency,
    current_user: User = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    role_filter: Optional[UserRole] = Query(default=None, description="Filter by user role"),
    active_only: bool = Query(default=False, description="Show only active users"),
    search: Optional[str] = Query(default=None, description="Search by name or email")
):
    """
    View all users (wholesalers & distributors).
    
    Admin only endpoint.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        role_filter: Optional filter by role (wholesaler, distributor)
        active_only: If True, only return active users
        search: Optional search term for name or email
    
    Returns:
        AdminUserListResponse: Paginated list of users
    """
    # Build query - exclude admin users from list
    query = select(User).where(User.role != UserRole.ADMIN)
    count_query = select(func.count(User.id)).where(User.role != UserRole.ADMIN) # type: ignore
    
    # Apply filters
    if role_filter and role_filter != UserRole.ADMIN:
        query = query.where(User.role == role_filter)
        count_query = count_query.where(User.role == role_filter)
    
    if active_only:
        query = query.where(User.is_active == True)
        count_query = count_query.where(User.is_active == True)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.full_name.ilike(search_pattern)) | (User.email.ilike(search_pattern))# type: ignore
        )
        count_query = count_query.where(
            (User.full_name.ilike(search_pattern)) | (User.email.ilike(search_pattern))# type: ignore
        )
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)# type: ignore
    
    # Execute query
    users = db.exec(query).all()
    
    # Build response with business info
    users_response = []
    for user in users:
        business_name = None
        is_verified = None
        
        if user.role == UserRole.WHOLESALER:
            profile = db.exec(
                select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
            ).first()
            if profile:
                business_name = profile.business_name
                is_verified = profile.is_verified
        elif user.role == UserRole.DISTRIBUTOR:
            profile = db.exec(
                select(DistributorProfile).where(DistributorProfile.user_id == user.id)
            ).first()
            if profile:
                business_name = profile.business_name
                is_verified = profile.is_verified
        
        users_response.append(AdminUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            business_name=business_name,
            is_verified=is_verified
        ))
    
    return AdminUserListResponse(
        users=users_response,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_admin.get("/orders", response_model=AdminOrderListResponse, status_code=status.HTTP_200_OK)
async def get_all_orders(
    db: db_dependency,
    current_user: User = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[OrderStatus] = Query(default=None, description="Filter by order status"),
    payment_status_filter: Optional[PaymentStatus] = Query(default=None, description="Filter by payment status")
):
    """
    View all orders and their payment statuses.
    
    Admin only endpoint.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        status_filter: Optional filter by order status
        payment_status_filter: Optional filter by payment status
    
    Returns:
        AdminOrderListResponse: Paginated list of orders with payment info
    """
    # Build query
    query = select(Order)
    count_query = select(func.count(Order.id)) # type: ignore
    
    # Apply order status filter
    if status_filter:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)
    
    # Get total count (before payment filter which requires join)
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    orders = db.exec(query).all()
    
    # Build response with payment info
    orders_response = []
    for order in orders:
        # Get payment info
        payment = db.exec(
            select(Payment).where(Payment.order_id == order.id)
        ).first()
        
        # Skip if payment status filter is set and doesn't match
        if payment_status_filter:
            if not payment or payment.status != payment_status_filter:
                continue
        
        # Get wholesaler name
        wholesaler = db.exec(
            select(User).where(User.id == order.wholesaler_id)
        ).first()
        
        # Get distributor name
        distributor = db.exec(
            select(User).where(User.id == order.distributor_id)
        ).first()
        
        orders_response.append(AdminOrderResponse(
            id=order.id,
            order_number=order.order_number,
            wholesaler_id=order.wholesaler_id,
            wholesaler_name=wholesaler.full_name if wholesaler else None,
            distributor_id=order.distributor_id,
            distributor_name=distributor.full_name if distributor else None,
            total_amount=order.total_amount,
            status=order.status,
            payment_status=payment.status if payment else None,
            payment_reference=payment.reference_number if payment else None,
            notes=order.notes,
            created_at=order.created_at,
            paid_at=order.paid_at
        ))
    
    return AdminOrderListResponse(
        orders=orders_response,
        total=len(orders_response) if payment_status_filter else total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_admin.post("/orders/{order_id}/override-status", response_model=AdminOrderResponse, status_code=status.HTTP_200_OK)
async def override_order_status(
    order_id: UUID,
    override_data: OrderStatusOverride,
    db: db_dependency,
    current_user: User = Depends(require_admin)
):
    """
    Manually override order status for dispute resolution.
    
    Admin only endpoint. Requires a reason for the override.
    
    Args:
        order_id: UUID of the order
        override_data: New status and reason for override
    
    Returns:
        AdminOrderResponse: Updated order details
        
    Raises:
        HTTPException 404: If order not found
    """
    # Find the order
    order = db.exec(
        select(Order).where(Order.id == order_id)
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    old_status = order.status
    
    # Update order status
    order.status = override_data.status
    
    # Update relevant timestamps based on new status
    now = datetime.utcnow()
    if override_data.status == OrderStatus.PAID:
        order.paid_at = now
    elif override_data.status == OrderStatus.APPROVED:
        order.approved_at = now
    elif override_data.status == OrderStatus.READY_FOR_PICKUP:
        order.ready_at = now
    elif override_data.status == OrderStatus.COMPLETED:
        order.completed_at = now
    elif override_data.status == OrderStatus.CANCELLED:
        order.cancelled_at = now
    
    # Append override reason to notes
    override_note = f"\n[ADMIN OVERRIDE {now.strftime('%Y-%m-%d %H:%M')}] Status changed from {old_status.value} to {override_data.status.value}. Reason: {override_data.reason}"
    order.notes = (order.notes or "") + override_note
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Get payment info
    payment = db.exec(
        select(Payment).where(Payment.order_id == order.id)
    ).first()
    
    # Get wholesaler and distributor names
    wholesaler = db.exec(select(User).where(User.id == order.wholesaler_id)).first()
    distributor = db.exec(select(User).where(User.id == order.distributor_id)).first()
    
    return AdminOrderResponse(
        id=order.id,
        order_number=order.order_number,
        wholesaler_id=order.wholesaler_id,
        wholesaler_name=wholesaler.full_name if wholesaler else None,
        distributor_id=order.distributor_id,
        distributor_name=distributor.full_name if distributor else None,
        total_amount=order.total_amount,
        status=order.status,
        payment_status=payment.status if payment else None,
        payment_reference=payment.reference_number if payment else None,
        notes=order.notes,
        created_at=order.created_at,
        paid_at=order.paid_at
    )


@v1_admin.put("/users/{user_id}/block", response_model=AdminUserResponse, status_code=status.HTTP_200_OK)
async def block_user(
    user_id: UUID,
    db: db_dependency,
    current_user: User = Depends(require_admin)
):
    """
    Block a user account.
    
    Admin only endpoint. Sets user's is_active to False.
    
    Args:
        user_id: UUID of the user to block
    
    Returns:
        AdminUserResponse: Updated user details
        
    Raises:
        HTTPException 404: If user not found
        HTTPException 400: If trying to block an admin or already blocked
    """
    # Find the user
    user = db.exec(
        select(User).where(User.id == user_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot block admin users
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block admin users"
        )
    
    # Check if already blocked
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already blocked"
        )
    
    # Block the user
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Get business info
    business_name = None
    is_verified = None
    
    if user.role == UserRole.WHOLESALER:
        profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        if profile:
            business_name = profile.business_name
            is_verified = profile.is_verified
    elif user.role == UserRole.DISTRIBUTOR:
        profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        if profile:
            business_name = profile.business_name
            is_verified = profile.is_verified
    
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        business_name=business_name,
        is_verified=is_verified
    )


@v1_admin.put("/users/{user_id}/unblock", response_model=AdminUserResponse, status_code=status.HTTP_200_OK)
async def unblock_user(
    user_id: UUID,
    db: db_dependency,
    current_user: User = Depends(require_admin)
):
    """
    Unblock a user account.
    
    Admin only endpoint. Sets user's is_active to True.
    
    Args:
        user_id: UUID of the user to unblock
    
    Returns:
        AdminUserResponse: Updated user details
        
    Raises:
        HTTPException 404: If user not found
        HTTPException 400: If user is not blocked
    """
    # Find the user
    user = db.exec(
        select(User).where(User.id == user_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already active
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not blocked"
        )
    
    # Unblock the user
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Get business info
    business_name = None
    is_verified = None
    
    if user.role == UserRole.WHOLESALER:
        profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        if profile:
            business_name = profile.business_name
            is_verified = profile.is_verified
    elif user.role == UserRole.DISTRIBUTOR:
        profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        if profile:
            business_name = profile.business_name
            is_verified = profile.is_verified
    
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        business_name=business_name,
        is_verified=is_verified
    )


@v1_admin.put("/users/{user_id}/verify", response_model=AdminUserResponse, status_code=status.HTTP_200_OK)
async def verify_user(
    user_id: UUID,
    db: db_dependency,
    current_user: User = Depends(require_admin)
):
    """
    Verify a user's business profile (Wholesaler or Distributor).
    
    Admin only endpoint. Sets is_verified to True on the profile.
    """
    # Find the user
    user = db.exec(
        select(User).where(User.id == user_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check role and get profile
    profile = None
    business_name = None
    
    if user.role == UserRole.WHOLESALER:
        profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wholesaler profile not found"
            )
    elif user.role == UserRole.DISTRIBUTOR:
        profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        if not profile:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distributor profile not found"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify this user role"
        )
        
    # Check if already verified
    if profile.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified"
        )
    
    # Verify the profile
    profile.is_verified = True
    profile.updated_at = datetime.utcnow()
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    business_name = profile.business_name
    
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        business_name=business_name,
        is_verified=True
    )


@v1_admin.put("/users/{user_id}/unverify", response_model=AdminUserResponse, status_code=status.HTTP_200_OK)
async def unverify_user(
    user_id: UUID,
    db: db_dependency,
    current_user: User = Depends(require_admin)
):
    """
    Unverify a user's business profile (Wholesaler or Distributor).
    
    Admin only endpoint. Sets is_verified to False on the profile.
    """
    # Find the user
    user = db.exec(
        select(User).where(User.id == user_id)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check role and get profile
    profile = None
    business_name = None
    
    if user.role == UserRole.WHOLESALER:
        profile = db.exec(
            select(WholesalerProfile).where(WholesalerProfile.user_id == user.id)
        ).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wholesaler profile not found"
            )
    elif user.role == UserRole.DISTRIBUTOR:
        profile = db.exec(
            select(DistributorProfile).where(DistributorProfile.user_id == user.id)
        ).first()
        if not profile:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distributor profile not found"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unverify this user role"
        )
        
    # Check if currently unverified
    if not profile.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not currently verified"
        )
    
    # Unverify the profile
    profile.is_verified = False
    profile.updated_at = datetime.utcnow()
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    business_name = profile.business_name
    
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        business_name=business_name,
        is_verified=False
    )
