import os
import pytest
from sqlalchemy import inspect
from src.database.session import init_db, get_session
from src.database.models import Base

def test_init_db_creates_tables(tmp_path):
    # Use a temporary database for testing
    db_path = tmp_path / "test.db"
    test_db_url = f"sqlite:///{db_path}"
    
    # Call init_db with the test URL
    engine = init_db(test_db_url)
    
    # Check if file was created
    assert db_path.exists()
    
    # Check if tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "game_records" in tables

def test_get_session(tmp_path):
    db_path = tmp_path / "test.db"
    test_db_url = f"sqlite:///{db_path}"
    
    init_db(test_db_url)
    
    # Get session
    session_generator = get_session(test_db_url)
    session = next(session_generator)
    
    # Check that session works and can execute a simple query
    try:
        from src.database.models import GameRecord
        result = session.query(GameRecord).all()
        assert isinstance(result, list)
    finally:
        session.close()
