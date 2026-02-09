# Local imports
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartItemRemove, CartItemResponse, CartResponse
from app.schemas.order import OrderCreate, OrderResponse, OrderDetailResponse, OrderItemResponse, OrderListResponse
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.user import User, UserRole
from app.core.dependencies import get_current_user, DBSession, require_role, CurrentUser

# External imports
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from math import ceil
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, func
import random
import string


v1_wholesaler = APIRouter(prefix="/v1/wholesaler", tags=['v1_wholesaler'])

db_dependency = DBSession


def generate_order_number() -> str:
    """Generate a unique order number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{timestamp}-{random_suffix}"


def get_or_create_cart(db: DBSession, wholesaler_id: UUID) -> Cart:
    """Get existing cart or create a new one for the wholesaler"""
    cart = db.exec(
        select(Cart).where(Cart.wholesaler_id == wholesaler_id)
    ).first()
    
    if not cart:
        cart = Cart(wholesaler_id=wholesaler_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


def build_cart_response(cart: Cart, db: DBSession) -> CartResponse:
    """Build a CartResponse with calculated totals and product details"""
    items_response = []
    total_amount = Decimal("0.00")
    
    for item in cart.items:
        # Get product details
        product = db.exec(
            select(Product).where(Product.id == item.product_id)
        ).first()
        
        if product:
            subtotal = product.price_per_case * item.quantity
            total_amount += subtotal
            
            items_response.append(CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=product.name,
                product_sku=product.sku,
                product_image_url=product.image_url,
                distributor_id=product.distributor_id,
                unit_price=product.price_per_case,
                quantity=item.quantity,
                subtotal=subtotal,
                added_at=item.added_at
            ))
    
    return CartResponse(
        id=cart.id,
        wholesaler_id=cart.wholesaler_id,
        items=items_response,
        total_items=len(items_response),
        total_amount=total_amount,
        created_at=cart.created_at,
        updated_at=cart.updated_at
    )


def clear_cart(db: db_dependency, cart: Cart) -> None:
    """Clear all items from a cart after order is placed"""
    for item in cart.items:
        db.delete(item)
    cart.updated_at = datetime.utcnow()
    db.add(cart)


# endpoints 
@v1_wholesaler.post(
    "/cart/add",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def add_to_cart(
    item_data: CartItemAdd,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Add a product to the wholesaler's cart.
    Accessible only by Wholesalers.
    """
    # Verify product exists and is available
    product = db.exec(
        select(Product).where(Product.id == item_data.product_id)
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available"
        )
    
    if product.stock_quantity < item_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Only {product.stock_quantity} available"
        )
    
    # Get or create cart
    cart = get_or_create_cart(db, current_user.id)
    
    # Check if product already in cart
    existing_item = db.exec(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item_data.product_id
        )
    ).first()
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + item_data.quantity
        if new_quantity > product.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add more. Only {product.stock_quantity} available (you have {existing_item.quantity} in cart)"
            )
        existing_item.quantity = new_quantity
        db.add(existing_item)
    else:
        # Add new item
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(cart_item)
    
    # Update cart timestamp
    cart.updated_at = datetime.utcnow()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    
    return build_cart_response(cart, db)


@v1_wholesaler.put(
    "/cart/update",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def update_cart_item(
    item_data: CartItemUpdate,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Update product quantity in the wholesaler's cart.
    Accessible only by Wholesalers.
    """
    # Get cart
    cart = db.exec(
        select(Cart).where(Cart.wholesaler_id == current_user.id)
    ).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Find cart item
    cart_item = db.exec(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item_data.product_id
        )
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in cart"
        )
    
    # Verify stock availability
    product = db.exec(
        select(Product).where(Product.id == item_data.product_id)
    ).first()
    
    if product and item_data.quantity > product.stock_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Only {product.stock_quantity} available"
        )
    
    # Update quantity
    cart_item.quantity = item_data.quantity
    db.add(cart_item)
    
    # Update cart timestamp
    cart.updated_at = datetime.utcnow()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    
    return build_cart_response(cart, db)


@v1_wholesaler.delete(
    "/cart/remove",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def remove_from_cart(
    item_data: CartItemRemove,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Remove a product from the wholesaler's cart.
    Accessible only by Wholesalers.
    """
    # Get cart
    cart = db.exec(
        select(Cart).where(Cart.wholesaler_id == current_user.id)
    ).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Find cart item
    cart_item = db.exec(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item_data.product_id
        )
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in cart"
        )
    
    # Remove item
    db.delete(cart_item)
    
    # Update cart timestamp
    cart.updated_at = datetime.utcnow()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    
    return build_cart_response(cart, db)


@v1_wholesaler.get(
    "/cart",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def get_cart(
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Retrieve the current contents of the wholesaler's cart.
    Accessible only by Wholesalers.
    """
    # Get or create cart
    cart = get_or_create_cart(db, current_user.id)
    
    return build_cart_response(cart, db)


@v1_wholesaler.post(
    "/orders",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def create_order(
    order_data: OrderCreate,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Create a new order from the wholesaler's cart.
    Accessible only by Wholesalers.
    """
    # Get cart
    cart = db.exec(
        select(Cart).where(Cart.wholesaler_id == current_user.id)
    ).first()
    
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    # Group cart items by distributor
    items_by_distributor: dict[UUID, list[CartItem]] = {}
    for item in cart.items:
        product = db.exec(
            select(Product).where(Product.id == item.product_id)
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product not found: {item.product_id}"
            )
        
        if not product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is no longer available"
            )
        
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.name}'. Only {product.stock_quantity} available"
            )
        
        if product.distributor_id not in items_by_distributor:
            items_by_distributor[product.distributor_id] = []
        items_by_distributor[product.distributor_id].append(item)
    
    created_orders = []
    
    # Create an order for each distributor
    for distributor_id, cart_items in items_by_distributor.items():
        # Calculate total amount for this order
        total_amount = Decimal("0.00")
        order_items_data = []
        
        for cart_item in cart_items:
            product = db.exec(
                select(Product).where(Product.id == cart_item.product_id)
            ).first()
            
            if product:
                subtotal = product.price_per_case * cart_item.quantity
                total_amount += subtotal
                order_items_data.append({
                    "product": product,
                    "quantity": cart_item.quantity,
                    "unit_price": product.price_per_case,
                    "subtotal": subtotal
                })
                
                # Decrease stock
                product.stock_quantity -= cart_item.quantity
                db.add(product)
        
        # Create order
        order = Order(
            order_number=generate_order_number(),
            wholesaler_id=current_user.id,
            distributor_id=distributor_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            notes=order_data.notes
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # Create order items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product"].id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"]
            )
            db.add(order_item)
        
        db.commit()
        db.refresh(order)
        created_orders.append(order)
    
    # Clear the cart (Option 1: keep cart, remove items)
    clear_cart(db, cart)
    db.commit()
    
    # Return the first order (or you could return all orders)
    first_order = created_orders[0]
    
    # Build response with items
    items_response = []
    for order_item in first_order.order_items:
        product = db.exec(
            select(Product).where(Product.id == order_item.product_id)
        ).first()
        
        items_response.append(OrderItemResponse(
            id=order_item.id,
            product_id=order_item.product_id,
            product_name=product.name if product else "Unknown",
            product_sku=product.sku if product else "N/A",
            quantity=order_item.quantity,
            unit_price=order_item.unit_price,
            subtotal=order_item.subtotal
        ))
    
    # Get distributor name
    distributor = db.exec(
        select(User).where(User.id == first_order.distributor_id)
    ).first()
    
    return OrderDetailResponse(
        id=first_order.id,
        order_number=first_order.order_number,
        wholesaler_id=first_order.wholesaler_id,
        distributor_id=first_order.distributor_id,
        total_amount=first_order.total_amount,
        status=first_order.status,
        notes=first_order.notes,
        created_at=first_order.created_at,
        paid_at=first_order.paid_at,
        approved_at=first_order.approved_at,
        ready_at=first_order.ready_at,
        completed_at=first_order.completed_at,
        cancelled_at=first_order.cancelled_at,
        items=items_response,
        distributor_name=distributor.full_name if distributor else None
    )


@v1_wholesaler.get(
    "/orders",
    response_model=OrderListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def get_wholesaler_orders(
    db: db_dependency,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[OrderStatus] = Query(default=None, description="Filter by order status")
):
    """
    Retrieve a list of all orders placed by the wholesaler.
    Accessible only by Wholesalers.
    """
    # Build query
    query = select(Order).where(Order.wholesaler_id == current_user.id)
    count_query = select(func.count()).select_from(Order).where(Order.wholesaler_id == current_user.id)
    
    # Apply status filter
    if status_filter:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)
    
    # Get total count
    total = db.exec(count_query).one()
    
    # Calculate pagination
    total_pages = ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size) # type: ignore
    
    # Execute query
    orders = db.exec(query).all()
    
    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@v1_wholesaler.get(
    "/orders/{order_id}",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role([UserRole.WHOLESALER]))]
)
async def get_wholesaler_order_details(
    order_id: UUID,
    db: db_dependency,
    current_user: CurrentUser
):
    """
    Retrieve details of a specific wholesaler order.
    Accessible only by Wholesalers (own orders).
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
    
    # Verify ownership
    if order.wholesaler_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders"
        )
    
    # Build items response
    items_response = []
    for order_item in order.order_items:
        product = db.exec(
            select(Product).where(Product.id == order_item.product_id)
        ).first()
        
        items_response.append(OrderItemResponse(
            id=order_item.id,
            product_id=order_item.product_id,
            product_name=product.name if product else "Unknown",
            product_sku=product.sku if product else "N/A",
            quantity=order_item.quantity,
            unit_price=order_item.unit_price,
            subtotal=order_item.subtotal
        ))
    
    # Get distributor name
    distributor = db.exec(
        select(User).where(User.id == order.distributor_id)
    ).first()
    
    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        wholesaler_id=order.wholesaler_id,
        distributor_id=order.distributor_id,
        total_amount=order.total_amount,
        status=order.status,
        notes=order.notes,
        created_at=order.created_at,
        paid_at=order.paid_at,
        approved_at=order.approved_at,
        ready_at=order.ready_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        items=items_response,
        distributor_name=distributor.full_name if distributor else None
    )
