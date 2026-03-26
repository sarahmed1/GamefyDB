from pathlib import Path

import pandas as pd

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.backend.database.models import SessionRecord
from src.backend.pipeline.orchestrator import run_pipeline


def _session_count(db_url: str) -> int:
    engine = create_engine(db_url, echo=False)
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(SessionRecord)) or 0


def test_run_pipeline_is_rerun_safe_for_same_source_files(tmp_path: Path):
    source_dir = tmp_path / "data"
    source_dir.mkdir()

    fixture_dst = source_dir / "SESSION DATA 01-09-2025.xlsx"
    pd.DataFrame(
        [
            {
                "Cashier": "cashier-1",
                "Terminal": "terminal-1",
                "Session Type": "Standard",
                "Free Time": "0 min",
                "Paused": "5 min",
                "Duration": "1 h 0 min",
                "Order/Transfer": "1,00 TND",
                "USB Data": "0,00 TND",
                "Usage": "4,00 TND",
                "Discount": "0,00 TND",
                "Total Amount": "5,00 TND",
            }
        ]
    ).to_excel(fixture_dst, index=False)

    db_path = tmp_path / "pipeline.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    run_pipeline(str(source_dir), batch_size=10, db_url=db_url)
    first_count = _session_count(db_url)
    assert first_count > 0

    run_pipeline(str(source_dir), batch_size=10, db_url=db_url)
    second_count = _session_count(db_url)

    assert second_count == first_count
