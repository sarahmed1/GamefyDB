from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.apps.api.deps import current_active_user
from backend.apps.api.models import User
from backend.apps.api.schemas.common import PagedResponse
from backend.apps.api.schemas.dims import DimCashier, DimItem, DimMember, DimTerminal
from backend.apps.api.services.data_cache import cache

router = APIRouter(prefix="/dims", tags=["dims"])

_DIM_MAP = {
    "cashier":  ("dim_cashier",  DimCashier),
    "terminal": ("dim_terminal", DimTerminal),
    "item":     ("dim_item",     DimItem),
    "member":   ("dim_member",   DimMember),
}


@router.get("/{name}")
async def get_dim(name: str, _: User = Depends(current_active_user)):
    if name not in _DIM_MAP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"unknown dim '{name}'")
    table_name, model = _DIM_MAP[name]
    df = cache.schema[table_name]
    items = [model.model_validate(row) for row in df.to_dict(orient="records")]
    return PagedResponse(items=items, total=len(items), page=1, size=max(len(items), 1))




