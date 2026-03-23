import pytest
from pathlib import Path
from src.backend.pipeline.extractor import extract_html_file
from src.backend.pipeline.normalizer import normalize_data
from src.backend.schemas.record import SessionRecordSchema, CashRecordSchema, StockRecordSchema, MemberRecordSchema

DATA_DIR = Path("data")

@pytest.mark.skipif(not DATA_DIR.exists(), reason="Data directory not found")
def test_extract_and_normalize_all():
    html_files = list(DATA_DIR.glob("*.html"))
    assert len(html_files) > 0, "No HTML files found to test"
    
    total_records = 0
    for file in html_files:
        extracted = extract_html_file(str(file))
        assert extracted is not None, f"Failed to extract {file}"
        
        record_type, raw_data = extracted
        assert len(raw_data) > 0, f"No records found in {file}"
        
        normalized = normalize_data(extracted)
        assert len(normalized) == len(raw_data), "Normalization dropped some rows"
        
        # Verify schema types based on expected report
        if "SESSION" in file.name:
            assert isinstance(normalized[0][1], SessionRecordSchema)
        elif "CASH" in file.name:
            assert isinstance(normalized[0][1], CashRecordSchema)
        elif "STOCK" in file.name:
            assert isinstance(normalized[0][1], StockRecordSchema)
        elif "MEMBER" in file.name:
            assert isinstance(normalized[0][1], MemberRecordSchema)
            
        total_records += len(normalized)
        
    assert total_records > 1000, "Expected thousands of records from the FastReport test suite"
