# from fastapi import Request, HTTPException, status
#
#
# def get_token(request: Request) -> str:
#     """
#     Extracts the Bearer token from the Authorization header.
#
#     :param request: FastAPI Request object.
#     :return: Extracted token string.
#     :raises HTTPException: If Authorization header is missing or invalid.
#     """
#     authorization: str = request.headers.get("Authorization")
#
#     if not authorization:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authorization header is missing"
#         )
#
#     scheme, _, token = authorization.partition(" ")
#
#     if scheme.lower() != "bearer" or not token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid Authorization header format. Expected 'Bearer <token>'"
#         )
#
#     return token


from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 1. Створюємо схему безпеки.
# auto_error=False дозволяє нам самим обробляти помилки, якщо захочеться.
security_scheme = HTTPBearer()


def get_token(auth: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    """
    Автоматично витягує Bearer токен.
    Тепер FastAPI "побачить" цей замок у Swagger!
    """
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )

    # auth.credentials — це вже готовий рядок токена (без слова 'Bearer')
    return auth.credentials
