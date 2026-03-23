import logging
import pandas as pd
from pydantic import ValidationError
from typing import List, Dict, Any
from src.schemas.record import GameRecordSchema

logger = logging.getLogger(__name__)

def normalize_data(raw_data_list: List[Dict[str, Any]]) -> List[GameRecordSchema]:
    if not raw_data_list:
        return []

    # Load into Pandas for any vectorized operations
    df = pd.DataFrame(raw_data_list)
    
    # Example vectorization: fill NaN values, clean strings, etc.
    if 'title' in df.columns:
        df['title'] = df['title'].astype(str).str.strip().replace({'nan': None, '': None})
    if 'url' in df.columns:
        df['url'] = df['url'].astype(str).str.strip().replace({'nan': None, '': None})

    valid_records: List[GameRecordSchema] = []

    # Iterate and validate
    for i, row in df.iterrows():
        try:
            # Dropna for the row so we don't pass pandas NaNs instead of Nones
            clean_row = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
            
            record = GameRecordSchema(**clean_row)
            valid_records.append(record)
        except ValidationError as e:
            logger.error(f"Validation error on row {i} (data: {clean_row}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing row {i}: {e}")

    return valid_records
