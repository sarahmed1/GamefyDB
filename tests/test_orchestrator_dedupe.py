from pathlib import Path

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

    fixture_src = Path("data") / "SESSION DATA 01-09-2025.html"
    fixture_dst = source_dir / fixture_src.name
    fixture_dst.write_text(fixture_src.read_text(encoding="utf-8"), encoding="utf-8")

    db_path = tmp_path / "pipeline.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    run_pipeline(str(source_dir), batch_size=10, db_url=db_url)
    first_count = _session_count(db_url)
    assert first_count > 0

    run_pipeline(str(source_dir), batch_size=10, db_url=db_url)
    second_count = _session_count(db_url)

    assert second_count == first_count
