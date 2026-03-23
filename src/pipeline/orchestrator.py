import logging
import math
from pathlib import Path
from typing import List, Callable, Optional

from src.pipeline.extractor import extract_html_file
from src.pipeline.normalizer import normalize_data
from src.database.session import get_session, init_db, DEFAULT_DB_URL
from src.database.models import GameRecord

logger = logging.getLogger(__name__)

def run_pipeline(
    target_directory: str,
    batch_size: int = 50,
    db_url: str = DEFAULT_DB_URL,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None
):
    """
    Scans target_directory for .html files and processes them in batches.
    Extracts raw data, normalizes it, and inserts it into the database.
    Rolls back on failure.
    """
    def _log(msg: str, level: int = logging.INFO):
        logger.log(level, msg)
        if log_callback:
            log_callback(msg)

    _log(f"Starting pipeline on {target_directory} (batch_size={batch_size})")
    
    # Initialize the DB schema to ensure tables exist
    init_db(db_url)
    
    # Glob for HTML files
    target_path = Path(target_directory)
    html_files = list(target_path.glob("*.html"))
    total_files = len(html_files)
    
    if progress_callback:
        progress_callback(0, total_files)
    
    if total_files == 0:
        _log(f"No .html files found in {target_directory}", logging.WARNING)
        return
        
    num_batches = math.ceil(total_files / batch_size)
    _log(f"Found {total_files} files. Processing in {num_batches} batches.")
    
    processed_count = 0
    
    for i in range(num_batches):
        if should_cancel and should_cancel():
            _log("Pipeline cancelled by user. Gracefully shutting down.")
            break
            
        batch_files = html_files[i * batch_size : (i + 1) * batch_size]
        _log(f"Processing batch {i + 1}/{num_batches} ({len(batch_files)} files)")
        
        # 1. Extraction
        raw_data_list = []
        for filepath in batch_files:
            if should_cancel and should_cancel():
                break
            extracted = extract_html_file(str(filepath))
            if extracted:
                raw_data_list.append(extracted)
            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_files)
                
        if should_cancel and should_cancel():
            _log("Pipeline cancelled during extraction. Gracefully shutting down.")
            # Commit whatever we extracted in this partial batch before breaking
            
        # 2. Normalization
        normalized_schemas = normalize_data(raw_data_list)
        
        # 3. DB Insertion
        if not normalized_schemas:
            _log("No valid records to insert in this batch.")
            if should_cancel and should_cancel():
                break
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
            _log(f"Successfully committed {len(models_to_insert)} records to DB.")
        except Exception as e:
            session.rollback()
            _log(f"Error committing batch {i + 1}: {e}", logging.ERROR)
            raise
        finally:
            # Close session by exhausting the generator
            try:
                next(session_gen)
            except StopIteration:
                pass
                
        if should_cancel and should_cancel():
            _log("Pipeline cancelled after batch commit. Gracefully shutting down.")
            break

    _log("Pipeline completed successfully.")
