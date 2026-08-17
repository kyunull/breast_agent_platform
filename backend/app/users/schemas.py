from pydantic import BaseModel, Field

from app.auth.schemas import Role, UserRead


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=1024)
    role: Role


__all__ = ["Role", "UserCreate", "UserRead"]
