import logging
import sys
import argparse
from pathlib import Path

from src.backend.database.session import init_db
from src.backend.pipeline.orchestrator import run_pipeline


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_cli(target: str, batch_size: int = 50, db_url: str = "sqlite:///local.db") -> int:
    """Run the backend pipeline against a target directory."""
    setup_logging()
    logger = logging.getLogger("backend.cli")

    target_dir = Path(target)
    if not target_dir.exists() or not target_dir.is_dir():
        logger.error(f"Target directory does not exist or is not a directory: {target}")
        return 1

    logger.info("Initializing database...")
    init_db(db_url)

    logger.info(f"Running pipeline on {target}...")
    try:
        run_pipeline(target_directory=target, batch_size=batch_size, db_url=db_url)
        logger.info("Pipeline execution wrapper finished.")
        return 0
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}", exc_info=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="GamefyDB CLI Pipeline")
    parser.add_argument("--target", type=str, required=True, help="Directory containing .html files")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of files to process per batch")
    parser.add_argument("--db-url", type=str, default="sqlite:///local.db", help="Database URL")
    args = parser.parse_args()
    return run_cli(target=args.target, batch_size=args.batch_size, db_url=args.db_url)


if __name__ == "__main__":
    raise SystemExit(main())
