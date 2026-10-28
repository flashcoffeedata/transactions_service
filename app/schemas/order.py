import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderUpsert(BaseModel):
    order_id: uuid.UUID
    status: str = Field(min_length=1, max_length=100)

    @field_validator("status")
    @classmethod
    def status_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("status must not be blank")
        return value


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class OrderListResponse(BaseModel):
    data: list[OrderResponse]
    pagination: Pagination
