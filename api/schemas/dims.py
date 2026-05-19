from __future__ import annotations

from pydantic import BaseModel


class DimCashier(BaseModel):
    cashier_id: int
    cashier_name: str


class DimTerminal(BaseModel):
    terminal_id: int
    terminal: str
    terminal_type: str


class DimItem(BaseModel):
    item_id: int
    item: str
    category: str | None = None
    unit_price: float | None = None
    quantite: float | None = None
    total_revenue: float | None = None


class DimMember(BaseModel):
    member_id: int
    username: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    usage_tnd: float | None = None
    orders_tnd: float | None = None
    usb_tnd: float | None = None
    total_tnd: float | None = None
    duration_min: float | None = None
