import os

from cafe_service.database.models.base import Base
from cafe_service.database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserProfileModel
)
from cafe_service.database.models.cafe import (
    CafeModel,
    CityModel,
    CafeOpeningHoursModel,
    ReviewModel,
    FavouriteModel,
    RatingModel,
    AmenityModel,
    MenuModel,
    MenuItemModel,
    FavouritesCafesModel,
    AmenitiesCafesModel,
)
from cafe_service.database.session_sqlite import reset_sqlite_database as reset_database
from cafe_service.database.validators import accounts as accounts_validators

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from cafe_service.database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from cafe_service.database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )
