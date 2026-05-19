from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.deps import current_active_user
from api.models import User
from api.schemas.kpis import HeatmapResponse, OverviewKPIs
from api.services import kpis as kpi_service
from api.services.data_cache import cache

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("/overview", response_model=OverviewKPIs)
async def overview(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    _: User = Depends(current_active_user),
):
    return kpi_service.overview(cache.schema, from_, to)


@router.get("/heatmap", response_model=HeatmapResponse)
async def heatmap(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    _: User = Depends(current_active_user),
):
    return kpi_service.heatmap(cache.schema, from_, to)


@router.get("/by-terminal")
async def by_terminal(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    _: User = Depends(current_active_user),
):
    return {"rows": kpi_service.by_terminal(cache.schema, from_, to)}


@router.get("/by-cashier")
async def by_cashier(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    _: User = Depends(current_active_user),
):
    return {"rows": kpi_service.by_cashier(cache.schema, from_, to)}
