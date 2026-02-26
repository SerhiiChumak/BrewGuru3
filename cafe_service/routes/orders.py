from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cafe_service.config.dependencies import get_user
from cafe_service.database.models.orders import CartModel, CartItemModel
from cafe_service.schemas.orders import CartResponseSchema, CartItemAddRequestSchema
from cafe_service.database import get_db, UserModel, MenuItemModel

router = APIRouter()


@router.get(
    "/cart/",
    response_model=CartResponseSchema,
    summary="Get shopping cart with items.",
    description=(
            "This endpoint retrieves user's shopping cart with added items."
    )
)
async def get_cart(
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user)
) -> CartResponseSchema:
    stmt = (
        select(CartModel)
        .where(CartModel.user_id == user.id)
        .options(
            selectinload(CartModel.items)
            .selectinload(CartItemModel.menu_item),
            selectinload(CartModel.items)
            .selectinload(CartItemModel.cafe),
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


@router.post(
    "/cart/",
    response_model=CartResponseSchema,
    summary="Add items to shopping cart.",
    description=(
            "This endpoint adds items to shopping cart."
    )
)
async def add_items_to_cart(
        cart_data: CartItemAddRequestSchema,
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_user),
) -> CartResponseSchema:
    stmt = (
        select(MenuItemModel)
        .options(selectinload(MenuItemModel.menu))
        .where(MenuItemModel.id == cart_data.menu_item_id)
    )

    menu_result = await db.execute(stmt)
    menu_item = menu_result.scalars().one_or_none()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu Item not found.")

    cafe_id = menu_item.cafe_id
    unit_price = menu_item.unit_price
    cart_stmt = (
        select(CartModel)
        .where(CartModel.user_id == user.id)
        .options(
            selectinload(CartModel.items)
            .selectinload(CartItemModel.menu_item),
            selectinload(CartModel.items)
            .selectinload(CartItemModel.cafe),
            selectinload(CartModel.user),
        )
    )
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().one_or_none()

    if cart is None:
        cart = CartModel(user_id=user.id, is_active=True)
        db.add(cart)
        await db.flush()
