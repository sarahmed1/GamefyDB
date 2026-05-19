from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def _filter_by_date(df: pd.DataFrame, date_from: datetime | None, date_to: datetime | None) -> pd.DataFrame:
    if "date" not in df.columns:
        return df
    out = df
    if date_from is not None:
        out = out[out["date"] >= pd.Timestamp(date_from)]
    if date_to is not None:
        out = out[out["date"] <= pd.Timestamp(date_to)]
    return out


def overview(schema: dict[str, pd.DataFrame], date_from, date_to) -> dict[str, Any]:
    tx = _filter_by_date(schema["fact_transaction"], date_from, date_to)

    if len(tx) == 0:
        return {
            "total_revenue": 0.0,
            "transaction_count": 0,
            "unique_cashiers": 0,
            "unique_terminals": 0,
            "top_categories": [],
            "top_terminals": [],
        }

    total_revenue = float(tx["amount"].sum())
    top_categories = (
        tx.groupby("category", dropna=True)["amount"].sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
        .to_dict(orient="records")
    )

    terminal_totals = (
        tx.dropna(subset=["terminal_id"])
        .groupby("terminal_id")["amount"].sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    terminal_lookup = dict(zip(
        schema["dim_terminal"]["terminal_id"],
        schema["dim_terminal"]["terminal"],
    ))
    top_terminals = [
        {"terminal_id": int(r["terminal_id"]),
         "terminal": terminal_lookup.get(int(r["terminal_id"]), str(int(r["terminal_id"]))),
         "amount": float(r["amount"])}
        for _, r in terminal_totals.iterrows()
    ]

    return {
        "total_revenue": total_revenue,
        "transaction_count": int(len(tx)),
        "unique_cashiers": int(tx["cashier_id"].nunique()),
        "unique_terminals": int(tx["terminal_id"].dropna().nunique()),
        "top_categories": [
            {"category": r["category"], "amount": float(r["amount"])}
            for r in top_categories
        ],
        "top_terminals": top_terminals,
    }


def heatmap(schema: dict[str, pd.DataFrame], date_from, date_to) -> dict[str, Any]:
    tx = _filter_by_date(schema["fact_transaction"], date_from, date_to)
    matrix = [[0.0] * 7 for _ in range(24)]
    if len(tx) == 0:
        return {"matrix": matrix}
    tx = tx.dropna(subset=["date"])
    hours = tx["date"].dt.hour.astype(int)
    weekdays = tx["date"].dt.weekday.astype(int)  # Monday=0 .. Sunday=6
    grouped = pd.DataFrame({"hour": hours, "weekday": weekdays, "amount": tx["amount"]})
    pivot = grouped.groupby(["hour", "weekday"])["amount"].sum().reset_index()
    for _, row in pivot.iterrows():
        matrix[int(row["hour"])][int(row["weekday"])] = float(row["amount"])
    return {"matrix": matrix}


def by_terminal(schema: dict[str, pd.DataFrame], date_from, date_to) -> list[dict[str, Any]]:
    tx = _filter_by_date(schema["fact_transaction"], date_from, date_to)
    if len(tx) == 0:
        return []
    grouped = (
        tx.dropna(subset=["terminal_id"])
        .groupby("terminal_id")["amount"].agg(["sum", "count"])
        .reset_index()
    )
    lookup = dict(zip(schema["dim_terminal"]["terminal_id"], schema["dim_terminal"]["terminal"]))
    return [
        {
            "terminal_id": int(r["terminal_id"]),
            "terminal": lookup.get(int(r["terminal_id"]), str(int(r["terminal_id"]))),
            "amount": float(r["sum"]),
            "transactions": int(r["count"]),
        }
        for _, r in grouped.iterrows()
    ]


def by_cashier(schema: dict[str, pd.DataFrame], date_from, date_to) -> list[dict[str, Any]]:
    tx = _filter_by_date(schema["fact_transaction"], date_from, date_to)
    if len(tx) == 0:
        return []
    grouped = (
        tx.dropna(subset=["cashier_id"])
        .groupby("cashier_id")["amount"].agg(["sum", "count"])
        .reset_index()
    )
    lookup = dict(zip(schema["dim_cashier"]["cashier_id"], schema["dim_cashier"]["cashier_name"]))
    return [
        {
            "cashier_id": int(r["cashier_id"]),
            "cashier": lookup.get(int(r["cashier_id"]), str(int(r["cashier_id"]))),
            "amount": float(r["sum"]),
            "transactions": int(r["count"]),
        }
        for _, r in grouped.iterrows()
    ]
