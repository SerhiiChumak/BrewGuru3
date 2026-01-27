from __future__ import annotations

from datetime import datetime, time
from typing import Optional, List

from pydantic import BaseModel, Field, HttpUrl

from cafe_service.database.models.cafe import ReactionTypeEnum, RatingTypeEnum


# -------------------------
# Base
# -------------------------

class CafeBriefSchema(BaseModel):
    id: int
    name: str

    model_config = {"extra": "forbid"}

class CitySchema(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class AmenityCreateSchema(BaseModel):
    name: str

    model_config = {"extra": "forbid"}


class AmenityReadSchema(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class AmenityRefSchema(BaseModel):

    id: int

    model_config = {"extra": "forbid"}


class CafeOpeningHoursReadSchema(BaseModel):
    id: int
    weekday: int
    open_time: time
    close_time: time
    model_config = {"from_attributes": True}


class CafeOpeningHoursCreateSchema(BaseModel):
    weekday: int
    open_time: time
    close_time: time
    model_config = {"extra": "forbid"}



# -------------------------
# Menu
# -------------------------

class MenuItemCreateSchema(BaseModel):
    name: str
    price: float

    model_config = {"extra": "forbid"}


class MenuBriefSchema(BaseModel):
    id: int
    name: str

    model_config = {"extra": "forbid"}


class MenuCreateSchema(BaseModel):
    name: str
    cafe_id: int
    items: List[MenuItemCreateSchema] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class MenuReadSchema(BaseModel):
    id: int
    name: str
    cafe_id: int
    cafe: Optional[CafeBriefSchema] = None

    model_config = {"from_attributes": True}


class MenuItemReadSchema(BaseModel):
    id: int
    name: str
    price: float
    menu_id: int
    menu: Optional[MenuBriefSchema] = None

    model_config = {"from_attributes": True}


class MenuWithItemsReadSchema(MenuReadSchema):
    items: List[MenuItemReadSchema] = Field(default_factory=list)


class MenuRefSchema(BaseModel):
    id: int

    model_config = {"extra": "forbid"}

# -------------------------
# Reviews
# -------------------------

class Review(BaseModel):
    cafe_id: int
    user_id: int
    review: Optional[str] = Field(None, min_length=1, max_length=1000)

    model_config = {"from_attributes": True}


class ReviewCreateSchema(BaseModel):
    review: Optional[str] = Field(None, min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class ReviewReadSchema(BaseModel):
    id: int
    cafe_id: int
    user_id: int
    review: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreateResponseSchema(ReviewReadSchema):
    pass


class ReviewUpdateSchema(BaseModel):
    review: str = Field(..., min_length=1, max_length=1000)
    model_config = {"extra": "forbid"}


class ReviewUpdateResponseSchema(ReviewReadSchema):
    updated_at: datetime

# -------------------------
# Reactions
# -------------------------


class ReactionRequestSchema(BaseModel):
    reaction: ReactionTypeEnum
    model_config = {"extra": "forbid"}


class ReactionReadSchema(BaseModel):
    cafe_id: int
    user_id: int
    reaction: ReactionTypeEnum
    created_at: datetime
    model_config = {"from_attributes": True}


class ReactionResponseSchema(BaseModel):
    cafe_id: int
    user_id: int
    reaction: Optional[ReactionTypeEnum] = None
    created_at: Optional[datetime] = None
    detail: str = "Reaction added"

    model_config = {"extra": "forbid"}


# -------------------------
# Ratings
# -------------------------

class RatingRequestSchema(BaseModel):
    rating: RatingTypeEnum
    model_config = {"extra": "forbid"}


class RatingReadSchema(BaseModel):
    cafe_id: int
    user_id: int
    rating: RatingTypeEnum
    created_at: datetime
    model_config = {"from_attributes": True}


class RatingResponseSchema(BaseModel):
    cafe_id: int
    user_id: int
    rating: Optional[RatingTypeEnum] = None
    created_at: Optional[datetime] = None
    detail: str = "Rating added"

    model_config = {"extra": "forbid"}


# -------------------------
# Cafes
# -------------------------

class CafeBaseSchema(BaseModel):
    name: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    address: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=100)
    website: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None
    description: str = Field(..., max_length=255)
    seats: int = Field(..., ge=0)

    model_config = {"from_attributes": True}


class CafeDetailSchema(CafeBaseSchema):
    id: int
    opening_hours: List[CafeOpeningHoursReadSchema] = Field(default_factory=list)
    amenities: List[AmenityReadSchema] = Field(default_factory=list)
    menus: List[MenuWithItemsReadSchema] = Field(default_factory=list)
    reviews: List[ReviewCreateResponseSchema] = Field(default_factory=list)
    reactions: List[ReactionReadSchema] = Field(default_factory=list)
    ratings: List[RatingReadSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CafeListItemSchema(BaseModel):
    id: int
    name: str
    city: str
    address: str
    opening_hours: List[CafeOpeningHoursReadSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CafeListResponseSchema(BaseModel):
    cafes: List[CafeListItemSchema] = Field(default_factory=list)
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int
    model_config = {"from_attributes": True}


class CafeCreateSchema(BaseModel):
    name: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    address: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=100)

    website: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None

    description: str = Field(..., max_length=255)
    seats: int = Field(..., ge=0)

    opening_hours: List[CafeOpeningHoursCreateSchema] = Field(default_factory=list)
    amenities: List[AmenityRefSchema] = Field(default_factory=list)
    menus: List[MenuRefSchema] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class CafeUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=100)
    opening_hours: Optional[List[CafeOpeningHoursCreateSchema]] = None
    phone: Optional[str] = Field(None, max_length=100)
    website: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None
    description: Optional[str] = Field(None, max_length=255)
    seats: Optional[int] = Field(None, ge=0)
    amenities: Optional[List[AmenityRefSchema]] = None
    menus: Optional[List[MenuRefSchema]] = None

    model_config = {"extra": "forbid"}


# -------------------------
# Favourites
# -------------------------

class FavouriteListResponseSchema(BaseModel):
    cafes: List[CafeBaseSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}
