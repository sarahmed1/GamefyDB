from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QPlainTextEdit,
    QFileDialog
)
from src.ui.worker import PipelineWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipeline Desktop UI")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 1. Directory selection area
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory selected")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(QLabel("Data Directory:"))
        dir_layout.addWidget(self.dir_label, stretch=1)
        dir_layout.addWidget(self.browse_button)
        main_layout.addLayout(dir_layout)

        # 2. Controls area
        controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_pipeline)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_pipeline)
        controls_layout.addStretch()
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.cancel_button)
        main_layout.addLayout(controls_layout)

        # 3. Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 4. Logs area
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        main_layout.addWidget(self.log_viewer)

        self.worker = None

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Data Directory")
        if directory:
            self.dir_label.setText(directory)

    def start_pipeline(self):
        directory = self.dir_label.text()
        if directory == "No directory selected" or not directory:
            self.log_viewer.appendPlainText("Error: Please select a valid directory before starting.")
            return

        self.start_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        
        self.worker = PipelineWorker(target_directory=directory)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.log_viewer.appendPlainText)
        self.worker.finished.connect(self.pipeline_finished)
        self.worker.error.connect(self.pipeline_error)
        
        self.worker.start()

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def pipeline_finished(self):
        self.start_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.log_viewer.appendPlainText("Pipeline finished.")

    def pipeline_error(self, err_msg):
        self.start_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.log_viewer.appendPlainText(f"Pipeline error: {err_msg}")

    def cancel_pipeline(self):
        if self.worker:
            self.worker.cancel()
            self.log_viewer.appendPlainText("Cancellation requested. Finishing current batch gracefully...")
            self.cancel_button.setEnabled(False)
