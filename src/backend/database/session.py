from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

DEFAULT_DB_URL = "sqlite:///local.db"

def init_db(db_url: str = DEFAULT_DB_URL):
    """Initializes the database by creating tables if they don't exist."""
    engine = create_engine(db_url, echo=False)
    # Import models here to ensure they are registered with Base before create_all
    import src.backend.database.models  # noqa
    Base.metadata.create_all(engine)
    return engine

def get_session(db_url: str = DEFAULT_DB_URL):
    """Yields a database session."""
    engine = create_engine(db_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def empty_database(db_url: str = DEFAULT_DB_URL) -> int:
    """Deletes all rows from all managed tables and returns total deleted rows."""
    engine = create_engine(db_url, echo=False)
    import src.backend.database.models  # noqa

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    total_deleted = 0

    with SessionLocal() as session:
        try:
            for table in reversed(Base.metadata.sorted_tables):
                result = session.execute(delete(table))
                total_deleted += result.rowcount or 0
            session.commit()
        except Exception:
            session.rollback()
            raise

    return total_deleted
