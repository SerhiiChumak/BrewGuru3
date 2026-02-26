from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cafe_service.config.dependencies import get_user, get_cafe
from cafe_service.database.models.accounts import UserModel
from cafe_service.database.models.cafe import CafeModel, RatingModel, RatingTypeEnum
from cafe_service.schemas.cafes import RatingRequestSchema, RatingResponseSchema
from cafe_service.database import get_db


router = APIRouter()


@router.post(
    "/cafes/{cafe_id}/ratings/",
    summary="Rate a cafe (toggle/update/remove)",
    description=(
        "<h3>Rate a cafe</h3>"
        "<p>This endpoint lets the authenticated user rate a cafe.</p>"
        "<ul>"
        "<li>If no rating exists yet, a new rating is created.</li>"
        "<li>If the same rating is sent again, the rating is removed (toggle off).</li>"
        "<li>If a different rating is sent, the rating is updated.</li>"
        "</ul>"
    ),
    status_code=201,
    response_model=RatingResponseSchema,
    responses={
        200: {"description": "Rating created/updated/removed successfully."},
        400: {
            "description": "Invalid input data.",
            "content": {"application/json": {"example": {"detail": "Invalid input data."}}},
        },
        404: {"description": "Cafe not found or user not found."},
    },
)
async def toggle_rating(
    data: RatingRequestSchema,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
    cafe: CafeModel = Depends(get_cafe),
) -> RatingResponseSchema:
    """
    Create/update/remove a rating for a cafe (toggle behavior).

    Rules:
    - If the user has no rating for this cafe -> create one.
    - If the user sends the same rating again -> delete it.
    - If the user sends a different rating -> update existing rating.

    Args:
        data (RatingRequestSchema): Rating payload.
        db (AsyncSession): Async SQLAlchemy DB session.
        user (UserModel): Authenticated user from token (dependency).
        cafe (CafeModel): Cafe instance from DB or 404 (dependency).

    Returns:
        RatingResponseSchema: Current rating (or null if removed) + message.

    Raises:
        HTTPException:
            - 400 if rating is missing or not allowed.
    """
    if data.rating is None:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    try:
        rating_value = RatingTypeEnum(data.rating)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    stmt = select(RatingModel).filter_by(cafe_id=cafe.id, user_id=user.id)
    result = await db.execute(stmt)
    rating = result.scalar_one_or_none()

    if rating is None:
        rating = RatingModel(
            cafe_id=cafe.id,
            user_id=user.id,
            rating=rating_value,
        )
        db.add(rating)
        await db.commit()
        await db.refresh(rating)
        message = f"You gave this cafe {data.rating}"

    elif rating.rating == data.rating:
        await db.delete(rating)
        await db.commit()
        rating = None
        message = "Your rating was removed"

    else:
        rating.rating = data.rating
        await db.commit()
        await db.refresh(rating)
        message = f"You gave this cafe {data.rating}"

    return RatingResponseSchema(
        cafe_id=cafe.id,
        user_id=user.id,
        rating=rating.rating if rating else None,
        created_at=rating.created_at if rating else None,
        detail=message,
    )
