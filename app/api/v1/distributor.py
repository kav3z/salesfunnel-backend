# Local imports
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.schemas.distributor import DistributorListResponse
from app.models.product import Product
from app.models.user import User, UserRole
from app.models.distributor_profile import DistributorProfile
from app.core.dependencies import get_current_user, DBSession, require_role, CurrentUser, DistributorUser
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.schemas.order import OrderResponse, OrderDetailResponse, OrderListResponse, OrderStatusUpdate, OrderItemResponse

# External imports
from typing import Annotated, Optional, List
from uuid import UUID
from math import ceil
from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, func, or_, desc


v1_distributor = APIRouter(prefix="/v1", tags=['v1_distributor'])

db_dependency = DBSession


@v1_distributor.get("/products", response_model=ProductListResponse, status_code=status.HTTP_200_OK)
async def get_all_products(
    db: db_dependency,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    distributor_id: Optional[UUID] = Query(default=None, description="Filter by distributor"),
    search: Optional[str] = Query(default=None, description="Search by product name"),
    available_only: bool = Query(default=True, description="Show only available products")
):
    """
    Retrieve a list of all products with optional filtering and pagination.
    
    This endpoint is used for the "All Products / Distributor Selection" view.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        category: Optional category filter
        distributor_id: Optional distributor filter
        search: Optional search term for product name
        available_only: If True, only return available products
    
    Returns:
        ProductListResponse: Paginated list of products
    """
    # Build base query
    query = select(Product)
    count_query = select(func.count()).select_from(Product)
    
    # Apply filters
    if available_only:
        query = query.where(Product.is_available == True)
        count_query = count_query.where(Product.is_available == True)
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    
    if distributor_id:
        query = query.where(Product.distributor_id == distributor_id)
        count_query = count_query.where(Product.distributor_id == distributor_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Product.name.ilike(search_pattern)) # type: ignore
        count_query = count_query.where(Product.name.ilike(search_pattern)) # type: ignore
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    products = db.exec(query).all()
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_distributor.post(
    "/distributors/{distributor_id}/products", 
    response_model=ProductResponse, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR, UserRole.ADMIN]))]
)
async def add_product_to_distributor_catalog(
    distributor_id: UUID,
    product_data: ProductCreate,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Add a new product to a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own catalog) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_data: Product creation data
    
    Returns:
        ProductResponse: The created product
        
    Raises:
        HTTPException 403: If user is not authorized to add products
        HTTPException 404: If distributor not found
        HTTPException 409: If SKU already exists
    """
    # Additional check for Distributor trying to add to another's catalog
    if current_user.role == UserRole.DISTRIBUTOR and current_user.id != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add products to your own catalog"
        )
    
    # Verify distributor exists and has the correct role
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Check if SKU already exists
    existing_product = db.exec(
        select(Product).where(Product.sku == product_data.sku)
    ).first()
    
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_data.sku}' already exists"
        )
    
    # Create new product
    new_product = Product(
        sku=product_data.sku,
        name=product_data.name,
        description=product_data.description,
        price_per_case=product_data.price_per_case,
        stock_quantity=product_data.stock_quantity,
        distributor_id=distributor_id,
        category=product_data.category,
        image_url=product_data.image_url,
        is_available=product_data.is_available
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return ProductResponse.model_validate(new_product)


@v1_distributor.get(
    "/distributors/{distributor_id}/products",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK
)
async def get_distributor_products(
    distributor_id: UUID,
    db: db_dependency,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search by product name"),
    available_only: bool = Query(default=False, description="Show only available products")
):
    """
    Retrieve a list of products for a specific distributor.
    
    This endpoint is used for the "Distributor Product Catalog" view.
    
    Args:
        distributor_id: UUID of the distributor
        page: Page number for pagination
        page_size: Number of items per page
        category: Optional category filter
        search: Optional search term for product name
        available_only: If True, only return available products
    
    Returns:
        ProductListResponse: Paginated list of distributor's products
    """
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Build base query filtered by distributor
    query = select(Product).where(Product.distributor_id == distributor_id)
    count_query = select(func.count()).select_from(Product).where(Product.distributor_id == distributor_id)
    
    # Apply filters
    if available_only:
        query = query.where(Product.is_available == True)
        count_query = count_query.where(Product.is_available == True)
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Product.name.ilike(search_pattern)) # type: ignore
        count_query = count_query.where(Product.name.ilike(search_pattern)) # type: ignore
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    products = db.exec(query).all()
    
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_distributor.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
async def get_product_details(
    product_id: UUID,
    db: db_dependency
):
    """
    Retrieve details of a single product.
    
    This endpoint is used for the "Wholesaler Product Detail Page".
    
    Args:
        product_id: UUID of the product
    
    Returns:
        ProductResponse: Product details
        
    Raises:
        HTTPException 404: If product not found
    """
    product = db.exec(
        select(Product).where(Product.id == product_id)
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductResponse.model_validate(product)


@v1_distributor.get(
    "/distributors",
    response_model=List[DistributorListResponse],
    status_code=status.HTTP_200_OK
)
async def get_all_distributors(
    db: db_dependency,
    verified_only: bool = Query(default=True, description="Show only verified distributors"),
    search: Optional[str] = Query(default=None, description="Search by business name")
):
    """
    Retrieve a list of all distributors.
    
    This endpoint returns all distributors including popular ones.
    
    Args:
        verified_only: If True, only return verified distributors
        search: Optional search term for business name
    
    Returns:
        List[DistributorListResponse]: List of distributors
    """
    # Build query for distributor profiles
    query = select(DistributorProfile)
    
    # Apply filters
    if verified_only:
        query = query.where(DistributorProfile.is_verified == True)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(DistributorProfile.business_name.ilike(search_pattern)) # type: ignore
    
    # Order by business name
    query = query.order_by(DistributorProfile.business_name)
    
    # Execute query
    distributors = db.exec(query).all()
    
    return [
        DistributorListResponse(
            id=str(d.id),
            business_name=d.business_name,
            business_address=d.business_address,
            business_phone=d.business_phone,
            business_email=d.business_email,
            is_verified=d.is_verified
        )
        for d in distributors
    ]


@v1_distributor.put(
    "/distributors/{distributor_id}/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR, UserRole.ADMIN]))]
)
async def update_distributor_product(
    distributor_id: UUID,
    product_id: UUID,
    product_data: ProductUpdate,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Update product details for a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own products) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_id: UUID of the product to update
        product_data: Product update data
    
    Returns:
        ProductResponse: Updated product details
        
    Raises:
        HTTPException 403: If user is not authorized to update products
        HTTPException 404: If distributor or product not found
    """
    # Additional check for Distributor trying to update another's catalog
    if current_user.role == UserRole.DISTRIBUTOR and current_user.id != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update products in your own catalog"
        )
    
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Find the product
    product = db.exec(
        select(Product).where(
            Product.id == product_id,
            Product.distributor_id == distributor_id
        )
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this distributor's catalog"
        )
    
    # Update only provided fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Update timestamp
    product.updated_at = datetime.utcnow()
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@v1_distributor.delete(
    "/distributors/{distributor_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR, UserRole.ADMIN]))]
)
async def delete_distributor_product(
    distributor_id: UUID,
    product_id: UUID,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Remove a product from a distributor's catalog.
    
    This endpoint is restricted to Distributors (for their own products) and Admins.
    
    Args:
        distributor_id: UUID of the distributor
        product_id: UUID of the product to remove
        
    Raises:
        HTTPException 403: If user is not authorized to delete products
        HTTPException 404: If distributor or product not found
    """
    # Additional check for Distributor trying to delete from another's catalog
    if current_user.role == UserRole.DISTRIBUTOR and current_user.id != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete products from your own catalog"
        )
    
    # Verify distributor exists
    distributor = db.exec(
        select(User).where(User.id == distributor_id, User.role == UserRole.DISTRIBUTOR)
    ).first()
    
    if not distributor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distributor not found"
        )
    
    # Find the product
    product = db.exec(
        select(Product).where(
            Product.id == product_id,
            Product.distributor_id == distributor_id
        )
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this distributor's catalog"
        )
    
    db.delete(product)
    db.commit()
    
    return None


@v1_distributor.get(
    "/distributor/orders/new",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    # Here we can just use DistributorUser as the type for current_user if it was defined as a param
    # But since current_user is passed as param, we can use dependency in path
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR]))]
)
async def get_new_distributor_orders(
    db: db_dependency,
    current_user: CurrentUser, # Already validated as Distributor by path dependency
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page")
):
    """
    Retrieve new incoming orders for a distributor.
    
    Returns orders with "pending" or "paid" status for the authenticated distributor.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
    
    Returns:
        OrderListResponse: Paginated list of new orders
        
    Raises:
        HTTPException 403: If user is not a distributor
    """
    # Role check removed as it is handled by require_role dependency
    
    # Build query for new orders (pending or paid status)
    query = select(Order).where(
        Order.distributor_id == current_user.id,
        or_(Order.status == OrderStatus.PENDING, Order.status == OrderStatus.PAID)
    )
    count_query = select(func.count()).select_from(Order).where(
        Order.distributor_id == current_user.id,
        or_(Order.status == OrderStatus.PENDING, Order.status == OrderStatus.PAID)
    )
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering (newest first)
    query = query.order_by(desc(Order.created_at)).offset(offset).limit(page_size)
    
    # Execute query
    orders = db.exec(query).all()
    
    return OrderListResponse(
        orders=[OrderResponse.model_validate(order) for order in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_distributor.get(
    "/distributor/orders/{order_id}",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR]))]
)
async def get_distributor_order_details(
    order_id: UUID,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Retrieve details of a specific order for a distributor.
    
    Returns complete order details including order items.
    
    Args:
        order_id: UUID of the order
    
    Returns:
        OrderDetailResponse: Detailed order information with items
        
    Raises:
        HTTPException 403: If user is not a distributor or not authorized
        HTTPException 404: If order not found
    """
    # Role check removed as it is handled by require_role dependency
    
    # Find the order
    order = db.exec(
        select(Order).where(
            Order.id == order_id,
            Order.distributor_id == current_user.id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or you don't have access to this order"
        )
    
    # Get order items with product details
    order_items = db.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()

    # Get all product IDs from order items
    product_ids = [item.product_id for item in order_items]

    # Fetch all products in one query for efficiency
    products = db.exec(
        select(Product).where(Product.id.in_(product_ids))  # type: ignore
    ).all()

    # Create a product lookup dictionary
    product_lookup = {product.id: product for product in products}

    # Get distributor name
    distributor_profile = db.exec(
        select(DistributorProfile).where(DistributorProfile.id == current_user.id)
    ).first()
    
    # Build response with actual product data
    order_response = OrderResponse.model_validate(order)

    items_response = [
        OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=product_lookup[item.product_id].name,
            product_sku=product_lookup[item.product_id].sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal
        )
        for item in order_items
    ]
    
    return OrderDetailResponse(
        **order_response.model_dump(),
        items=items_response,
        distributor_name=distributor_profile.business_name if distributor_profile else None
    )


@v1_distributor.put(
    "/distributor/orders/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.DISTRIBUTOR]))]
)
async def update_distributor_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Update the order status (e.g., "Packaging Confirmation").
    
    Distributors can update order status to track order progress.
    
    Args:
        order_id: UUID of the order
        status_update: New status information
    
    Returns:
        OrderResponse: Updated order information
        
    Raises:
        HTTPException 403: If user is not a distributor or not authorized
        HTTPException 404: If order not found
        HTTPException 400: If status transition is invalid
    """
    # Role check removed as it is handled by require_role dependency
    
    # Find the order
    order = db.exec(
        select(Order).where(
            Order.id == order_id,
            Order.distributor_id == current_user.id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or you don't have access to this order"
        )
    
    # Validate status transition
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
        OrderStatus.PAID: [OrderStatus.APPROVED, OrderStatus.CANCELLED],
        OrderStatus.APPROVED: [OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED],
        OrderStatus.READY_FOR_PICKUP: [OrderStatus.COMPLETED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: []
    }
    
    if status_update.status not in valid_transitions.get(order.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {order.status} to {status_update.status}"
        )
    
    # Update order status
    order.status = status_update.status
    
    # Update relevant timestamp
    now = datetime.utcnow()
    if status_update.status == OrderStatus.APPROVED:
        order.approved_at = now
    elif status_update.status == OrderStatus.READY_FOR_PICKUP:
        order.ready_at = now
    elif status_update.status == OrderStatus.COMPLETED:
        order.completed_at = now
    elif status_update.status == OrderStatus.CANCELLED:
        order.cancelled_at = now
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return OrderResponse.model_validate(order)

