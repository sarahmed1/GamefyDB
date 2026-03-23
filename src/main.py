import argparse
import sys
import logging
from pathlib import Path

# Ensure src is in the path when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import init_db
from src.pipeline.orchestrator import run_pipeline

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main():
    parser = argparse.ArgumentParser(description="GamefyDB Data Extraction Pipeline")
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Directory containing .html files to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of files to process per batch"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:///local.db",
        help="Database URL for persistence"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger("main")
    
    target_dir = Path(args.target)
    if not target_dir.exists() or not target_dir.is_dir():
        logger.error(f"Target directory does not exist or is not a directory: {args.target}")
        sys.exit(1)
        
    logger.info("Initializing database...")
    init_db(args.db_url)
    
    logger.info(f"Running pipeline on {args.target}...")
    try:
        run_pipeline(target_directory=str(args.target), batch_size=args.batch_size, db_url=args.db_url)
        logger.info("Pipeline execution wrapper finished.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
