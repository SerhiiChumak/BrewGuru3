from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    @classmethod
    def default_order_by(cls):
        return None

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }
