from __future__ import annotations

from pydantic import BaseModel


class CategoryRow(BaseModel):
    category: str
    amount: float


class TerminalRow(BaseModel):
    terminal_id: int
    terminal: str
    amount: float
    transactions: int | None = None


class CashierRow(BaseModel):
    cashier_id: int
    cashier: str
    amount: float
    transactions: int | None = None


class OverviewKPIs(BaseModel):
    total_revenue: float
    transaction_count: int
    unique_cashiers: int
    unique_terminals: int
    top_categories: list[CategoryRow]
    top_terminals: list[TerminalRow]


class HeatmapResponse(BaseModel):
    matrix: list[list[float]]  # 24 rows × 7 cols (hour × weekday)


class RowsResponse(BaseModel):
    rows: list[TerminalRow] | list[CashierRow]
