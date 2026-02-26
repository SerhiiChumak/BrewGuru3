from enum import StrEnum
from decimal import Decimal
from cafe_service.database.models.base import Base
from sqlalchemy import Boolean, CheckConstraint, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint, DateTime, func, Numeric, Integer


class OrderStatusEnum(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    COMPLETED = "completed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentStatusEnum(StrEnum):
    REQUIRES_ACTION = "requires_action"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at = mapped_column(DateTime, default=func.now())
    updated_at = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")
    items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "is_active", name="uq_user_active_cart"),
    )


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)

    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # snapshot

    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="items")
    cafe: Mapped["CafeModel"] = relationship("CafeModel")
    menu_item: Mapped["MenuItemModel"] = relationship("MenuItemModel")

    __table_args__ = (
        UniqueConstraint("cart_id", "menu_item_id", name="uq_cart_menu_item"),
        CheckConstraint("quantity > 0", name="ck_cart_item_qty_positive"),
    )


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), nullable=False, index=True)
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped["OrderStatusEnum"] = mapped_column(
        Enum(OrderStatusEnum),
        nullable=False,
        default=OrderStatusEnum.PENDING,
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UAH")

    created_at = mapped_column(DateTime, default=func.now(), index=True)
    updated_at = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    cafe: Mapped["CafeModel"] = relationship("CafeModel")
    reservation: Mapped["ReservationModel | None"] = relationship("ReservationModel", back_populates="order")

    items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )




class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True)

    name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="items")
    menu_item: Mapped["MenuItemModel"] = relationship("MenuItemModel")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_qty_positive"),
    )
