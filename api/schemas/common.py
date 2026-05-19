from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=500)


class DateRangeQuery(BaseModel):
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

    model_config = {"populate_by_name": True}
