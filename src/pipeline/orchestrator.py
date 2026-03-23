import logging
import math
from pathlib import Path
from typing import List

from src.pipeline.extractor import extract_html_file
from src.pipeline.normalizer import normalize_data
from src.database.session import get_session, init_db, DEFAULT_DB_URL
from src.database.models import GameRecord

logger = logging.getLogger(__name__)

def run_pipeline(target_directory: str, batch_size: int = 50, db_url: str = DEFAULT_DB_URL):
    """
    Scans target_directory for .html files and processes them in batches.
    Extracts raw data, normalizes it, and inserts it into the database.
    Rolls back on failure.
    """
    logger.info(f"Starting pipeline on {target_directory} (batch_size={batch_size})")
    
    # Initialize the DB schema to ensure tables exist
    init_db(db_url)
    
    # Glob for HTML files
    target_path = Path(target_directory)
    html_files = list(target_path.glob("*.html"))
    total_files = len(html_files)
    
    if total_files == 0:
        logger.warning(f"No .html files found in {target_directory}")
        return
        
    num_batches = math.ceil(total_files / batch_size)
    logger.info(f"Found {total_files} files. Processing in {num_batches} batches.")
    
    for i in range(num_batches):
        batch_files = html_files[i * batch_size : (i + 1) * batch_size]
        logger.info(f"Processing batch {i + 1}/{num_batches} ({len(batch_files)} files)")
        
        # 1. Extraction
        raw_data_list = []
        for filepath in batch_files:
            extracted = extract_html_file(str(filepath))
            if extracted:
                raw_data_list.append(extracted)
                
        # 2. Normalization
        normalized_schemas = normalize_data(raw_data_list)
        
        # 3. DB Insertion
        if not normalized_schemas:
            logger.info("No valid records to insert in this batch.")
            continue
            
        # Get a DB session
        session_gen = get_session(db_url)
        session = next(session_gen)
        try:
            # Convert schemas to SQLAlchemy models
            models_to_insert = []
            for schema in normalized_schemas:
                model_data = schema.model_dump(exclude_unset=True, exclude_none=True)
                # Remove id so it can be auto-generated
                model_data.pop("id", None)
                models_to_insert.append(GameRecord(**model_data))
                
            session.add_all(models_to_insert)
            session.commit()
            logger.info(f"Successfully committed {len(models_to_insert)} records to DB.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error committing batch {i + 1}: {e}")
            raise
        finally:
            # Close session by exhausting the generator
            try:
                next(session_gen)
            except StopIteration:
                pass

logger.info("Pipeline completed successfully.")
