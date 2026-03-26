import argparse
import sys
from pathlib import Path

# Ensure src is in the path when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.app.cli import run_cli
from src.frontend.app.gui import run_gui

def main():
    parser = argparse.ArgumentParser(description="GamefyDB Data Extraction Pipeline")
    parser.add_argument(
        "--target",
        type=str,
        required=False,
        help="Directory containing .xlsx, .xls, or .html files to process (run CLI mode if provided)"
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

    if not args.target:
        sys.exit(run_gui())

    exit_code = run_cli(target=args.target, batch_size=args.batch_size, db_url=args.db_url)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
