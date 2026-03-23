from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QPlainTextEdit,
    QFileDialog
)

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
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
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

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Data Directory")
        if directory:
            self.dir_label.setText(directory)
