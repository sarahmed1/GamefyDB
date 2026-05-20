from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FactCash(BaseModel):
    tx_id: int
    date: datetime | None = None
    type: str | None = None
    payment: str | None = None
    category: str | None = None
    amount: float | None = None
    cashier_id: int | None = None
    terminal_id: int | None = None
    item_id: int | None = None
    member_id: int | None = None


class FactSession(BaseModel):
    session_id: int
    session_type: str | None = None
    order_transfer: float | None = None
    usb_data: float | None = None
    usage: float | None = None
    discount: float | None = None
    total: float | None = None
    duration_min: float | None = None
    cashier_id: int | None = None
    terminal_id: int | None = None
    member_id: int | None = None
