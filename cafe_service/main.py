from fastapi import FastAPI

from cafe_service.routes import (
    cafe_router,
    accounts_router,
    cafes_favourites_router,
    cafes_ratings_router,
    cafes_reviews_router,
    cafes_orders_router
)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_version_prefix = "/api/v1"


app.include_router(cafe_router, prefix=f"{api_version_prefix}/brewguru", tags=["cafes"])
app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(cafes_favourites_router, prefix=f"{api_version_prefix}/favourites", tags=["favourites"])
app.include_router(cafes_ratings_router, prefix=f"{api_version_prefix}/ratings", tags=["ratings"])
app.include_router(cafes_reviews_router, prefix=f"{api_version_prefix}/reviews", tags=["reviews"])
app.include_router(cafes_orders_router, prefix=f"{api_version_prefix}/orders", tags=["orders"])