import os
import pytest
import logging
from src.pipeline.extractor import extract_html_file

@pytest.fixture
def sample_html_file(tmp_path):
    file_path = tmp_path / "sample.html"
    file_path.write_text("""
        <html>
            <head><title>Test Game</title></head>
            <body>
                <a href="http://example.com/game">Game Link</a>
                <div class="status">active</div>
            </body>
        </html>
    """)
    return str(file_path)

@pytest.fixture
def empty_html_file(tmp_path):
    file_path = tmp_path / "empty.html"
    file_path.write_text("")
    return str(file_path)

@pytest.fixture
def malformed_html_file(tmp_path):
    file_path = tmp_path / "malformed.html"
    # missing closing tags, just garbage
    file_path.write_text("<<<>>>html><body<div class='test'>broken")
    return str(file_path)

def test_extract_valid_html(sample_html_file):
    result = extract_html_file(sample_html_file)
    assert result is not None
    assert result['source_file'] == sample_html_file
    assert result['title'] == 'Test Game'
    assert result['url'] == 'http://example.com/game'
    assert result['status'] == 'extracted'

def test_extract_empty_html(empty_html_file, caplog):
    with caplog.at_level(logging.WARNING):
        result = extract_html_file(empty_html_file)
    assert result is None
    assert "Empty or unparseable HTML" in caplog.text

def test_extract_missing_critical_fields(tmp_path, caplog):
    file_path = tmp_path / "missing.html"
    # no title or url
    file_path.write_text("<html><body><p>hello</p></body></html>")
    with caplog.at_level(logging.WARNING):
        result = extract_html_file(str(file_path))
    assert result is None
    assert "Missing critical fields" in caplog.text
