from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func, or_, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cafe_service.config.dependencies import user_is_staff
from cafe_service.database.models.accounts import UserModel
from cafe_service.database.models.cafe import (
    CafeModel,
    AmenityModel,
    CityModel,
    MenuModel,
    MenuItemModel,
    CafeOpeningHoursModel
)
from cafe_service.schemas.cafes import (
    CafeListResponseSchema,
    CafeQueryParamsSchema,
    CafeListItemSchema,
    CafeDetailSchema,
    CafeCreateSchema,
    AmenityRefSchema,
    MenuRefSchema,
    CafeUpdateSchema
)
from cafe_service.database import get_db


router = APIRouter()


@router.get(
    "/cafes/",
    response_model=CafeListResponseSchema,
    summary="Get a paginated list of cafes",
    description=(
            "<h3>This endpoint retrieves a paginated list of cafes from the database.</h3>"
            "<p>Supports:</p>"
            "<ul>"
            "<li><b>Pagination</b> via <code>page</code> and <code>per_page</code></li>"
            "<li><b>Search</b> via <code>search</code> (matches cafe name, address, "
            "amenity name)</li>"
            "<li><b>Filtering</b> via <code>rating</code></li>"
            "<li><b>Sorting</b> via <code>sort_by</code> (name) and "
            "<code>sort_order</code> (asc/desc)</li>"
            "</ul>"
            "<p>The response includes items, total counts, and previous/next page links when applicable.</p>"
    ),
    responses={
        404: {
            "description": "No cafes found or page out of range.",
            "content": {
                "application/json": {
                    "examples": {
                        "no_cafes": {"value": {"detail": "No cafes found."}},
                        "page_out_of_range": {"value": {"detail": "Page out of range."}},
                    }
                }
            },
        }
    }
)
async def get_cafe_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
        params: CafeQueryParamsSchema = Depends(),
        db: AsyncSession = Depends(get_db),
) -> CafeListResponseSchema:
    """
    Retrieve a paginated list of cafes with optional search, filtering, and sorting.

    Behavior:
    - Pagination uses `page` and `per_page` (1-based index).
    - Search (`params.search`) matches:
      - Cafe name
      - Cafe address
      - Amenity name
    - Filters:
      - `params.rating` filters by cafe rating
    - Sorting:
      - `params.sort_by` supports: name
      - `params.sort_order` supports: asc/desc
      - A model-defined default ordering is appended after custom sorting (if present).
    - Total count is computed over distinct cafe IDs (to avoid duplicates from joins).

    Returns:
    - 200 with `CafeListResponseSchema` (cafes + pagination metadata).

    Errors:
    - 404 if no cafes match the query (`"No cafes found."`)
    - 404 if `page` exceeds total pages (`"Page out of range."`)
    """
    offset = (page - 1) * per_page

    base_from = (
        select(CafeModel.id)
        .select_from(CafeModel)
        .outerjoin(CafeModel.amenities)
    )

    if params.search:
        pattern = f"%{params.search}%"
        base_from = base_from.where(
            or_(
                CafeModel.name.ilike(pattern),
                CafeModel.address.ilike(pattern),
                AmenityModel.name.ilike(pattern),
            )
        )

    if params.rating is not None:
        base_from = base_from.where(CafeModel.ratings >= params.rating)

    if params.city:
        base_from = base_from.where(CafeModel.city.ilike(f"%{params.city}%"))

    # ---- count distinct cafes ----
    count_stmt = select(func.count()).select_from(base_from.distinct().subquery())
    total_items = (await db.execute(count_stmt)).scalar_one()

    if total_items == 0:
        raise HTTPException(status_code=404, detail="No cafes found.")

    total_pages = (total_items + per_page - 1) // per_page
    if page > total_pages:
        raise HTTPException(status_code=404, detail="Page out of range.")

    # ---- sorting (apply to the ID query) ----
    sort_columns = {
        "name": CafeModel.name,
    }

    order_clauses = []
    sort_column = sort_columns.get(params.sort_by)
    if sort_column is not None:
        order_clauses.append(sort_column.asc() if params.sort_order == "asc" else sort_column.desc())

    default_order = CafeModel.default_order_by()
    if default_order:
        order_clauses.extend(default_order)

    # ---- page IDs (distinct!) ----
    ids_stmt = base_from.distinct()
    if order_clauses:
        ids_stmt = ids_stmt.order_by(*order_clauses)

    ids_stmt = ids_stmt.offset(offset).limit(per_page)
    cafe_ids = (await db.execute(ids_stmt)).scalars().all()

    if not cafe_ids:
        raise HTTPException(status_code=404, detail="No cafes found.")

    # ---- fetch full cafes by IDs ----
    # Keep the same order as cafes_ids (important for stable pagination)
    order_by_ids = case({mid: idx for idx, mid in enumerate(cafe_ids)}, value=CafeModel.id)

    cafes_stmt = (select(CafeModel).
                  where(CafeModel.id.in_(cafe_ids)).
                  options(selectinload(CafeModel.opening_hours)).
                  order_by(order_by_ids))

    cafes = (await db.execute(cafes_stmt)).scalars().all()

    cafe_list = [CafeListItemSchema.model_validate(c) for c in cafes]

    return CafeListResponseSchema(
        cafes=cafe_list,
        prev_page=f"/brewguru/cafes/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/brewguru/cafes/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/cafes/",
    response_model=CafeDetailSchema,
    summary="Add a new cafe",
    description=(
            "<h3>This endpoint creates a new cafe in the database (staff-only).</h3>"
            "<p>It will link existing related entities or create them if missing:</p>"
            "<ul>"
            "<li>Opening hours (by code)</li>"
            "<li>Amenities (by name)</li>"
            "<li>Menus (by name)</li>"
            "</ul>"
            "<p>Uniqueness check: a cafe with the same <code>name</code> and "
            "<code>city_id</code> cannot be created twice.</p>"
    ),
    responses={
        201: {
            "description": "Cafe created successfully.",
        },
        400: {
            "description": "Invalid input data (constraint/validation error at DB level).",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        },
        409: {
            "description": "Cafe with the same name and city_id already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A cafe with the name 'Cafe X and city_id '1' already exists."
                    }
                }
            },
        },
    },
    status_code=201
)
async def create_cafe(
        cafe_data: CafeCreateSchema,
        db: AsyncSession = Depends(get_db),
        _user: UserModel = Depends(user_is_staff),
) -> CafeDetailSchema:
    """
    Create a new cafe and attach related entities (staff-only).

    Workflow:
    - Rejects duplicates by checking `(name, city_id)` before insert.
    - Resolves relations by lookup-and-create:
      - Opening_hours/ by `code`
      - City/Amenities/Menus by `name`
    - Commits the transaction and refreshes the cafe with relationships.

    Returns:
    - 201 with the created cafe (`CafeDetailSchema`).

    Errors:
    - 409 if a cafe with the same `name` and `city_id` already exists.
    - 400 if a database constraint fails (captured as `IntegrityError`).
    """
    city = await db.get(CityModel, cafe_data.city_id)
    if city is None:
        raise HTTPException(status_code=400, detail=f"Unknown city_id: {cafe_data.city_id}")

    existing_id = await db.scalar(
        select(CafeModel.id).where(
            func.lower(CafeModel.name) == cafe_data.name.lower(),
            CafeModel.city_id == cafe_data.city_id
        )
    )

    if existing_id is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cafe already exists with the same attributes: "
                f"name='{cafe_data.name}', city='{cafe_data.city_id}'."
            ),
        )

    try:
        async with db.begin():
            amenities: list[AmenityModel] = []
            for a in cafe_data.amenities:
                if isinstance(a, AmenityRefSchema) and a.id is not None:
                    amenity = await db.get(AmenityModel, a.id)
                    if amenity is None:
                        raise HTTPException(status_code=400, detail=f"Unknown amenity_id: {a.id}")
                    amenities.append(amenity)
                    continue
                else:
                    name = a.name.strip()
                    amenity = await db.scalar(select(AmenityModel).where(func.lower(AmenityModel.name) == name.lower()))
                    if not amenity:
                        amenity = AmenityModel(name=name)
                        db.add(amenity)
                        await db.flush()
                    amenities.append(amenity)

            cafe = CafeModel(
                name=cafe_data.name,
                city_id=cafe_data.city_id,
                address=cafe_data.address,
                phone=cafe_data.phone,
                website=str(cafe_data.website) if cafe_data.website else None,
                instagram=str(cafe_data.instagram) if cafe_data.instagram else None,
                description=cafe_data.description,
                seats=cafe_data.seats,
                amenities=amenities,
            )

            db.add(cafe)
            await db.flush()

            opening_rows: list[CafeOpeningHoursModel] = []

            for hours in cafe_data.opening_hours:
                opening_rows.append(CafeOpeningHoursModel(
                    weekday=hours.weekday,
                    open_time=hours.open_time,
                    close_time=hours.close_time,
                    is_open=True,
                ))
                continue

            if opening_rows:
                db.add_all(opening_rows)
                cafe.opening_hours = opening_rows

            menus: list[MenuModel] = []
            for m in cafe_data.menus:
                if isinstance(m, MenuRefSchema) and m.id is not None:
                    menu = await db.get(MenuModel, m.id)
                    if menu is None:
                        raise HTTPException(status_code=400, detail=f"Unknown menu_id: {m.id}")
                    if menu.cafe_id != cafe.id:
                        raise HTTPException(status_code=400, detail=f"Menu {m.id} does not belong to this cafe")
                    menus.append(menu)
                    continue

                menu_name = m.name.strip()
                if not menu_name:
                    raise HTTPException(status_code=400, detail=f"Menu name cannot be empty")

                stmt = select(MenuModel).where(
                    MenuModel.cafe_id == cafe.id,
                    func.lower(MenuModel.name) == menu_name.lower()
                )
                await db.scalar(stmt)

                if menu is None:
                    menu = MenuModel(name=menu_name, cafe_id=cafe.id)
                    db.add(menu)
                    await db.flush()

                    for item in m.items:
                        item_name = item.name.strip()
                        if not item_name:
                            raise HTTPException(status_code=400, detail=f"Menu items cannot be empty")
                        db.add(MenuItemModel(
                            name=item.name,
                            price=item.price,
                            menu_id=menu.id,
                        ))

                menus.append(menu)

            cafe.menus = menus

        stmt = (
            select(CafeModel)
            .where(CafeModel.id == cafe.id)
            .options(
                selectinload(CafeModel.city),
                selectinload(CafeModel.amenities),
                selectinload(CafeModel.opening_hours),
                selectinload(CafeModel.menus).selectinload(MenuModel.items),
            )
        )

        cafe_full = (await db.execute(stmt)).scalar_one()
        return CafeDetailSchema.model_validate(cafe_full)

    except IntegrityError:
        raise HTTPException(status_code=400, detail="Invalid input data.")

@router.get(
    "/cafes/{cafe_id}/",
    response_model=CafeDetailSchema,
    summary="Get cafe details by ID",
    description=(
            "<h3>Fetch detailed information about a specific cafe by its unique ID.</h3>"
            "<p>The response includes cafe and its related entities:</p>"
            "<ul>"
            "<li>Reviews</li>"
            "<li>Reactions</li>"
            "<li>Ratings</li>"
            "<li>Amenities</li>"
            "<li>Menus</li>"
            "</ul>"
            "<p>If cafe with the given ID is not found, a 404 error is returned.</p>"
    ),
    responses={
        404: {
            "description": "Cafe not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cafe with the given ID was not found."}
                }
            },
        }
    }
)
async def get_cafe_by_id(
        cafe_id: int,
        db: AsyncSession = Depends(get_db),
) -> CafeDetailSchema:
    """
    Retrieve a single cafe by ID, including related entities.

    The query eagerly loads the following relationships:
    - amenities, menus
    - reviews, ratings

    Returns:
    - 200 with `CafeDetailSchema`.

    Errors:
    - 404 if the cafe does not exist (`"Cafe with the given ID was not found."`).
    """
    stmt = (
        select(CafeModel)
        .where(CafeModel.id == cafe_id)
        .options(
            selectinload(CafeModel.city),
            selectinload(CafeModel.amenities),
            selectinload(CafeModel.opening_hours),
            selectinload(CafeModel.menus).selectinload(MenuModel.items),
            selectinload(CafeModel.reviews),
            selectinload(CafeModel.reactions),
        )
    )

    result = await db.execute(stmt)
    cafe = result.scalars().first()

    if not cafe:
        raise HTTPException(
            status_code=404,
            detail="Cafe with the given ID was not found."
        )

    return CafeDetailSchema.model_validate(cafe)


@router.delete(
    "/cafes/{cafe_id}/",
    summary="Delete cafe by ID",
    description=(
            "<h3>Delete specific cafe from the database by its unique ID (staff-only).</h3>"
            "<p>If cafe does not exist, a 404 error will be returned.</p>"
            "<p><b>Note:</b> This endpoint is declared with status code <code>204 No Content</code>.</p>"
    ),
    responses={
        204: {
            "description": "Cafe deleted successfully."
        },
        404: {
            "description": "Cafe not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cafe with the given ID was not found."}
                }
            },
        },
    },
    status_code=204
)
async def delete_cafe(
        cafe_id: int,
        db: AsyncSession = Depends(get_db),
        _requestor: UserModel = Depends(user_is_staff),
) -> Response:
    """
    Delete cafe by ID (staff-only).

    Workflow:
    - Fetches cafe by `cafe_id`.
    - If found, deletes it and commits.

    Returns:
    - 204 (as declared in the router decorator).

    Errors:
    - 404 if cafe does not exist (`"Cafe with the given ID was not found."`).

    Note:
    - The function currently returns a JSON body, even though the route is configured as 204.
    """
    stmt = select(CafeModel).where(CafeModel.id == cafe_id)
    result = await db.execute(stmt)
    cafe = result.scalars().first()

    if not cafe:
        raise HTTPException(
            status_code=404,
            detail="Cafe with the given ID was not found."
        )

    await db.delete(cafe)
    await db.commit()

    return Response(status_code=204)


@router.patch(
    "/cafes/{cafe_id}/",
    summary="Update cafe by ID",
    description=(
            "<h3>Update fields of an existing cafe by its unique ID (staff-only).</h3>"
            "<p>Only fields provided in the request body are updated (partial update).</p>"
            "<p>If cafe does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Cafe updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cafe updated successfully."}
                }
            },
        },
        400: {
            "description": "Invalid input data (constraint/validation error at DB level).",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        },
        404: {
            "description": "Cafe not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cafe with the given ID was not found."}
                }
            },
        },
    }
)
async def update_cafe(
        cafe_id: int,
        cafe_data: CafeUpdateSchema,
        db: AsyncSession = Depends(get_db),
        _user: UserModel = Depends(user_is_staff),
) -> dict[str, str]:
    """
    Partially update cafe by ID (staff-only).

    Behavior:
    - Fetches cafe by `cafe_id`.
    - Applies only provided fields from `cafe_data` (`exclude_unset=True`).
    - Commits changes and refreshes the instance.

    Returns:
    - 200 with a confirmation message.

    Errors:
    - 404 if cafe does not exist (`"Cafe with the given ID was not found."`).
    - 400 if a database constraint fails during commit (captured as `IntegrityError`).
    """
    stmt = select(CafeModel).where(CafeModel.id == cafe_id)
    result = await db.execute(stmt)
    cafe = result.scalars().first()

    if cafe is None:
        raise HTTPException(
            status_code=404,
            detail="Cafe with the given ID was not found."
        )

    payload = cafe_data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        if field in ("website", "instagram"):
            value = str(value) if value is not None else None
        if field == "name" and value is not None:
            value = value.strip()
        setattr(cafe, field, value)

    try:
        await db.commit()
        await db.refresh(cafe)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Cafe updated successfully."}
