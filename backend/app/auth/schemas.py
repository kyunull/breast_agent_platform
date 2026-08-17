from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin_developer", "medical_user"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    role: Role
    is_active: bool
