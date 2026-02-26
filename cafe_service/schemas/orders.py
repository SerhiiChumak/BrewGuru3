from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Annotated

from pydantic import BaseModel, Field, computed_field

from cafe_service.schemas.cafes import MenuItemBriefSchema, CafeBriefSchema, UserBriefSchema
from cafe_service.database.models.orders import OrderStatusEnum


# -------------------------
# Cart
# -------------------------

class CartItemAddRequestSchema(BaseModel):
    menu_item_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0)]

    model_config = {"extra": "forbid"}


class CartItemResponseSchema(BaseModel):
    id: int
    cafe_id: int
    menu_item_id: int
    quantity: int
    unit_price: Decimal
    menu_item: MenuItemBriefSchema
    cafe: CafeBriefSchema

    model_config = {"from_attributes": True}


class CartResponseSchema(BaseModel):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user: UserBriefSchema
    items: List[CartItemResponseSchema]

    model_config = {"from_attributes": True}

# -------------------------
# Orders
# -------------------------

class OrderItemCreateSchema(BaseModel):
    menu_item_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0)]

    model_config = {"extra": "forbid"}


class OrderCheckoutSchema(BaseModel):
    model_config = {"extra": "forbid"}


class OrderItemResponseSchema(BaseModel):
    id: int
    menu_item_id: int | None
    name_snapshot: str
    unit_price: Decimal
    quantity: int

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price


class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    cafe_id: int
    status: OrderStatusEnum
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    user: UserBriefSchema
    cafe: CafeBriefSchema
    items: List[OrderItemResponseSchema]

    model_config = {"from_attributes": True}
