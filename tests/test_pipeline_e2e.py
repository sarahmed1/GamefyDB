import pytest
import re
from pathlib import Path
from src.backend.pipeline.extractor import SUPPORTED_INPUT_PATTERNS, extract_file
from src.backend.pipeline.normalizer import normalize_data
from src.backend.schemas.record import SessionRecordSchema, CashRecordSchema, StockRecordSchema, MemberRecordSchema

DATA_DIR = Path("data")
NOISE_PATTERN = re.compile(r"Page\s*\d+\s*/\s*\d+|\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}", re.IGNORECASE)


def _list_supported_files(data_dir: Path) -> list[Path]:
    return sorted(
        {
            file_path
            for pattern in SUPPORTED_INPUT_PATTERNS
            for file_path in data_dir.glob(pattern)
        }
    )

@pytest.mark.skipif(not DATA_DIR.exists(), reason="Data directory not found")
def test_extract_and_normalize_all():
    input_files = _list_supported_files(DATA_DIR)
    assert len(input_files) > 0, "No supported source files found to test"
    
    total_records = 0
    dropped_total = 0
    for file in input_files:
        extracted = extract_file(str(file))
        assert extracted is not None, f"Failed to extract {file}"
        
        record_type, raw_data = extracted
        assert len(raw_data) > 0, f"No records found in {file}"
        
        normalized = normalize_data(extracted)
        assert len(normalized) > 0, f"Normalization produced no rows for {file}"
        assert len(normalized) <= len(raw_data), "Normalization cannot create more rows than extraction"
        dropped_total += len(raw_data) - len(normalized)
        
        # Verify schema types based on expected report
        if "SESSION" in file.name:
            assert isinstance(normalized[0][1], SessionRecordSchema)
        elif "CASH" in file.name:
            assert isinstance(normalized[0][1], CashRecordSchema)
        elif "STOCK" in file.name:
            assert isinstance(normalized[0][1], StockRecordSchema)
        elif "MEMBER" in file.name:
            assert isinstance(normalized[0][1], MemberRecordSchema)

        for _, schema in normalized:
            serialized = " | ".join(str(v) for v in schema.model_dump().values() if v is not None)
            assert not NOISE_PATTERN.search(serialized), f"Noise marker leaked after normalization in {file}: {serialized}"
            
        total_records += len(normalized)
        
    assert dropped_total > 0, "Expected normalization to drop footer/header noise rows"
    assert total_records > 1000, "Expected thousands of records from the FastReport test suite"
