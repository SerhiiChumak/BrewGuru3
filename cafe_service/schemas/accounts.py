from pydantic import BaseModel, EmailStr, field_validator

from cafe_service.database.validators.accounts import validate_password_strength

from cafe_service.database.models.accounts import UserGroupEnum


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "from_attributes": True
    }

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return validate_password_strength(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class PasswordChangeRequestSchema(BaseEmailPasswordSchema):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value):
        return validate_password_strength(value)


class PasswordChangeResponseSchema(BaseEmailPasswordSchema):
    pass


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLogoutRequestSchema(BaseModel):
    refresh_token: str


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = {
        "from_attributes": True
    }


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(BaseModel):
    message: str


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangeUserGroupRequestSchema(BaseModel):
    user_id: int
    new_group: UserGroupEnum

    model_config = {
        "from_attributes": True
    }
