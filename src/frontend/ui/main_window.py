from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QPlainTextEdit,
    QFileDialog, QTabWidget, QTableView, QComboBox, QHeaderView,
    QMessageBox
)
from PySide6.QtSql import QSqlDatabase, QSqlTableModel
from src.frontend.ui.worker import PipelineWorker
from src.backend.database.session import empty_database

class MainWindow(QMainWindow):
    """
    Main application window for the Pipeline Desktop UI.
    Contains two tabs:
    1. Data Pipeline: For selecting a directory and running the extraction/normalization process.
    2. Database Explorer: For viewing the normalized data stored in the local SQLite database.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipeline Desktop UI")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Data Pipeline
        self.pipeline_tab = QWidget()
        pipeline_layout = QVBoxLayout(self.pipeline_tab)
        
        # Tab 2: Database Explorer
        self.db_tab = QWidget()
        db_layout = QVBoxLayout(self.db_tab)

        self.tabs.addTab(self.pipeline_tab, "Data Pipeline")
        self.tabs.addTab(self.db_tab, "Database Explorer")

        # ========================================
        # SETUP TAB 1: DATA PIPELINE
        # ========================================
        # 1. Directory selection area
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory selected")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(QLabel("Data Directory:"))
        dir_layout.addWidget(self.dir_label, stretch=1)
        dir_layout.addWidget(self.browse_button)
        pipeline_layout.addLayout(dir_layout)

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
        pipeline_layout.addLayout(controls_layout)

        # 3. Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        pipeline_layout.addWidget(self.progress_bar)

        # 4. Logs area
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        pipeline_layout.addWidget(self.log_viewer)

        self.worker = None

        # ========================================
        # SETUP TAB 2: DATABASE EXPLORER
        # ========================================
        # Top controls for DB Explorer
        db_controls_layout = QHBoxLayout()
        self.table_selector = QComboBox()
        self.table_selector.addItems([
            "sessions",
            "cash_reports",
            "stock_reports",
            "member_reports"
        ])
        self.table_selector.currentTextChanged.connect(self.load_table_data)
        
        self.refresh_db_button = QPushButton("Refresh Data")
        self.refresh_db_button.clicked.connect(self.load_table_data)
        self.empty_db_button = QPushButton("Empty Database")
        self.empty_db_button.clicked.connect(self.confirm_and_empty_database)

        db_controls_layout.addWidget(QLabel("Select Table:"))
        db_controls_layout.addWidget(self.table_selector)
        db_controls_layout.addStretch()
        db_controls_layout.addWidget(self.empty_db_button)
        db_controls_layout.addWidget(self.refresh_db_button)

        db_layout.addLayout(db_controls_layout)

        # Table View: Configure appearance and behavior for data visualization
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True) # Make rows easier to read
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) # Allow columns to be manually resized
        self.table_view.setSelectionBehavior(QTableView.SelectRows) # Select whole rows instead of single cells
        self.table_view.setEditTriggers(QTableView.NoEditTriggers) # Make view read-only to prevent accidental data modification
        db_layout.addWidget(self.table_view)

        # Initialize Database connection
        self.db = None
        self.sql_model = None
        self.init_database()

    def init_database(self):
        """
        Initializes the SQLite database connection and sets up the QSqlTableModel
        to display data in the Database Explorer tab.
        """
        db_path = "local.db"
        
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(db_path)
        
        if not self.db.open():
            QMessageBox.critical(self, "Database Error", f"Could not open database {db_path}")
            return

        self.sql_model = QSqlTableModel(self, self.db)
        self.table_view.setModel(self.sql_model)
        
        # Load initially selected table
        self.load_table_data()

    def load_table_data(self):
        """
        Loads or refreshes the data in the QTableView based on the currently
        selected table in the dropdown.
        """
        if not self.sql_model:
            return
            
        table_name = self.table_selector.currentText()
        if table_name:
            self.sql_model.setTable(table_name)
            self.sql_model.select()

    def browse_directory(self):
        """Opens a file dialog to select the target directory for data extraction."""
        directory = QFileDialog.getExistingDirectory(self, "Select Data Directory")
        if directory:
            self.dir_label.setText(directory)

    def start_pipeline(self):
        """
        Starts the pipeline extraction process in a background worker thread.
        Disables UI controls while the pipeline is running.
        """
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
        """Callback for when the pipeline completes successfully."""
        self.start_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.log_viewer.appendPlainText("Pipeline finished.")
        # Automatically refresh DB view
        self.load_table_data()

    def pipeline_error(self, err_msg):
        """Callback for when the pipeline encounters an error."""
        self.start_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.log_viewer.appendPlainText(f"Pipeline error: {err_msg}")

    def cancel_pipeline(self):
        """Requests cancellation of the running pipeline worker."""
        if self.worker:
            self.worker.cancel()
            self.log_viewer.appendPlainText("Cancellation requested. Finishing current batch gracefully...")
            self.cancel_button.setEnabled(False)

    def confirm_and_empty_database(self):
        """Prompts for confirmation, then deletes all rows from managed tables."""
        result = QMessageBox.question(
            self,
            "Confirm Empty Database",
            "This will permanently delete all records from all tables. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        try:
            deleted_count = empty_database()
            self.load_table_data()
            self.log_viewer.appendPlainText(
                f"Database emptied successfully. Deleted {deleted_count} rows."
            )
            QMessageBox.information(self, "Database Emptied", "All database records have been deleted.")
        except Exception as exc:
            QMessageBox.critical(self, "Database Error", f"Failed to empty database: {exc}")
