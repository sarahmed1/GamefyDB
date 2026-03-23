import sys

from PySide6.QtWidgets import QApplication

from src.frontend.ui.main_window import MainWindow


def run_gui() -> int:
    """Launch the desktop GUI and block until the app exits."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_gui())
