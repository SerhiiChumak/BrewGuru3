from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cafe_service.config.dependencies import get_user
from cafe_service.database.models.orders import (
    CartModel,
    CartItemModel,
    OrderModel,
    OrderItemModel,
    OrderStatusEnum
)
from cafe_service.schemas.orders import (
    CartResponseSchema,
    CartItemAddRequestSchema,
    OrderResponseSchema
)
from cafe_service.database import get_db, UserModel, MenuItemModel

router = APIRouter()


@router.get("/cart/", response_model=CartResponseSchema, tags=["cart"])
async def get_cart(
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> CartResponseSchema:
    stmt = (
        select(CartModel)
        .where(CartModel.user_id == user.id, CartModel.is_active == True)
        .options(
            selectinload(CartModel.items).selectinload(CartItemModel.menu_item),
            selectinload(CartModel.items).selectinload(CartItemModel.cafe),
            selectinload(CartModel.user),
        )
    )
    result = await db.execute(stmt)
    cart = result.scalars().one_or_none()

    if cart is None:
        cart = CartModel(user_id=user.id, is_active=True)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


@router.post("/cart/", response_model=CartResponseSchema, tags=["cart"])
async def add_items_to_cart(
        cart_data: CartItemAddRequestSchema,
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user),
) -> CartResponseSchema:
    menu_item = await db.get(MenuItemModel, cart_data.menu_item_id)
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu Item not found.")

    cart = await get_cart(db, user)
    existing_item = next((item for item in cart.items if item.menu_item_id == cart_data.menu_item_id), None)

    if existing_item:
        existing_item.quantity += cart_data.quantity
    else:
        new_item = CartItemModel(
            cart_id=cart.id,
            cafe_id=menu_item.cafe_id,
            menu_item_id=menu_item.id,
            quantity=cart_data.quantity,
            unit_price=menu_item.unit_price
        )
        db.add(new_item)

    await db.commit()
    await db.refresh(cart)
    return cart


@router.post("/checkout/", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED, tags=["orders"])
async def checkout(
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> OrderResponseSchema:
    stmt = (
        select(CartModel)
        .where(CartModel.user_id == user.id, CartModel.is_active == True)
        .options(selectinload(CartModel.items).selectinload(CartItemModel.menu_item))
    )
    result = await db.execute(stmt)
    cart = result.scalars().one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    subtotal = sum(item.unit_price * item.quantity for item in cart.items)
    cafe_id = cart.items[0].cafe_id

    new_order = OrderModel(
        user_id=user.id,
        cafe_id=cafe_id,
        status=OrderStatusEnum.PENDING,
        subtotal=subtotal,
        total=subtotal,
        currency="UAH"
    )
    db.add(new_order)
    await db.flush()

    for cart_item in cart.items:
        order_item = OrderItemModel(
            order_id=new_order.id,
            menu_item_id=cart_item.menu_item_id,
            name_snapshot=cart_item.menu_item.name,
            unit_price=cart_item.unit_price,
            quantity=cart_item.quantity
        )
        db.add(order_item)

    await db.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart.id))
    await db.commit()

    final_stmt = (
        select(OrderModel)
        .where(OrderModel.id == new_order.id)
        .options(selectinload(OrderModel.items), selectinload(OrderModel.user), selectinload(OrderModel.cafe))
    )
    final_res = await db.execute(final_stmt)
    return final_res.scalars().one()


@router.post(
    "/orders/{order_id}/pay-test/",
    response_model=OrderResponseSchema,
    tags=["orders"],
    summary="Mock Payment: Set order status to PAID"
)
async def pay_order_test(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> OrderResponseSchema:
    # 1. Шукаємо замовлення
    stmt = (
        select(OrderModel)
        .where(OrderModel.id == order_id, OrderModel.user_id == user.id)
        .options(
            selectinload(OrderModel.items),
            selectinload(OrderModel.user),
            selectinload(OrderModel.cafe)
        )
    )
    result = await db.execute(stmt)
    order = result.scalars().one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatusEnum.PAID:
        raise HTTPException(status_code=400, detail="Order is already paid")

    # 2. Змінюємо статус (імітуємо успішну відповідь банку)
    order.status = OrderStatusEnum.PAID

    # Тут можна було б додати логіку сповіщення кафе про нове замовлення

    await db.commit()
    await db.refresh(order)

    return order
