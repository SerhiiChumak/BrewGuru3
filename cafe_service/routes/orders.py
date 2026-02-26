# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import selectinload
#
# from cafe_service.config.dependencies import get_user
# from cafe_service.database.models.orders import CartModel, CartItemModel
# from cafe_service.schemas.orders import CartResponseSchema, CartItemAddRequestSchema
# from cafe_service.database import get_db, UserModel, MenuItemModel
#
# router = APIRouter()
#
#
# @router.get(
#     "/cart/",
#     response_model=CartResponseSchema,
#     summary="Get shopping cart with items.",
#     description=(
#             "This endpoint retrieves user's shopping cart with added items."
#     )
# )
# async def get_cart(
#         db: AsyncSession = Depends(get_db),
#         user: UserModel = Depends(get_user)
# ) -> CartResponseSchema:
#     stmt = (
#         select(CartModel)
#         .where(CartModel.user_id == user.id)
#         .options(
#             selectinload(CartModel.items)
#             .selectinload(CartItemModel.menu_item),
#             selectinload(CartModel.items)
#             .selectinload(CartItemModel.cafe),
#             selectinload(CartModel.user),
#         )
#     )
#     result = await db.execute(stmt)
#     cart = result.scalars().one_or_none()
#
#     if cart is None:
#         cart = CartModel(user_id=user.id, is_active=True)
#         db.add(cart)
#         await db.commit()
#         await db.refresh(cart)
#
#     return cart
#
#
# @router.post(
#     "/cart/",
#     response_model=CartResponseSchema,
#     summary="Add items to shopping cart.",
#     description=(
#             "This endpoint adds items to shopping cart."
#     )
# )
# async def add_items_to_cart(
#         cart_data: CartItemAddRequestSchema,
#         db: AsyncSession = Depends(get_db),
#         user: UserModel = Depends(get_user),
# ) -> CartResponseSchema:
#     stmt = (
#         select(MenuItemModel)
#         .options(selectinload(MenuItemModel.menu))
#         .where(MenuItemModel.id == cart_data.menu_item_id)
#     )
#
#     menu_result = await db.execute(stmt)
#     menu_item = menu_result.scalars().one_or_none()
#     if menu_item is None:
#         raise HTTPException(status_code=404, detail="Menu Item not found.")
#
#     cafe_id = menu_item.cafe_id
#     unit_price = menu_item.unit_price
#     cart_stmt = (
#         select(CartModel)
#         .where(CartModel.user_id == user.id)
#         .options(
#             selectinload(CartModel.items)
#             .selectinload(CartItemModel.menu_item),
#             selectinload(CartModel.items)
#             .selectinload(CartItemModel.cafe),
#             selectinload(CartModel.user),
#         )
#     )
#     cart_result = await db.execute(cart_stmt)
#     cart = cart_result.scalars().one_or_none()
#
#     if cart is None:
#         cart = CartModel(user_id=user.id, is_active=True)
#         db.add(cart)
#         await db.flush()


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


# --- ЕНДПОЇНТИ КОШИКА ---

@router.get("/cart/", response_model=CartResponseSchema)
async def get_cart(
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> CartResponseSchema:
    # (Ваш існуючий код get_cart працює добре)
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


@router.post("/cart/", response_model=CartResponseSchema)
async def add_items_to_cart(
        cart_data: CartItemAddRequestSchema,
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user),
) -> CartResponseSchema:
    # 1. Перевіряємо товар
    menu_item = await db.get(MenuItemModel, cart_data.menu_item_id)
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu Item not found.")

    # 2. Отримуємо кошик
    cart = await get_cart(db, user)

    # 3. Шукаємо, чи є вже такий товар у кошику
    existing_item = next((item for item in cart.items if item.menu_item_id == cart_data.menu_item_id), None)

    if existing_item:
        existing_item.quantity += cart_data.quantity
    else:
        new_item = CartItemModel(
            cart_id=cart.id,
            cafe_id=menu_item.cafe_id,
            menu_item_id=menu_item.id,
            quantity=cart_data.quantity,
            unit_price=menu_item.unit_price  # Snapshot ціни
        )
        db.add(new_item)

    await db.commit()
    await db.refresh(cart)
    return cart


# --- ЕНДПОЇНТИ ЗАМОВЛЕНЬ (CHECKOUT) ---

@router.post(
    "/checkout/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout: Convert cart to order"
)
async def checkout(
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> OrderResponseSchema:
    """
    Бере всі товари з активного кошика, створює замовлення (Order)
    та очищає кошик.
    """
    # 1. Отримуємо кошик з товарами
    stmt = (
        select(CartModel)
        .where(CartModel.user_id == user.id, CartModel.is_active == True)
        .options(selectinload(CartModel.items).selectinload(CartItemModel.menu_item))
    )
    result = await db.execute(stmt)
    cart = result.scalars().one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    # 2. Розрахунок сум
    subtotal = sum(item.unit_price * item.quantity for item in cart.items)
    # Припускаємо, що замовлення створюється для кафе з першого товару в кошику
    cafe_id = cart.items[0].cafe_id

    # 3. Створення замовлення
    new_order = OrderModel(
        user_id=user.id,
        cafe_id=cafe_id,
        status=OrderStatusEnum.PENDING,
        subtotal=subtotal,
        total=subtotal,  # Тут можна врахувати знижки пізніше
        currency="UAH"
    )
    db.add(new_order)
    await db.flush()  # Отримуємо ID замовлення

    # 4. Переносимо товари в OrderItemModel
    for cart_item in cart.items:
        order_item = OrderItemModel(
            order_id=new_order.id,
            menu_item_id=cart_item.menu_item_id,
            name_snapshot=cart_item.menu_item.name,
            unit_price=cart_item.unit_price,
            quantity=cart_item.quantity
        )
        db.add(order_item)

    # 5. Очищення кошика
    await db.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart.id))
    # Можна також деактивувати сам кошик, якщо хочете історію кошиків
    # cart.is_active = False

    await db.commit()

    # Повертаємо замовлення з усіма зв'язками для відповіді
    final_stmt = (
        select(OrderModel)
        .where(OrderModel.id == new_order.id)
        .options(
            selectinload(OrderModel.items),
            selectinload(OrderModel.user),
            selectinload(OrderModel.cafe)
        )
    )
    final_res = await db.execute(final_stmt)
    return final_res.scalars().one()
