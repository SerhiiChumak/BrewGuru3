import enum
from datetime import time
from decimal import Decimal
from enum import IntEnum

from sqlalchemy import (
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
    Table,
    Column,
    Integer,
    Enum,
    DateTime,
    func,
    Numeric, Time
)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from cafe_service.database.models.base import Base


FavouritesCafesModel = Table(
    "favourites_cafes",
    Base.metadata,
    Column(
        "cafe_id",
        ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "favourite_id",
        ForeignKey("favourites.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

AmenitiesCafesModel = Table(
    "amenities_cafes",
    Base.metadata,
    Column(
        "cafe_id",
        ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "amenity_id",
        ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)


class RatingTypeEnum(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class WeekdayEnum(IntEnum):
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3
    FIVE = 4
    SIX = 5
    SEVEN = 6


class ReactionTypeEnum(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class CityModel(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)

    cafes: Mapped[list["CafeModel"]] = relationship("CafeModel", back_populates="city")

    def __repr__(self):
        return f"City: {self.name}"


class CafeOpeningHoursModel(Base):
    __tablename__ = "cafe_opening_hours"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), nullable=False)
    cafe: Mapped["CafeModel"] = relationship("CafeModel", back_populates="opening_hours")
    weekday: Mapped["WeekdayEnum"] = mapped_column(nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_open: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("cafe_id", "weekday", name="unique_time_constraint"),
    )


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reviews")
    review: Mapped[str] = mapped_column(Text, nullable=False)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), nullable=False, index=True)
    cafe: Mapped["CafeModel"] = relationship("CafeModel", back_populates="reviews")
    created_at = mapped_column(DateTime, default=func.now(), index=True)
    updated_at = mapped_column(DateTime, default=func.now())

    def __repr__(self):
        return f"<Review(review='{self.review}')>"


class FavouriteModel(Base):
    __tablename__ = "favourites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="favourites")
    cafes: Mapped[list["CafeModel"]] = relationship(
        "CafeModel",
        secondary=FavouritesCafesModel,
        back_populates="favourites"
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return f"<Favourite id={self.id}, user={self.user_id})>"


class RatingModel(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="ratings")
    rating: Mapped["RatingTypeEnum"] = mapped_column(
        Enum(RatingTypeEnum),
        nullable=False
    )
    created_at = mapped_column(DateTime, default=func.now())
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), nullable=False)
    cafe: Mapped["CafeModel"] = relationship("CafeModel", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "cafe_id", name="unique_user_cafe_rating"),
    )

    def __repr__(self):
        return f"<User id={self.user_id} gave cafe={self.cafe_id} {self.rating}/10>"


class AmenityModel(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cafes: Mapped[list["CafeModel"]] = relationship(
        "CafeModel",
        secondary=AmenitiesCafesModel,
        back_populates="amenities"
    )

    def __repr__(self):
        return f"<Amenity(name='{self.name}')>"


class MenuModel(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cafe: Mapped["CafeModel"] = relationship("CafeModel", back_populates="menus")
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id"), nullable=False)
    items: Mapped[list["MenuItemModel"]] = relationship(
        "MenuItemModel",
        back_populates="menu",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("cafe_id", "name", name="uq_menu_cafe_name"),
    )

    def __repr__(self):
        return f"<Food menu (name='{self.name}')>"


class MenuItemModel(Base):
    __tablename__ = "menu_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    menu: Mapped["MenuModel"] = relationship("MenuModel", back_populates="items")
    price: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=False)


class CafeModel(Base):
    __tablename__ = "cafes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    city: Mapped["CityModel"] = relationship("CityModel", back_populates="cafes")
    address: Mapped[str] = mapped_column(String(100), nullable=False)
    opening_hours: Mapped[list["CafeOpeningHoursModel"]] = relationship(
        "CafeOpeningHoursModel",
        back_populates="cafe"
    )
    phone: Mapped[str] = mapped_column(String(100), nullable=False)
    website: Mapped[str] = mapped_column(String(100), nullable=True)
    instagram: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    reviews: Mapped[list["ReviewModel"]] = relationship("ReviewModel", back_populates="cafe")
    favourites: Mapped[list["FavouriteModel"]] = relationship(
        "FavouriteModel",
        secondary=FavouritesCafesModel,
        back_populates="cafes"
    )
    ratings: Mapped[list["RatingModel"]] = relationship(
        "RatingModel",
        back_populates="cafe"
    )
    amenities: Mapped[list["AmenityModel"]] = relationship(
        "AmenityModel",
        secondary=AmenitiesCafesModel,
        back_populates="cafes"
    )
    menus: Mapped[list["MenuModel"]] = relationship("MenuModel", back_populates="cafe")

    __table_args__ = (
        UniqueConstraint("name", "city_id", name="unique_cafe_constraint"),
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]
