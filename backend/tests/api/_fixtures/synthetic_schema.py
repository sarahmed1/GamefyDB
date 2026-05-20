"""Tiny synthetic star schema used by router tests.

Two cashiers, two terminals (1 PC + 1 PS5), one item, one member, and
six transactions split across categories. Designed to make KPI
aggregations deterministic and easy to assert.
"""

from __future__ import annotations

import pandas as pd


def build_synthetic_schema() -> dict[str, pd.DataFrame]:
    dim_cashier = pd.DataFrame({"cashier_id": [1, 2], "cashier_name": ["taktek", "youssef"]})
    dim_terminal = pd.DataFrame({
        "terminal_id": [1, 2],
        "terminal": ["PC-01", "PS5-01"],
        "terminal_type": ["Standard PC", "PlayStation"],
    })
    dim_item = pd.DataFrame({
        "item_id": [1],
        "item": ["Coke"],
        "category": ["Drink"],
        "unit_price": [3.0],
        "quantite": [10],
        "total_revenue": [30.0],
    })
    dim_member = pd.DataFrame({
        "member_id": [1001],
        "username": ["amine"],
        "firstname": ["Amine"],
        "lastname": ["Ben Ali"],
        "usage_tnd": [50.0],
        "orders_tnd": [12.0],
        "usb_tnd": [0.0],
        "total_tnd": [62.0],
        "duration_min": [180.0],
    })
    fact_transaction = pd.DataFrame({
        "tx_id": [1, 2, 3, 4, 5, 6],
        "date": pd.to_datetime([
            "2026-05-10 10:00:00",
            "2026-05-10 14:30:00",
            "2026-05-11 11:00:00",
            "2026-05-11 18:15:00",
            "2026-05-12 09:45:00",
            "2026-05-12 20:00:00",
        ]),
        "type": ["Income"] * 6,
        "payment": ["Cash", "Cash", "Credit Card", "Cash", "Cash", "Credit Card"],
        "category": [
            "Computer Incomes", "Playstation Incomes", "Order Incomes",
            "Computer Incomes", "Member Transactions", "Playstation Incomes",
        ],
        "amount": [10.0, 20.0, 3.0, 15.0, 25.0, 18.0],
        "cashier_id": [1, 2, 1, 2, 1, 2],
        "terminal_id": [1, 2, None, 1, None, 2],
        "item_id":     [None, None, 1, None, None, None],
        "member_id":   [None, None, None, None, 1001, None],
    }).astype({"terminal_id": "Int64", "item_id": "Int64", "member_id": "Int64"})

    fact_session = pd.DataFrame({
        "session_id": [1, 2],
        "session_type": ["Walk-in", "Member"],
        "order_transfer": [0.0, 0.0],
        "usb_data": [0.0, 0.0],
        "usage": [10.0, 25.0],
        "discount": [0.0, 0.0],
        "total": [10.0, 25.0],
        "duration_min": [60.0, 120.0],
        "cashier_id": [1, 2],
        "terminal_id": [1, 2],
        "member_id": [None, 1001],
    }).astype({"member_id": "Int64"})

    return {
        "dim_cashier": dim_cashier,
        "dim_terminal": dim_terminal,
        "dim_item": dim_item,
        "dim_member": dim_member,
        "fact_transaction": fact_transaction,
        "fact_session": fact_session,
    }
