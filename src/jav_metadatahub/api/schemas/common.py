from __future__ import annotations

from pydantic import BaseModel


class ListResponse[T](BaseModel):
    data: list[T]
    limit: int
    offset: int
    total: int
