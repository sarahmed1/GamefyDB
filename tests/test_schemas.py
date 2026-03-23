import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.schemas.record import GameRecordSchema

def test_valid_game_record():
    data = {
        "id": 1,
        "source_file": "file1.html",
        "title": "Super Game",
        "url": "https://example.com/game",
        "status": "extracted",
        "extracted_at": datetime.now(timezone.utc),
        "raw_data": {"key": "value"}
    }
    record = GameRecordSchema(**data)
    assert record.source_file == "file1.html"
    assert record.title == "Super Game"
    assert record.id == 1

def test_invalid_game_record_missing_required():
    data = {
        "title": "Super Game"
        # source_file is missing
    }
    with pytest.raises(ValidationError):
        GameRecordSchema(**data)

def test_invalid_data_types():
    data = {
        "source_file": 123, # should be string but pydantic coerces int to str... wait, strict=True?
        "title": "Game",
        "url": 1234, # coerces to string if not strict mode
        # Let's test something that fails coercion
        "extracted_at": "not a date"
    }
    with pytest.raises(ValidationError):
        GameRecordSchema(**data)
        
    data2 = {
        "source_file": "file.html",
        "title": ["Not", "a", "string"] # List cannot be coerced to string in v2 usually
    }
    with pytest.raises(ValidationError):
        GameRecordSchema(**data2)
