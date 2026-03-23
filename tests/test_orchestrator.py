import pytest
from pathlib import Path
from src.pipeline.orchestrator import run_pipeline
from src.database.session import init_db, get_session
from src.database.models import GameRecord

@pytest.fixture
def mock_html_dir(tmp_path):
    # Create mock HTML files
    for i in range(5):
        file_path = tmp_path / f"test_{i}.html"
        file_path.write_text(f"<html><head><title>Test {i}</title></head><body><a href='http://test.com/{i}'>Link</a></body></html>", encoding="utf-8")
    
    # Create one malformed file
    malformed_path = tmp_path / "malformed.html"
    malformed_path.write_text("not html", encoding="utf-8")
    
    return tmp_path

def test_run_pipeline_success(mock_html_dir):
    # Setup test DB
    db_path = mock_html_dir / "test.db"
    db_url = f"sqlite:///{db_path}"
    
    # Run pipeline with batch size 2
    run_pipeline(target_directory=str(mock_html_dir), batch_size=2, db_url=db_url)
    
    # Verify records were inserted
    session_gen = get_session(db_url)
    session = next(session_gen)
    
    try:
        records = session.query(GameRecord).all()
        assert len(records) == 5
        
        # Check values
        titles = [r.title for r in records]
        assert "Test 0" in titles
        assert "Test 4" in titles
        
        # Check malformed file was skipped
        assert not any(r.source_file.endswith("malformed.html") for r in records)
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass

def test_run_pipeline_transaction_rollback(mock_html_dir, monkeypatch):
    db_path = mock_html_dir / "test.db"
    db_url = f"sqlite:///{db_path}"
    
    class FakeSession:
        def __init__(self):
            self.rollbacked = False
            self.committed = False
            
        def add_all(self, *args, **kwargs):
            pass
            
        def commit(self):
            self.committed = True
            raise Exception("Mock DB failure")
            
        def rollback(self):
            self.rollbacked = True
            
        def close(self):
            pass
            
    fake_session = FakeSession()
    
    def mock_get_session(url):
        yield fake_session
        
    monkeypatch.setattr("src.pipeline.orchestrator.get_session", mock_get_session)
    
    with pytest.raises(Exception, match="Mock DB failure"):
        run_pipeline(target_directory=str(mock_html_dir), batch_size=2, db_url=db_url)
        
    assert fake_session.rollbacked
