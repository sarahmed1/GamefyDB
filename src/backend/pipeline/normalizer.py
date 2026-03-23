import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime
import re

from src.backend.schemas.record import (
    SessionRecordSchema,
    CashRecordSchema,
    StockRecordSchema,
    MemberRecordSchema
)

logger = logging.getLogger(__name__)

def parse_currency(val: Any) -> float:
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).upper().replace('TND', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
    try:
        # Some values might be "1 745.44", remove spaces
        val_str = re.sub(r'[^\d\.\-]', '', val_str)
        if not val_str:
            return 0.0
        return float(val_str)
    except ValueError:
        return 0.0

def parse_duration(val: Any) -> int:
    if pd.isna(val) or val is None:
        return 0
    val_str = str(val).lower()
    if not val_str or val_str.strip() == '':
        return 0
        
    # parse formats like "3 h 54 min", "10 min", "223 h 26 min"
    hours = 0
    minutes = 0
    
    h_match = re.search(r'(\d+)\s*h', val_str)
    if h_match:
        hours = int(h_match.group(1))
        
    m_match = re.search(r'(\d+)\s*m', val_str)
    if m_match:
        minutes = int(m_match.group(1))
        
    return hours * 60 + minutes

def parse_datetime(val: Any) -> datetime | None:
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    try:
        # format: "10.01.2026 16:52:51"
        return datetime.strptime(val_str, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return None

def safe_str(val: Any) -> str | None:
    if pd.isna(val) or val is None:
        return None
    return str(val).strip()

def normalize_data(extracted: Tuple[str, List[Dict[str, Any]]]) -> List[Any]:
    if not extracted:
        return []
        
    record_type, raw_data_list = extracted
    if not raw_data_list:
        return []

    df = pd.DataFrame(raw_data_list)
    # We replace NaNs with None right here before doing anything
    df = df.replace({np.nan: None})
    
    valid_records = []

    if record_type == "session":
        for i, row in df.iterrows():
            try:
                data = {
                    "source_file": safe_str(row.get("source_file")),
                    "cashier": safe_str(row.get("Cashier")),
                    "terminal": safe_str(row.get("Terminal")),
                    "session_type": safe_str(row.get("Session Type")),
                    "free_time_minutes": parse_duration(row.get("Free Time")),
                    "paused_minutes": parse_duration(row.get("Paused")),
                    "duration_minutes": parse_duration(row.get("Duration")),
                    "order_transfer_tnd": parse_currency(row.get("Order/Transfer") or row.get("Order/Trans.")),
                    "usb_data_tnd": parse_currency(row.get("USB Data")),
                    "usage_tnd": parse_currency(row.get("Usage")),
                    "discount_tnd": parse_currency(row.get("Discount")),
                    "total_amount_tnd": parse_currency(row.get("Total Amount"))
                }
                valid_records.append((record_type, SessionRecordSchema(**{k: v for k,v in data.items() if v is not None})))
            except Exception as e:
                logger.error(f"Error normalizing session row {i}: {e}")

    elif record_type == "cash":
        for i, row in df.iterrows():
            try:
                data = {
                    "source_file": safe_str(row.get("source_file")),
                    "cashier": safe_str(row.get("Cashier")),
                    "date": parse_datetime(row.get("Date")),
                    "income_expense": safe_str(row.get("Income/Expense")),
                    "payment_method": safe_str(row.get("Payment Method")),
                    "transaction_type": safe_str(row.get("Transaction Type")),
                    "amount_tnd": parse_currency(row.get("Amount")),
                    "comment": safe_str(row.get("Comment"))
                }
                valid_records.append((record_type, CashRecordSchema(**{k: v for k,v in data.items() if v is not None})))
            except Exception as e:
                logger.error(f"Error normalizing cash row {i}: {e}")

    elif record_type == "stock":
        for i, row in df.iterrows():
            try:
                # quantity parse
                qty_raw = row.get("Quantity", 0)
                qty = 0
                if qty_raw and not pd.isna(qty_raw):
                    try:
                        qty = int(float(str(qty_raw).strip()))
                    except:
                        qty = 0
                
                data = {
                    "source_file": safe_str(row.get("source_file")),
                    "cashier": safe_str(row.get("Cashier")),
                    "date": parse_datetime(row.get("Date")),
                    "item_name": safe_str(row.get("Item Name")),
                    "category": safe_str(row.get("Category")),
                    "in_out": safe_str(row.get("In/Out")),
                    "quantity": qty,
                    "unit_price_tnd": parse_currency(row.get("Unit Price")),
                    "total_amount_tnd": parse_currency(row.get("Total Amount")),
                    "comment": safe_str(row.get("Comment"))
                }
                valid_records.append((record_type, StockRecordSchema(**{k: v for k,v in data.items() if v is not None})))
            except Exception as e:
                logger.error(f"Error normalizing stock row {i}: {e}")

    elif record_type == "member":
        for i, row in df.iterrows():
            try:
                m_id_raw = row.get("ID")
                m_id = None
                if m_id_raw and not pd.isna(m_id_raw):
                    try:
                        m_id = int(float(str(m_id_raw).strip()))
                    except:
                        pass
                
                # Handling order/trans. name variations
                order_col = row.get("Ord.& Trans.") if "Ord.& Trans." in row else row.get("Order/Transfer")

                data = {
                    "source_file": safe_str(row.get("source_file")),
                    "member_id": m_id,
                    "username": safe_str(row.get("Username")),
                    "firstname": safe_str(row.get("Firstname")),
                    "lastname": safe_str(row.get("Lastname")),
                    "duration_minutes": parse_duration(row.get("Duration")),
                    "usage_tnd": parse_currency(row.get("Usage")),
                    "order_transfer_tnd": parse_currency(order_col),
                    "usb_data_tnd": parse_currency(row.get("USB Data")),
                    "total_amount_tnd": parse_currency(row.get("Total Amount"))
                }
                valid_records.append((record_type, MemberRecordSchema(**{k: v for k,v in data.items() if v is not None})))
            except Exception as e:
                logger.error(f"Error normalizing member row {i}: {e}")

    return valid_records
