# Phase 2 — Data Cache + Read Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-memory star-schema cache built at API startup and expose read-only `/api/kpis/*`, `/api/facts/*`, and `/api/dims/*` endpoints that serve cached pandas aggregations as JSON.

**Architecture:** A singleton `DataCache` calls `gamefydb.pipeline.run_pipeline()` on startup and stores the resulting star-schema dict in memory; if any of the four source files is missing or fails to parse, the cache falls back to empty DataFrames with the correct columns so endpoints can still respond. KPI endpoints compute pandas aggregations on the cached `fact_transaction` DataFrame; fact endpoints return paged/filtered slices; dim endpoints return full dim tables. Dates are stored as `datetime64` in the cache (re-parsed from the string form `run_pipeline` produces) so the KPI service can filter cheaply on `from`/`to`.

**Tech Stack:** FastAPI 0.115+, pandas, pydantic v2, pytest, pytest-asyncio, fastapi `TestClient`. No new dependencies.

**Scope deviations from spec §5 (documented; do not "fix"):**

- The actual star schema produced by `gamefydb/pipeline.py` has **6 tables**: `dim_cashier`, `dim_terminal`, `dim_item`, `dim_member`, `fact_transaction`, `fact_session`. There is **no** `fact_stock_movements` (stock is aggregated into `dim_item`) and **no** `fact_member_stats` (member totals live in `dim_member`). Phase 2 therefore exposes:
  - `/api/facts/cash` → `fact_transaction`
  - `/api/facts/sessions` → `fact_session`
  - `/api/facts/stock` → 404 *(not implemented; documented as out of scope for Phase 2)*
  - `/api/facts/members` → 404 *(stats live in `/api/dims/member`)*
- `fact_session` has **no date column** in the source data. Date-range filters on `/api/facts/sessions` are accepted but ignored (with a `Warning` header). KPI heatmap / overview run on `fact_transaction` only.

**Python invocation (per CLAUDE.md):** Every shell example uses the literal path `C:/Users/sarah/AppData/Local/Python/bin/python` — Python is **not** on PATH.

---

## File Structure

**Create:**

- `api/services/__init__.py`
- `api/services/data_cache.py` — `DataCache` class + module-level `cache` singleton
- `api/services/kpis.py` — pandas aggregations: overview / heatmap / by-terminal / by-cashier
- `api/routers/__init__.py`
- `api/routers/kpis.py` — `/api/kpis/*` endpoints
- `api/routers/facts.py` — `/api/facts/{cash,sessions}` endpoints
- `api/routers/dims.py` — `/api/dims/{cashier,terminal,item,member}` endpoints
- `api/schemas/common.py` — `PagedResponse`, `DateRangeQuery`
- `api/schemas/kpis.py` — KPI response models
- `api/schemas/facts.py` — fact-row pydantic models
- `api/schemas/dims.py` — dim-row pydantic models
- `api/tests/test_data_cache.py`
- `api/tests/test_kpis.py`
- `api/tests/test_facts.py`
- `api/tests/test_dims.py`
- `api/tests/_fixtures/synthetic_schema.py` — small in-memory star schema for tests

**Modify:**

- `api/main.py` — add `lifespan` context manager that calls `cache.build()` on startup; register new routers
- `api/schemas/__init__.py` — re-export new schema names
- `api/tests/conftest.py` — add `synthetic_schema` and `cached_app` fixtures that inject a synthetic schema into the cache singleton
- `CLAUDE.md` — append Phase 2 endpoints to the API section (local edit only; CLAUDE.md is gitignored)

---

## Task 1: `DataCache` skeleton with empty-schema fallback

**Files:**

- Create: `api/services/__init__.py` (empty)
- Create: `api/services/data_cache.py`
- Create: `api/tests/test_data_cache.py`

- [ ] **Step 1: Write the failing test for empty-schema columns**

Create `api/tests/test_data_cache.py`:

```python
import pandas as pd
import pytest

from api.services.data_cache import DataCache, EMPTY_COLUMNS


def test_empty_schema_has_all_tables():
    cache = DataCache()
    assert set(cache.schema.keys()) == {
        "dim_cashier", "dim_terminal", "dim_item", "dim_member",
        "fact_transaction", "fact_session",
    }


def test_empty_schema_columns_match_contract():
    cache = DataCache()
    for table, columns in EMPTY_COLUMNS.items():
        assert list(cache.schema[table].columns) == columns
        assert len(cache.schema[table]) == 0


def test_loaded_flag_starts_false():
    cache = DataCache()
    assert cache.loaded is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_data_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.services'`.

- [ ] **Step 3: Implement `DataCache` skeleton**

Create `api/services/__init__.py` (empty file).

Create `api/services/data_cache.py`:

```python
"""In-memory star-schema cache built at API startup.

The cache stores the star schema produced by ``gamefydb.pipeline.run_pipeline``
in memory. Endpoints read these DataFrames directly — no SQL warehouse in v1.

Failure mode: if any of the four source ``.xlsx`` files is missing or fails to
parse, the cache initializes as empty DataFrames with the correct columns so
KPI/fact/dim endpoints can still respond (empty payloads) instead of 500ing.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

EMPTY_COLUMNS: dict[str, list[str]] = {
    "dim_cashier": ["cashier_id", "cashier_name"],
    "dim_terminal": ["terminal_id", "terminal", "terminal_type"],
    "dim_item": ["item_id", "item", "category", "unit_price", "quantite", "total_revenue"],
    "dim_member": [
        "member_id", "username", "firstname", "lastname",
        "usage_tnd", "orders_tnd", "usb_tnd", "total_tnd", "duration_min",
    ],
    "fact_transaction": [
        "tx_id", "date", "type", "payment", "category", "amount",
        "cashier_id", "terminal_id", "item_id", "member_id",
    ],
    "fact_session": [
        "session_id", "session_type", "order_transfer", "usb_data",
        "usage", "discount", "total", "duration_min",
        "cashier_id", "terminal_id", "member_id",
    ],
}


def _empty_schema() -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame({col: [] for col in cols}) for name, cols in EMPTY_COLUMNS.items()}


class DataCache:
    def __init__(self) -> None:
        self.schema: dict[str, pd.DataFrame] = _empty_schema()
        self.loaded: bool = False
        self.source_dir: Path | None = None

    def build(self, input_dir: str | Path) -> None:
        """Build the star schema from ``input_dir``. On any failure, leave the
        cache as the empty schema and log a warning. Never raises."""
        from gamefydb.pipeline import run_pipeline  # local import: heavy deps

        try:
            schema, _cash, _stock = run_pipeline(str(input_dir), use_augment=True)
            schema["fact_transaction"]["date"] = pd.to_datetime(
                schema["fact_transaction"]["date"], errors="coerce"
            )
            self.schema = schema
            self.loaded = True
            self.source_dir = Path(input_dir)
            logger.info("DataCache built from %s — %d transactions, %d sessions",
                        input_dir,
                        len(schema["fact_transaction"]),
                        len(schema["fact_session"]))
        except Exception as exc:
            logger.warning("DataCache build failed (%s); falling back to empty schema.", exc)
            self.schema = _empty_schema()
            self.loaded = False


cache = DataCache()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_data_cache.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add api/services/__init__.py api/services/data_cache.py api/tests/test_data_cache.py
git commit -m "feat(api): add DataCache skeleton with empty-schema fallback"
```

---

## Task 2: `DataCache.build()` happy path + failure path

**Files:**

- Modify: `api/tests/test_data_cache.py`

- [ ] **Step 1: Add failing tests for `build()`**

Append to `api/tests/test_data_cache.py`:

```python
import os
from pathlib import Path
from unittest.mock import patch


def test_build_with_missing_dir_keeps_empty_schema(tmp_path):
    cache = DataCache()
    cache.build(tmp_path / "does-not-exist")  # must NOT raise

    assert cache.loaded is False
    assert len(cache.schema["fact_transaction"]) == 0
    assert list(cache.schema["fact_transaction"].columns) == EMPTY_COLUMNS["fact_transaction"]


def test_build_with_real_excel_dir_loads_schema():
    repo_root = Path(__file__).resolve().parents[2]
    excel_dir = repo_root / "excel"
    if not excel_dir.exists() or not (excel_dir / "extended_cash.xlsx").exists():
        pytest.skip("extended_*.xlsx not present in excel/")

    cache = DataCache()
    cache.build(excel_dir)

    assert cache.loaded is True
    assert len(cache.schema["fact_transaction"]) > 0
    assert pd.api.types.is_datetime64_any_dtype(cache.schema["fact_transaction"]["date"])


def test_build_pipeline_exception_logged_and_swallowed(caplog):
    cache = DataCache()
    with patch("gamefydb.pipeline.run_pipeline", side_effect=RuntimeError("boom")):
        with caplog.at_level("WARNING"):
            cache.build("/tmp/whatever")

    assert cache.loaded is False
    assert "DataCache build failed" in caplog.text
```

- [ ] **Step 2: Run tests to verify they pass (no implementation change needed; the skeleton already swallows exceptions)**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_data_cache.py -v`
Expected: 6 passed (or 5 passed + 1 skipped if `excel/extended_cash.xlsx` is absent).

- [ ] **Step 3: Commit**

```powershell
git add api/tests/test_data_cache.py
git commit -m "test(api): cover DataCache build happy and failure paths"
```

---

## Task 3: Wire cache build into FastAPI lifespan

**Files:**

- Modify: `api/main.py`
- Modify: `api/config.py` — add `excel_dir` setting
- Modify: `api/tests/conftest.py` — add `synthetic_schema` + `cached_app` fixtures
- Create: `api/tests/_fixtures/__init__.py`
- Create: `api/tests/_fixtures/synthetic_schema.py`

- [ ] **Step 1: Add `excel_dir` to `Settings`**

Modify `api/config.py`. Replace the `Settings` body to add `excel_dir`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GAMEFYDB_", extra="ignore")

    secret: str = "dev-secret-change-me"
    database_url: str = "sqlite+aiosqlite:///./api/gamefydb.sqlite"
    cookie_name: str = "gamefydb_session"
    cookie_max_age: int = 60 * 60 * 24  # 24h
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    excel_dir: str = str(Path(__file__).resolve().parents[1] / "excel")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Create synthetic-schema fixture module**

Create `api/tests/_fixtures/__init__.py` (empty).

Create `api/tests/_fixtures/synthetic_schema.py`:

```python
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
```

- [ ] **Step 3: Extend `conftest.py` with cache fixtures**

Modify `api/tests/conftest.py`. After the existing fixtures, append:

```python
from api.services import data_cache as _data_cache_mod
from api.services.data_cache import cache as data_cache
from api.tests._fixtures.synthetic_schema import build_synthetic_schema


@pytest.fixture(scope="session", autouse=True)
def _disable_real_cache_build():
    """Prevent the lifespan startup from hitting the real ``excel/`` dir on every
    TestClient context entry. Individual tests that need to verify the build
    call (e.g. ``test_app_startup_builds_cache``) re-monkeypatch ``build``
    themselves and that takes precedence inside the test scope."""
    original = _data_cache_mod.DataCache.build
    _data_cache_mod.DataCache.build = lambda self, input_dir: None
    yield
    _data_cache_mod.DataCache.build = original


@pytest.fixture(scope="function")
def synthetic_schema():
    """A small deterministic star schema for KPI/facts/dims tests."""
    return build_synthetic_schema()


@pytest.fixture(scope="function")
def cached_app(client, synthetic_schema):
    """Reuse the authenticated TestClient from `client`, but install
    the synthetic schema into the module-level DataCache singleton."""
    previous = data_cache.schema, data_cache.loaded
    data_cache.schema = synthetic_schema
    data_cache.loaded = True
    yield client
    data_cache.schema, data_cache.loaded = previous
```

- [ ] **Step 4: Write a failing test asserting startup builds the cache**

Append to `api/tests/test_data_cache.py`:

```python
def test_app_startup_builds_cache(monkeypatch):
    from api.services import data_cache as dc_mod

    called = {}

    def fake_build(self, input_dir):
        called["dir"] = str(input_dir)
        self.loaded = True

    monkeypatch.setattr(dc_mod.DataCache, "build", fake_build)

    from api.main import app
    from fastapi.testclient import TestClient
    with TestClient(app):
        pass

    assert "dir" in called
    assert called["dir"].endswith("excel")
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_data_cache.py::test_app_startup_builds_cache -v`
Expected: FAIL — cache build is not yet wired into startup.

- [ ] **Step 6: Wire the lifespan in `api/main.py`**

Modify `api/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import build_auth_router
from api.config import get_settings
from api.deps import require_admin
from api.models import User
from api.services.data_cache import cache as data_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    data_cache.build(settings.excel_dir)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GamefyDB API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(build_auth_router(), prefix="/api")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # TODO(phase-9): remove when real admin routes exist
    @app.get("/api/_admin_ping")
    async def admin_ping(user: User = Depends(require_admin)) -> dict[str, str]:
        return {"hello": user.email}

    return app


app = create_app()
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_data_cache.py -v`
Expected: all tests passed (including the new startup test).

- [ ] **Step 8: Commit**

```powershell
git add api/main.py api/config.py api/tests/conftest.py api/tests/_fixtures/__init__.py api/tests/_fixtures/synthetic_schema.py api/tests/test_data_cache.py
git commit -m "feat(api): build DataCache on app startup via lifespan"
```

---

## Task 4: Common pagination + date-range schemas

**Files:**

- Create: `api/schemas/common.py`
- Modify: `api/schemas/__init__.py`

- [ ] **Step 1: Implement common schemas**

Create `api/schemas/common.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=500)


class DateRangeQuery(BaseModel):
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

    model_config = {"populate_by_name": True}
```

- [ ] **Step 2: Update `api/schemas/__init__.py`**

Check the current file first with Read; then append:

```python
from api.schemas.common import PagedResponse, DateRangeQuery

__all__ = [*globals().get("__all__", []), "PagedResponse", "DateRangeQuery"]
```

(If `__all__` does not already exist, just add an explicit `__all__` list including the existing `UserRead`, `UserCreate`, `UserUpdate`.)

- [ ] **Step 3: Smoke check the imports**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -c "from api.schemas import PagedResponse, DateRangeQuery; print('ok')"`
Expected output: `ok`

- [ ] **Step 4: Commit**

```powershell
git add api/schemas/common.py api/schemas/__init__.py
git commit -m "feat(api): add PagedResponse and DateRangeQuery schemas"
```

---

## Task 5: `/api/dims/*` endpoints

**Files:**

- Create: `api/schemas/dims.py`
- Create: `api/routers/__init__.py` (empty)
- Create: `api/routers/dims.py`
- Modify: `api/main.py`
- Create: `api/tests/test_dims.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_dims.py`:

```python
def test_dim_cashier_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/cashier")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    names = {item["cashier_name"] for item in data["items"]}
    assert names == {"taktek", "youssef"}


def test_dim_terminal_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/terminal")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    types = {item["terminal_type"] for item in data["items"]}
    assert types == {"Standard PC", "PlayStation"}


def test_dim_item_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/item")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["item"] == "Coke"
    assert items[0]["unit_price"] == 3.0


def test_dim_member_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/member")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "amine"
    assert items[0]["total_tnd"] == 62.0


def test_dim_unknown_returns_404(cached_app):
    r = cached_app.get("/api/dims/widgets")
    assert r.status_code == 404


def test_dim_endpoint_requires_auth(client):
    # `client` (without `cached_app`) is still authenticated via the seeded
    # admin cookie; we want to verify unauth → 401. Use a fresh TestClient.
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        r = c.get("/api/dims/cashier")
        assert r.status_code == 401
```

- [ ] **Step 2: Run test to confirm failure**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_dims.py -v`
Expected: 6 FAILs (or errors) — no router yet.

- [ ] **Step 3: Implement dim schemas**

Create `api/schemas/dims.py`:

```python
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
```

- [ ] **Step 4: Implement the router**

Create `api/routers/__init__.py` (empty).

Create `api/routers/dims.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import current_active_user
from api.models import User
from api.schemas.common import PagedResponse
from api.schemas.dims import DimCashier, DimItem, DimMember, DimTerminal
from api.services.data_cache import cache

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
```

- [ ] **Step 5: Register the router in `main.py`**

Modify `api/main.py`. Add the import and the include_router call:

```python
from api.routers import dims as dims_router

# ... inside create_app(), after the existing include_router:
app.include_router(dims_router.router, prefix="/api")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_dims.py -v`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```powershell
git add api/schemas/dims.py api/routers/__init__.py api/routers/dims.py api/main.py api/tests/test_dims.py
git commit -m "feat(api): add /api/dims/{cashier,terminal,item,member} endpoints"
```

---

## Task 6: `/api/facts/cash` endpoint with paging + filters

**Files:**

- Create: `api/schemas/facts.py`
- Create: `api/routers/facts.py`
- Modify: `api/main.py`
- Create: `api/tests/test_facts.py`

- [ ] **Step 1: Write failing tests for cash facts**

Create `api/tests/test_facts.py`:

```python
def test_facts_cash_returns_paged_rows(cached_app):
    r = cached_app.get("/api/facts/cash?page=1&size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 6
    assert len(body["items"]) == 6
    assert body["items"][0]["tx_id"] == 1


def test_facts_cash_paging(cached_app):
    r = cached_app.get("/api/facts/cash?page=2&size=2")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2
    assert body["size"] == 2
    assert body["total"] == 6
    assert len(body["items"]) == 2
    assert body["items"][0]["tx_id"] == 3


def test_facts_cash_date_filter(cached_app):
    r = cached_app.get("/api/facts/cash?from=2026-05-11&to=2026-05-11T23:59:59")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {3, 4}


def test_facts_cash_terminal_filter(cached_app):
    r = cached_app.get("/api/facts/cash?terminal_id=1")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {1, 4}


def test_facts_cash_cashier_filter(cached_app):
    r = cached_app.get("/api/facts/cash?cashier_id=2")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {2, 4, 6}


def test_facts_cash_method_filter(cached_app):
    r = cached_app.get("/api/facts/cash?payment=Credit%20Card")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {3, 6}


def test_facts_cash_unauth(client):
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        r = c.get("/api/facts/cash")
        assert r.status_code == 401
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_facts.py -v`
Expected: 7 FAILs.

- [ ] **Step 3: Implement fact schemas**

Create `api/schemas/facts.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FactCash(BaseModel):
    tx_id: int
    date: datetime | None = None
    type: str | None = None
    payment: str | None = None
    category: str | None = None
    amount: float | None = None
    cashier_id: int | None = None
    terminal_id: int | None = None
    item_id: int | None = None
    member_id: int | None = None


class FactSession(BaseModel):
    session_id: int
    session_type: str | None = None
    order_transfer: float | None = None
    usb_data: float | None = None
    usage: float | None = None
    discount: float | None = None
    total: float | None = None
    duration_min: float | None = None
    cashier_id: int | None = None
    terminal_id: int | None = None
    member_id: int | None = None
```

- [ ] **Step 4: Implement the facts router**

Create `api/routers/facts.py`:

```python
from __future__ import annotations

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import current_active_user
from api.models import User
from api.schemas.common import PagedResponse
from api.schemas.facts import FactCash, FactSession
from api.services.data_cache import cache

router = APIRouter(prefix="/facts", tags=["facts"])


def _page(df: pd.DataFrame, page: int, size: int) -> pd.DataFrame:
    start = (page - 1) * size
    return df.iloc[start : start + size]


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
```

- [ ] **Step 5: Register router in `main.py`**

Modify `api/main.py`:

```python
from api.routers import dims as dims_router, facts as facts_router

# ... inside create_app(), after the dims include:
app.include_router(facts_router.router, prefix="/api")
```

- [ ] **Step 6: Run tests**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_facts.py -v -k cash`
Expected: cash tests pass.

- [ ] **Step 7: Commit**

```powershell
git add api/schemas/facts.py api/routers/facts.py api/main.py api/tests/test_facts.py
git commit -m "feat(api): add /api/facts/cash with filters and paging"
```

---

## Task 7: `/api/facts/sessions` + stock/members 404s

**Files:**

- Modify: `api/tests/test_facts.py`

- [ ] **Step 1: Add failing tests for sessions + 404 behaviour**

Append to `api/tests/test_facts.py`:

```python
def test_facts_sessions_returns_paged_rows(cached_app):
    r = cached_app.get("/api/facts/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    types = {it["session_type"] for it in body["items"]}
    assert types == {"Walk-in", "Member"}


def test_facts_sessions_member_filter(cached_app):
    r = cached_app.get("/api/facts/sessions?session_type=Member")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["member_id"] == 1001


def test_facts_stock_returns_404(cached_app):
    r = cached_app.get("/api/facts/stock")
    assert r.status_code == 404


def test_facts_members_returns_404(cached_app):
    r = cached_app.get("/api/facts/members")
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_facts.py -v`
Expected: all 11 tests pass (sessions + stock/members handlers already exist from Task 6).

- [ ] **Step 3: Commit**

```powershell
git add api/tests/test_facts.py
git commit -m "test(api): cover /api/facts/sessions and unsupported-fact 404s"
```

---

## Task 8: KPI service — overview aggregation

**Files:**

- Create: `api/services/kpis.py`
- Create: `api/tests/test_kpis.py`

- [ ] **Step 1: Write failing test for overview aggregation**

Create `api/tests/test_kpis.py`:

```python
import pandas as pd

from api.services.kpis import overview
from api.tests._fixtures.synthetic_schema import build_synthetic_schema


def test_overview_totals_match_synthetic_schema():
    schema = build_synthetic_schema()
    result = overview(schema, date_from=None, date_to=None)

    assert result["total_revenue"] == 91.0  # sum of synthetic amounts
    assert result["transaction_count"] == 6
    assert result["unique_cashiers"] == 2
    assert result["unique_terminals"] == 2
    assert result["top_categories"][0]["category"] in {
        "Computer Incomes", "Playstation Incomes", "Member Transactions"
    }


def test_overview_date_filter_narrows_results():
    schema = build_synthetic_schema()
    result = overview(
        schema,
        date_from=pd.Timestamp("2026-05-12"),
        date_to=pd.Timestamp("2026-05-12T23:59:59"),
    )
    assert result["transaction_count"] == 2
    assert result["total_revenue"] == 43.0  # 25 + 18


def test_overview_empty_schema_returns_zeros():
    from api.services.data_cache import _empty_schema
    result = overview(_empty_schema(), date_from=None, date_to=None)
    assert result["total_revenue"] == 0.0
    assert result["transaction_count"] == 0
    assert result["top_categories"] == []
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v`
Expected: ImportError — `overview` does not exist yet.

- [ ] **Step 3: Implement `overview`**

Create `api/services/kpis.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add api/services/kpis.py api/tests/test_kpis.py
git commit -m "feat(api): add KPI overview aggregation"
```

---

## Task 9: KPI service — heatmap, by-terminal, by-cashier

**Files:**

- Modify: `api/services/kpis.py`
- Modify: `api/tests/test_kpis.py`

- [ ] **Step 1: Write failing tests**

Append to `api/tests/test_kpis.py`:

```python
from api.services.kpis import heatmap, by_terminal, by_cashier


def test_heatmap_shape_is_24x7():
    schema = build_synthetic_schema()
    result = heatmap(schema, date_from=None, date_to=None)
    assert "matrix" in result
    assert len(result["matrix"]) == 24      # rows = hours
    assert all(len(row) == 7 for row in result["matrix"])
    # Verify at least one populated cell from the synthetic data
    assert any(any(cell > 0 for cell in row) for row in result["matrix"])


def test_by_terminal_returns_named_rows():
    schema = build_synthetic_schema()
    rows = by_terminal(schema, date_from=None, date_to=None)
    by_name = {r["terminal"]: r for r in rows}
    assert "PC-01" in by_name and "PS5-01" in by_name
    # PC-01 transactions: 10 + 15 = 25
    assert by_name["PC-01"]["amount"] == 25.0
    # PS5-01: 20 + 18 = 38
    assert by_name["PS5-01"]["amount"] == 38.0


def test_by_cashier_returns_named_rows():
    schema = build_synthetic_schema()
    rows = by_cashier(schema, date_from=None, date_to=None)
    by_name = {r["cashier"]: r for r in rows}
    assert by_name["taktek"]["amount"] == 38.0    # 10 + 3 + 25
    assert by_name["youssef"]["amount"] == 53.0   # 20 + 15 + 18
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v`
Expected: ImportError on `heatmap`, `by_terminal`, `by_cashier`.

- [ ] **Step 3: Implement the three functions**

Append to `api/services/kpis.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v`
Expected: all 6 tests passed.

- [ ] **Step 5: Commit**

```powershell
git add api/services/kpis.py api/tests/test_kpis.py
git commit -m "feat(api): add KPI heatmap, by-terminal, by-cashier aggregations"
```

---

## Task 10: KPI router — wire endpoints

**Files:**

- Create: `api/schemas/kpis.py`
- Create: `api/routers/kpis.py`
- Modify: `api/main.py`
- Modify: `api/tests/test_kpis.py`

- [ ] **Step 1: Write failing router tests**

Append to `api/tests/test_kpis.py`:

```python
def test_kpis_overview_endpoint(cached_app):
    r = cached_app.get("/api/kpis/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_revenue"] == 91.0
    assert body["transaction_count"] == 6


def test_kpis_heatmap_endpoint(cached_app):
    r = cached_app.get("/api/kpis/heatmap")
    assert r.status_code == 200
    body = r.json()
    assert len(body["matrix"]) == 24
    assert len(body["matrix"][0]) == 7


def test_kpis_by_terminal_endpoint(cached_app):
    r = cached_app.get("/api/kpis/by-terminal")
    assert r.status_code == 200
    body = r.json()
    names = {row["terminal"] for row in body["rows"]}
    assert names == {"PC-01", "PS5-01"}


def test_kpis_by_cashier_endpoint(cached_app):
    r = cached_app.get("/api/kpis/by-cashier")
    assert r.status_code == 200
    body = r.json()
    names = {row["cashier"] for row in body["rows"]}
    assert names == {"taktek", "youssef"}


def test_kpis_unauth(client):
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        r = c.get("/api/kpis/overview")
        assert r.status_code == 401
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v -k endpoint`
Expected: 4 FAILs.

- [ ] **Step 3: Implement KPI schemas**

Create `api/schemas/kpis.py`:

```python
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
```

- [ ] **Step 4: Implement the router**

Create `api/routers/kpis.py`:

```python
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
```

- [ ] **Step 5: Register router in `main.py`**

Modify `api/main.py`:

```python
from api.routers import dims as dims_router, facts as facts_router, kpis as kpis_router

# ... inside create_app(), after facts include:
app.include_router(kpis_router.router, prefix="/api")
```

- [ ] **Step 6: Run all KPI tests**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest api/tests/test_kpis.py -v`
Expected: all tests passed.

- [ ] **Step 7: Commit**

```powershell
git add api/schemas/kpis.py api/routers/kpis.py api/main.py api/tests/test_kpis.py
git commit -m "feat(api): add /api/kpis/{overview,heatmap,by-terminal,by-cashier}"
```

---

## Task 11: Full test sweep + CLAUDE.md update

**Files:**

- Modify: `CLAUDE.md` (local only — file is gitignored)

- [ ] **Step 1: Run the full test suite**

Run: `C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v`
Expected: all Phase 1 + Phase 2 tests pass. Capture and report counts.

- [ ] **Step 2: Boot the API locally to confirm startup works**

Run (in a separate terminal — do NOT block the agent):

```powershell
$env:GAMEFYDB_EXCEL_DIR = "C:/Users/sarah/GamefyDB/excel"
& C:/Users/sarah/AppData/Local/Python/bin/python -m uvicorn api.main:app --port 8000
```

Then in another shell:

```powershell
& C:/Users/sarah/AppData/Local/Python/bin/python -c "import httpx; print(httpx.get('http://localhost:8000/api/health').json())"
```

Expected: `{'status': 'ok'}`. If the server fails to start because `excel/` is empty, that is an expected pass condition — the cache logs a warning and the server still serves `/api/health`.

Stop the server with Ctrl+C. **Do not commit anything in this step.**

- [ ] **Step 3: Update `CLAUDE.md`** (local edit only — file is gitignored)

Locate the existing `## API (Phase 1+)` section in `CLAUDE.md` and append a Phase 2 subsection after the auth bullet:

```markdown
### Phase 2 read endpoints (require login cookie)

```
GET /api/kpis/overview?from=&to=
GET /api/kpis/heatmap?from=&to=          24×7 matrix (hour × weekday)
GET /api/kpis/by-terminal?from=&to=
GET /api/kpis/by-cashier?from=&to=

GET /api/facts/cash?from=&to=&terminal_id=&cashier_id=&item_id=&member_id=&payment=&page=&size=
GET /api/facts/sessions?terminal_id=&cashier_id=&member_id=&session_type=&page=&size=
GET /api/facts/stock           → 404 (stock is dim_item, not a fact in v1)
GET /api/facts/members         → 404 (member stats live in dim_member)

GET /api/dims/{cashier|terminal|item|member}
```

Cache: built from `excel/extended_*.xlsx` at startup via `gamefydb.pipeline.run_pipeline`.
If files are missing the cache is empty and endpoints return 0 rows (intentional).
```

- [ ] **Step 4: Final git status check**

Run: `git status` and `git log --oneline -15`
Expected: clean working tree (CLAUDE.md remains untracked/ignored), 10 new commits on top of `1ea6d62`.

- [ ] **Step 5: Done — report Phase 2 summary**

No commit in this step. Report to the user:

- Final test count (`pytest -v` last line)
- Commit log for Phase 2
- Confirmation that CLAUDE.md was updated locally (not committed)
- Any deviations from the plan (e.g. extra error handling that proved necessary)
