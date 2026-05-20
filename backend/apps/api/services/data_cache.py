"""In-memory star-schema cache built at API startup.

The cache stores the star schema produced by ``packages.etl.pipeline.run_pipeline``
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
        from backend.packages.etl.pipeline import run_pipeline  # local import: heavy deps

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




