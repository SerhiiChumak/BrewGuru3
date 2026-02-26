from fastapi import Depends, HTTPException
from sqlalchemy.orm import selectinload

from cafe_service.config.settings import BaseAppSettings, get_settings
from cafe_service.notifications.interfaces import EmailSenderInterface
from cafe_service.notifications.emails import EmailSender
from cafe_service.security.interfaces import JWTAuthManagerInterface
from cafe_service.security.token_manager import JWTAuthManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from cafe_service.storages.interfaces import S3StorageInterface
from cafe_service.storages.s3 import S3StorageClient

from cafe_service.database.models.accounts import UserModel, UserGroupEnum, UserGroupModel
from cafe_service.database.models.cafe import CafeModel
from cafe_service.exceptions.security import BaseSecurityError
from cafe_service.security.http import get_token
from cafe_service.database import get_db


def get_jwt_auth_manager(settings: BaseAppSettings = Depends(get_settings)) -> JWTAuthManagerInterface:
    """
    Create and return a JWT authentication manager instance.

    This function uses the provided application settings to instantiate a JWTAuthManager, which implements
    the JWTAuthManagerInterface. The manager is configured with secret keys for access and refresh tokens
    as well as the JWT signing algorithm specified in the settings.

    Args:
        settings (BaseAppSettings, optional): The application settings instance.
        Defaults to the output of get_settings().

    Returns:
        JWTAuthManagerInterface: An instance of JWTAuthManager configured with
        the appropriate secret keys and algorithm.
    """
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


def get_accounts_email_notificator(
    settings: BaseAppSettings = Depends(get_settings)
) -> EmailSenderInterface:
    """
    Retrieve an instance of the EmailSenderInterface configured with the application settings.

    This function creates an EmailSender using the provided settings, which include details such as the email host,
    port, credentials, TLS usage, and the directory and filenames for email templates. This allows the application
    to send various email notifications (e.g., activation, password reset) as required.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        EmailSenderInterface: An instance of EmailSender configured with the appropriate email settings.
    """
    return EmailSender(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        email=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME
    )


def get_s3_storage_client(
    settings: BaseAppSettings = Depends(get_settings)
) -> S3StorageInterface:
    """
    Retrieve an instance of the S3StorageInterface configured with the application settings.

    This function instantiates an S3StorageClient using the provided settings, which include the S3 endpoint URL,
    access credentials, and the bucket name. The returned client can be used to interact with an S3-compatible
    storage service for file uploads and URL generation.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        S3StorageInterface: An instance of S3StorageClient configured with the appropriate S3 storage settings.
    """
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )


async def get_user(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve and validate the currently authenticated user.

    This dependency:
    1. Decodes the provided JWT access token.
    2. Extracts the `user_id` from the token payload.
    3. Fetches the user from the database along with their group.
    4. Ensures the user exists and is active.

    Args:
        token (str): Raw access token extracted from the Authorization header.
        jwt_manager (JWTAuthManagerInterface): Service responsible for decoding and validating JWTs.
        db (AsyncSession): Asynchronous SQLAlchemy database session.

    Returns:
        UserModel: The authenticated and active user.

    Raises:
        HTTPException:
            - 400 Bad Request: If the token is invalid or expired.
            - 404 Not Found: If the user does not exist.
            - 403 Forbidden: If the user account is inactive.
    """
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    user_stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == user_id)
    )
    result_user = await db.execute(user_stmt)
    user = result_user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


async def user_is_staff(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
):
    """
    Ensure the authenticated user has staff-level permissions.

    Staff users are those belonging to the MODERATOR or ADMIN groups.
    This dependency should be used to protect endpoints that require
    elevated (but not full admin) privileges.

    Args:
        db (AsyncSession): Asynchronous SQLAlchemy database session.
        user (UserModel): Authenticated user provided by `get_user`.

    Returns:
        UserModel: The authenticated staff user.

    Raises:
        HTTPException:
            - 403 Forbidden: If the user is not a moderator or admin.
    """
    stmt = select(UserGroupModel.name).where(UserGroupModel.id == user.group_id)
    res = await db.execute(stmt)
    user_group = res.scalar_one()

    if user_group not in (UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action.",
        )

    return user


async def user_is_admin(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_user),
):
    """
    Ensure the authenticated user has administrator permissions.

    This dependency restricts access strictly to users belonging
    to the ADMIN group.

    Args:
        db (AsyncSession): Asynchronous SQLAlchemy database session.
        user (UserModel): Authenticated user provided by `get_user`.

    Returns:
        UserModel: The authenticated admin user.

    Raises:
        HTTPException:
            - 403 Forbidden: If the user is not an admin.
    """
    stmt = select(UserGroupModel.name).where(UserGroupModel.id == user.group_id)
    res = await db.execute(stmt)
    user_group = res.scalar_one()

    if user_group not in UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action.",
        )

    return user


async def get_cafe(
    cafe_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a cafe by its ID.

    This dependency fetches a cafe from the database and ensures
    it exists before allowing further processing.

    Args:
        cafe_id (int): ID of the cafe to retrieve.
        db (AsyncSession): Asynchronous SQLAlchemy database session.

    Returns:
        CafeModel: The requested cafe.

    Raises:
        HTTPException:
            - 404 Not Found: If the cafe does not exist.
    """
    cafe_stmt = select(CafeModel).where(CafeModel.id == cafe_id)
    result_cafe = await db.execute(cafe_stmt)
    cafe = result_cafe.scalar_one_or_none()

    if not cafe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cafe not found.",
        )

    return cafe
