import logging
import math
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import delete

from src.backend.pipeline.extractor import SUPPORTED_INPUT_PATTERNS, extract_file
from src.backend.pipeline.normalizer import normalize_data
from src.backend.database.session import get_session, init_db, DEFAULT_DB_URL
from src.backend.database.models import SessionRecord, CashRecord, StockRecord, MemberRecord

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
    Scans target_directory for supported input files and processes them in batches.
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
    
    # Glob for supported source files.
    target_path = Path(target_directory)
    input_files = sorted(
        {
            filepath
            for pattern in SUPPORTED_INPUT_PATTERNS
            for filepath in target_path.glob(pattern)
        }
    )
    total_files = len(input_files)
    
    if progress_callback:
        progress_callback(0, total_files)
    
    if total_files == 0:
        _log(
            f"No supported files found in {target_directory}. "
            "Expected .xlsx, .xls, or .html inputs.",
            logging.WARNING,
        )
        return
        
    num_batches = math.ceil(total_files / batch_size)
    _log(f"Found {total_files} files. Processing in {num_batches} batches.")
    
    processed_count = 0
    
    for i in range(num_batches):
        if should_cancel and should_cancel():
            _log("Pipeline cancelled by user. Gracefully shutting down.")
            break
            
        batch_files = input_files[i * batch_size : (i + 1) * batch_size]
        _log(f"Processing batch {i + 1}/{num_batches} ({len(batch_files)} files)")
        
        # 1. Extraction & 2. Normalization
        normalized_schemas = []
        for filepath in batch_files:
            if should_cancel and should_cancel():
                break
            extracted = extract_file(str(filepath))
            if extracted:
                normalized_schemas.extend(normalize_data(extracted))
            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_files)
                
        if should_cancel and should_cancel():
            _log("Pipeline cancelled during extraction. Gracefully shutting down.")
            # Commit whatever we extracted in this partial batch before breaking
            
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
            touched_source_files = set()
            touched_models = set()
            for record_type, schema in normalized_schemas:
                model_data = schema.model_dump(exclude_unset=True, exclude_none=True)
                # Remove id so it can be auto-generated
                model_data.pop("id", None)
                source_file = model_data.get("source_file")
                if source_file:
                    touched_source_files.add(source_file)
                
                if record_type == "session":
                    models_to_insert.append(SessionRecord(**model_data))
                    touched_models.add(SessionRecord)
                elif record_type == "cash":
                    models_to_insert.append(CashRecord(**model_data))
                    touched_models.add(CashRecord)
                elif record_type == "stock":
                    models_to_insert.append(StockRecord(**model_data))
                    touched_models.add(StockRecord)
                elif record_type == "member":
                    models_to_insert.append(MemberRecord(**model_data))
                    touched_models.add(MemberRecord)

            # Rerun-safe upsert behavior:
            # replace existing rows for the same source_file in this transaction,
            # then insert freshly normalized rows.
            if touched_source_files and touched_models:
                for model_cls in touched_models:
                    session.execute(
                        delete(model_cls).where(model_cls.source_file.in_(touched_source_files))
                    )
                
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
