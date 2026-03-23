from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class BaseRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: Optional[int] = None
    source_file: str = Field(..., max_length=255)
    extracted_at: Optional[datetime] = None

class SessionRecordSchema(BaseRecordSchema):
    cashier: Optional[str] = None
    terminal: Optional[str] = None
    session_type: Optional[str] = None
    free_time_minutes: int = 0
    paused_minutes: int = 0
    duration_minutes: int = 0
    order_transfer_tnd: float = 0.0
    usb_data_tnd: float = 0.0
    usage_tnd: float = 0.0
    discount_tnd: float = 0.0
    total_amount_tnd: float = 0.0

class CashRecordSchema(BaseRecordSchema):
    cashier: Optional[str] = None
    date: Optional[datetime] = None
    income_expense: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_type: Optional[str] = None
    amount_tnd: float = 0.0
    comment: Optional[str] = None

class StockRecordSchema(BaseRecordSchema):
    cashier: Optional[str] = None
    date: Optional[datetime] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    in_out: Optional[str] = None
    quantity: int = 0
    unit_price_tnd: float = 0.0
    total_amount_tnd: float = 0.0
    comment: Optional[str] = None

class MemberRecordSchema(BaseRecordSchema):
    member_id: Optional[int] = None
    username: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    duration_minutes: int = 0
    usage_tnd: float = 0.0
    order_transfer_tnd: float = 0.0
    usb_data_tnd: float = 0.0
    total_amount_tnd: float = 0.0
