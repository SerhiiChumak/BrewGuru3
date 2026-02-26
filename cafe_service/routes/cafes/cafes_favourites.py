from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select, exists, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cafe_service.config.dependencies import get_user, get_cafe
from cafe_service.database.models.accounts import UserModel
from cafe_service.database import get_db

from cafe_service.database.models.cafe import CafeModel, FavouriteModel, FavouritesCafesModel
from cafe_service.schemas.accounts import MessageResponseSchema
from cafe_service.schemas.cafes import CafeListItemSchema

router = APIRouter()


@router.post(
    "/user/favourites/{cafe_id}/",
    summary="Add a cafe to the user's favourites",
    description=(
        "<h3>Add a cafe to favourites</h3>"
        "<p>This endpoint adds the specified cafe to the authenticated user's favourites list.</p>"
        "<ul>"
        "<li>If the user has no favourites list yet, it will be created automatically.</li>"
        "<li>If the cafe is already in favourites, the endpoint returns <b>409 Conflict</b>.</li>"
        "</ul>"
    ),
    status_code=201,
    response_model=MessageResponseSchema,
    responses={
        201: {"description": "Cafe added to favourites successfully."},
        404: {"description": "Cafe not found or user not found."},
        409: {
            "description": "Cafe already in favourites.",
            "content": {"application/json": {"example": {"detail": "Cafe already in favourites."}}},
        },
    },
)
async def add_to_favourites(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
    cafe: CafeModel = Depends(get_cafe),
) -> MessageResponseSchema:
    """
    Add a cafe to the authenticated user's favourites.

    Creates a favourites container for the user if it doesn't exist yet, then inserts a row
    into the association table between favourites and cafes.

    Args:
        db (AsyncSession): Async SQLAlchemy DB session.
        user (UserModel): Authenticated user from token (dependency).
        cafe (CafeModel): Cafe instance from DB or 404 (dependency).

    Returns:
        MessageResponseSchema: Success message.

    Raises:
        HTTPException:
            - 409 if the cafe already exists in favourites.
    """
    stmt = select(FavouriteModel).where(FavouriteModel.user_id == user.id)
    result = await db.execute(stmt)
    favourites = result.scalar_one_or_none()

    if favourites is None:
        favourites = FavouriteModel(user_id=user.id)
        db.add(favourites)
        await db.flush()

    exists_stmt = select(
        exists().where(
            FavouritesCafesModel.c.favourite_id == favourites.id,
            FavouritesCafesModel.c.cafe_id == cafe.id,
        )
    )
    already_exists = await db.scalar(exists_stmt)

    if already_exists:
        raise HTTPException(status_code=409, detail="Cafe already in favourites.")

    await db.execute(
        insert(FavouritesCafesModel).values(
            favourite_id=favourites.id,
            cafe_id=cafe.id,
        )
    )
    await db.commit()

    return MessageResponseSchema(message="Cafe added to favourites successfully.")


@router.get(
    "/user/favourites/",
    summary="Get the user's favourite cafes",
    description=(
        "<h3>Get favourites</h3>"
        "<p>This endpoint returns the authenticated user's list of favourite cafes.</p>"
        "<p>If the user has no favourites yet, it returns an empty list.</p>"
    ),
    responses={
        200: {"description": "List of favourite cafes (possibly empty)."},
        404: {"description": "User not found or inactive."},
    },
)
async def get_favourites(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
) -> list[CafeListItemSchema]:
    """
    Retrieve the authenticated user's favourite cafes.

    Args:
        db (AsyncSession): Async SQLAlchemy DB session.
        user (UserModel): Authenticated user from token (dependency).

    Returns:
        list[CafeModel]: A list of favourite cafes (empty if none exist).
    """
    stmt = (
        select(FavouriteModel)
        .options(selectinload(FavouriteModel.cafes))
        .where(FavouriteModel.user_id == user.id)
    )
    result = await db.execute(stmt)
    favourites = result.scalar_one_or_none()

    if not favourites:
        return []

    return [CafeListItemSchema.model_validate(cafe) for cafe in favourites.cafes]


@router.delete(
    "/user/favourites/{cafe_id}/",
    summary="Remove a cafe from the user's favourites",
    description=(
        "<h3>Remove a cafe from favourites</h3>"
        "<p>This endpoint removes the specified cafe from the authenticated user's favourites list.</p>"
        "<ul>"
        "<li>If the user has no favourites list, returns <b>404</b>.</li>"
        "<li>If the cafe is not in favourites, returns <b>404</b>.</li>"
        "</ul>"
    ),
    status_code=204,
    responses={
        204: {"description": "Cafe removed successfully."},
        404: {
            "description": "No favourites found or cafe not in favourites.",
            "content": {"application/json": {"example": {"detail": "Cafe not in favourites."}}},
        },
    },
)
async def remove_from_favourites(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
    cafe: CafeModel = Depends(get_cafe),
):
    """
    Remove a cafe from the authenticated user's favourites.

    Args:
        db (AsyncSession): Async SQLAlchemy DB session.
        user (UserModel): Authenticated user from token (dependency).
        cafe (CafeModel): Cafe instance from DB or 404 (dependency).

    Returns:
        dict: A small confirmation payload (even though status code is 204).

    Raises:
        HTTPException:
            - 404 if the favourites list doesn't exist or the cafe isn't in favourites.
    """
    stmt = (
        select(FavouriteModel)
        .options(selectinload(FavouriteModel.cafes))
        .where(FavouriteModel.user_id == user.id)
    )
    result = await db.execute(stmt)
    favourites = result.scalar_one_or_none()

    if not favourites:
        raise HTTPException(status_code=404, detail="No favourites found.")

    exists_stmt = select(
        exists().where(
            FavouritesCafesModel.c.favourite_id == favourites.id,
            FavouritesCafesModel.c.cafe_id == cafe.id,
        )
    )
    exists_cafe= await db.scalar(exists_stmt)

    if not exists_cafe:
        raise HTTPException(status_code=404, detail="Cafe not in favourites.")

    await db.execute(
        delete(FavouritesCafesModel).where(
            FavouritesCafesModel.c.favourite_id == favourites.id,
            FavouritesCafesModel.c.cafe_id == cafe.id,
        )
    )
    await db.commit()

    return
