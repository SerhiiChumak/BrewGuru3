from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cafe_service.config.dependencies import get_user, get_cafe
from cafe_service.database.models.accounts import UserModel
from cafe_service.database import get_db

from cafe_service.database.models.cafe import ReviewModel, CafeModel
from cafe_service.schemas.cafes import ReviewCreateResponseSchema, ReviewCreateSchema, ReviewReadSchema

router = APIRouter()


@router.post("/cafes/{cafe_id}/reviews/",
             summary="Post a review for a specific cafe",
             description=(
                     "<h3>This endpoint allows clients to add a new review for a specific cafe "
                     "to the database.</h3>"
             ),
             response_model=ReviewCreateResponseSchema,
             responses={
                 400: {
                     "description": "Invalid input.",
                     "content": {
                         "application/json": {
                             "example": {"detail": "Invalid input data."}
                         }
                     },
                 }
             },
             status_code=201
             )
async def post_review(
        data: ReviewCreateSchema,
        db: AsyncSession = Depends(get_db),
        cafe: CafeModel = Depends(get_cafe),
        user: UserModel = Depends(get_user)
) -> ReviewCreateResponseSchema:
    """
    Add a review for a specific cafe to the database.

    This endpoint allows the creation of a new review for specific cafe.

    :param data: The data required to create a new review.
    :type data: ReviewCreateSchema
    :param db: The async SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession
    :param cafe: Cafe fetched from database or 404 if cafe not found (provided via dependency injection).
    :type db: AsyncSession
    :param user: User session via decoded token, 404 if user not found or 403 if user is not active
    (provided via dependency injection).
    :type db: AsyncSession

    :return: The created review.
    :rtype: ReviewCreateResponseSchema

    :raises HTTPException:
        - 400 if input data is invalid (e.g., violating a constraint).
    """

    try:
        review = ReviewModel(
            user=user,
            cafe=cafe,
            review=data.review,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        return ReviewCreateResponseSchema.model_validate(review)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.get("/cafes/{cafe_id}/reviews/",
            summary="Get a list of reviews for cafe",
            response_model=list[ReviewReadSchema],
            description=(
                    "This endpoint retrieves a  list of reviews for a cafe from the database. "
            ),
            )
async def read_reviews(
        db: AsyncSession = Depends(get_db),
        cafe: CafeModel = Depends(get_cafe),
        _user: UserModel = Depends(get_user),
) -> list[ReviewReadSchema]:
    """
    Fetch a list of reviews for cafe from the database (asynchronously).

    This function retrieves a list of reviews for a specific cafe.

    :param db: The async SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession
    :param cafe: Cafe fetched from database or 404 if cafe not found (provided via dependency injection).
    :type db: AsyncSession
    :param _user: User session via decoded token, 404 if user not found or 403 if user is not active
    (provided via dependency injection).
    :type db: AsyncSession

    :return: A response containing the list of reviews for specific cafe and metadata.
    Returns an empty list if no reviews are found.
    :rtype: list[ReviewReadSchema]
.
    """

    stmt = select(ReviewModel).where(ReviewModel.cafe_id == cafe.id)
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    return [ReviewReadSchema.model_validate(review) for review in reviews]


@router.delete(
    "/cafes/{cafe_id}/reviews/{review_id}/",
    description=(
        "<h3>Delete a specific review from the database by its unique ID.</h3>"
        "<p>If the review exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned. Admins and moderators can delete any review.</p>"
    ),
    responses={
        204: {
            "description": "Review deleted successfully."
        },
        404: {
            "description": "Review not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Review not found"}
                }
            },
        },
        403: {
            "description": "User does not have permission to delete other users reviews.",
            "content": {
                "application/json": {
                    "example": {"detail": "You can't delete this review."}
                }
            },
        },
    },
    status_code=204,
)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_db),
        cafe: CafeModel = Depends(get_cafe),
        user: UserModel = Depends(get_user)
):
    """
    Delete a specific review by its ID.

    This function deletes a review identified by its unique ID.
    If review does not exist, 404 error is raised.
    Users can only delete their own reviews.

    :param review_id: The unique identifier of the review to delete.
    :type review_id: int
    :param db: The async SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession
    :param cafe: Cafe fetched from database or 404 if cafe not found (provided via dependency injection).
    :type db: AsyncSession
    :param user: User session via decoded token, 404 if user not found or 403 if user is not active
    (provided via dependency injection).
    :type db: AsyncSession

    :raises HTTPException: Raises a 404 error if review with the given ID is not found.
    :raises HTTPException: Raises a 403 error if user tries to delete other users reviews.

    :return: A response indicating the successful deletion of the cafe.
    :rtype: None
    """
    stmt = select(ReviewModel).where(
        ReviewModel.id == review_id,
        ReviewModel.cafe_id == cafe.id,
    )
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    is_owner = review.user_id == user.id
    is_moderator_or_admin = user.group.name in ("moderator", "admin")

    if not (is_owner or is_moderator_or_admin):
        raise HTTPException(status_code=403, detail="You can't delete this review.")

    await db.delete(review)
    await db.commit()

    return {"detail": "Review deleted successfully."}
