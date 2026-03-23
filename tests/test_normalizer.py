import pytest
import logging
from src.pipeline.normalizer import normalize_data
from src.schemas.record import GameRecordSchema

def test_normalize_valid_data():
    raw_data = [
        {
            "source_file": "file1.html",
            "title": "Game 1",
            "url": "http://example.com/1",
            "status": "extracted"
        },
        {
            "source_file": "file2.html",
            "title": "Game 2",
            "url": "http://example.com/2",
            "status": "extracted"
        }
    ]
    
    result = normalize_data(raw_data)
    assert len(result) == 2
    assert all(isinstance(r, GameRecordSchema) for r in result)
    assert result[0].title == "Game 1"
    assert result[1].url == "http://example.com/2"

def test_normalize_drops_invalid_rows(caplog):
    raw_data = [
        {
            "source_file": "valid.html",
            "title": "Valid Game",
            "url": "http://example.com/valid",
            "status": "extracted"
        },
        {
            # Missing source_file (required by GameRecordSchema)
            "title": "Invalid Game",
            "url": "http://example.com/invalid"
        },
        {
            "source_file": "toolong.html",
            "title": "X" * 300, # Assuming max_length=255
            "status": "extracted"
        }
    ]
    
    with caplog.at_level(logging.ERROR):
        result = normalize_data(raw_data)
        
    assert len(result) == 1
    assert result[0].title == "Valid Game"
    assert "Validation error" in caplog.text

def test_normalize_empty_list():
    result = normalize_data([])
    assert result == []
