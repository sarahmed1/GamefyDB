import logging
from typing import Callable, Optional
from PySide6.QtCore import QThread, Signal

from src.pipeline.orchestrator import run_pipeline
from src.database.session import DEFAULT_DB_URL

class PipelineWorker(QThread):
    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        target_directory: str,
        batch_size: int = 50,
        db_url: str = DEFAULT_DB_URL,
        parent=None
    ):
        super().__init__(parent)
        self.target_directory = target_directory
        self.batch_size = batch_size
        self.db_url = db_url
        self._is_cancelled = False

    def cancel(self):
        """Thread-safe cancellation flag toggle."""
        self._is_cancelled = True

    def run(self):
        try:
            run_pipeline(
                target_directory=self.target_directory,
                batch_size=self.batch_size,
                db_url=self.db_url,
                progress_callback=lambda current, total: self.progress.emit(current, total),
                log_callback=lambda msg: self.log.emit(msg),
                should_cancel=lambda: self._is_cancelled
            )
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()
