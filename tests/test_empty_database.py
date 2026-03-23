from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.backend.database.models import CashRecord, MemberRecord, SessionRecord, StockRecord
from src.backend.database.session import empty_database, init_db


def _count_rows(db_url: str, model_cls) -> int:
    engine = create_engine(db_url, echo=False)
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model_cls)) or 0


def test_empty_database_deletes_all_managed_tables(tmp_path: Path):
    db_path = tmp_path / "empty_db_test.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    init_db(db_url)

    engine = create_engine(db_url, echo=False)
    with Session(engine) as session:
        session.add(SessionRecord(source_file="s1.html"))
        session.add(CashRecord(source_file="c1.html"))
        session.add(StockRecord(source_file="st1.html"))
        session.add(MemberRecord(source_file="m1.html"))
        session.commit()

    assert _count_rows(db_url, SessionRecord) == 1
    assert _count_rows(db_url, CashRecord) == 1
    assert _count_rows(db_url, StockRecord) == 1
    assert _count_rows(db_url, MemberRecord) == 1

    deleted_count = empty_database(db_url)

    assert deleted_count >= 4
    assert _count_rows(db_url, SessionRecord) == 0
    assert _count_rows(db_url, CashRecord) == 0
    assert _count_rows(db_url, StockRecord) == 0
    assert _count_rows(db_url, MemberRecord) == 0
