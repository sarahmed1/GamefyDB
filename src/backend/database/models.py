from sqlalchemy import String
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from src.backend.database.session import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    cashier: Mapped[Optional[str]]
    terminal: Mapped[Optional[str]]
    session_type: Mapped[Optional[str]]
    free_time_minutes: Mapped[int] = mapped_column(default=0)
    paused_minutes: Mapped[int] = mapped_column(default=0)
    duration_minutes: Mapped[int] = mapped_column(default=0)
    order_transfer_tnd: Mapped[float] = mapped_column(default=0.0)
    usb_data_tnd: Mapped[float] = mapped_column(default=0.0)
    usage_tnd: Mapped[float] = mapped_column(default=0.0)
    discount_tnd: Mapped[float] = mapped_column(default=0.0)
    total_amount_tnd: Mapped[float] = mapped_column(default=0.0)
    extracted_at: Mapped[datetime] = mapped_column(default=_utc_now)

class CashRecord(Base):
    __tablename__ = "cash_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    cashier: Mapped[Optional[str]]
    date: Mapped[Optional[datetime]]
    income_expense: Mapped[Optional[str]]
    payment_method: Mapped[Optional[str]]
    transaction_type: Mapped[Optional[str]]
    amount_tnd: Mapped[float] = mapped_column(default=0.0)
    comment: Mapped[Optional[str]]
    extracted_at: Mapped[datetime] = mapped_column(default=_utc_now)

class StockRecord(Base):
    __tablename__ = "stock_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    cashier: Mapped[Optional[str]]
    date: Mapped[Optional[datetime]]
    item_name: Mapped[Optional[str]]
    category: Mapped[Optional[str]]
    in_out: Mapped[Optional[str]]
    quantity: Mapped[int] = mapped_column(default=0)
    unit_price_tnd: Mapped[float] = mapped_column(default=0.0)
    total_amount_tnd: Mapped[float] = mapped_column(default=0.0)
    comment: Mapped[Optional[str]]
    extracted_at: Mapped[datetime] = mapped_column(default=_utc_now)

class MemberRecord(Base):
    __tablename__ = "member_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    member_id: Mapped[Optional[int]]
    username: Mapped[Optional[str]]
    firstname: Mapped[Optional[str]]
    lastname: Mapped[Optional[str]]
    duration_minutes: Mapped[int] = mapped_column(default=0)
    usage_tnd: Mapped[float] = mapped_column(default=0.0)
    order_transfer_tnd: Mapped[float] = mapped_column(default=0.0)
    usb_data_tnd: Mapped[float] = mapped_column(default=0.0)
    total_amount_tnd: Mapped[float] = mapped_column(default=0.0)
    extracted_at: Mapped[datetime] = mapped_column(default=_utc_now)
