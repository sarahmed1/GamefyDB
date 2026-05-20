from __future__ import annotations

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.apps.api.deps import current_active_user
from backend.apps.api.models import User
from backend.apps.api.schemas.common import PagedResponse
from backend.apps.api.schemas.facts import FactCash, FactSession
from backend.apps.api.services.data_cache import cache

router = APIRouter(prefix="/facts", tags=["facts"])


def _page(df: pd.DataFrame, page: int, size: int) -> pd.DataFrame:
    start = (page - 1) * size
    return df.iloc[start : start + size]


def _clean_na(record: dict) -> dict:
    out = {}
    for k, v in record.items():
        if v is None:
            out[k] = None
        elif isinstance(v, float) and pd.isna(v):
            out[k] = None
        elif hasattr(v, "to_pydatetime"):
            out[k] = v.to_pydatetime() if pd.notna(v) else None
        elif pd.isna(v):
            out[k] = None
        else:
            out[k] = v
    return out


@router.get("/cash", response_model=PagedResponse[FactCash])
async def get_cash(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    terminal_id: int | None = None,
    cashier_id: int | None = None,
    item_id: int | None = None,
    member_id: int | None = None,
    payment: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    _: User = Depends(current_active_user),
):
    df = cache.schema["fact_transaction"]
    if from_ is not None:
        df = df[df["date"] >= pd.Timestamp(from_)]
    if to is not None:
        df = df[df["date"] <= pd.Timestamp(to)]
    if terminal_id is not None:
        df = df[df["terminal_id"] == terminal_id]
    if cashier_id is not None:
        df = df[df["cashier_id"] == cashier_id]
    if item_id is not None:
        df = df[df["item_id"] == item_id]
    if member_id is not None:
        df = df[df["member_id"] == member_id]
    if payment is not None:
        df = df[df["payment"] == payment]

    total = len(df)
    rows = _page(df, page, size).to_dict(orient="records")
    items = [FactCash.model_validate(_clean_na(r)) for r in rows]
    return PagedResponse[FactCash](items=items, total=total, page=page, size=size)


@router.get("/sessions", response_model=PagedResponse[FactSession])
async def get_sessions(
    terminal_id: int | None = None,
    cashier_id: int | None = None,
    member_id: int | None = None,
    session_type: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    _: User = Depends(current_active_user),
):
    df = cache.schema["fact_session"]
    if terminal_id is not None:
        df = df[df["terminal_id"] == terminal_id]
    if cashier_id is not None:
        df = df[df["cashier_id"] == cashier_id]
    if member_id is not None:
        df = df[df["member_id"] == member_id]
    if session_type is not None:
        df = df[df["session_type"] == session_type]

    total = len(df)
    rows = _page(df, page, size).to_dict(orient="records")
    items = [FactSession.model_validate(_clean_na(r)) for r in rows]
    return PagedResponse[FactSession](items=items, total=total, page=page, size=size)


@router.get("/stock")
async def get_stock(_: User = Depends(current_active_user)):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="stock movements are not modelled as a fact; see /api/dims/item",
    )


@router.get("/members")
async def get_members(_: User = Depends(current_active_user)):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="member stats are not modelled as a fact; see /api/dims/member",
    )




