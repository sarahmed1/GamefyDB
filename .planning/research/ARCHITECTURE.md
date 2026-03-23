# Architecture Patterns

**Domain:** Desktop Data Processing & Normalization Application
**Researched:** 2026-03-23

## Recommended Architecture

A Model-View-Controller (MVC) architecture with strictly separated background processing.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| MainWindow (UI) | Handles user inputs, directory selection, displays progress, and initiates jobs. | `PipelineWorker` via Qt Signals/Slots |
| PipelineWorker | Subclasses `QThread` or `QRunnable`. Executes the actual data extraction and normalization. | MainWindow (emits progress), DataProcessor |
| DataProcessor | Uses BS4/lxml and Pandas to open HTML files, normalize tables/data, and validate. | SQLite Database (SQLAlchemy) |
| Database Layer | SQLAlchemy Engine and Session management handling SQLite operations and schema definitions. | DataProcessor |

### Data Flow

1. User selects a directory in the UI and clicks "Start Processing".
2. UI instantiates a `PipelineWorker`, passing the directory path, and connects `progress`, `log`, and `finished` signals to UI slots.
3. The Worker calls the `DataProcessor` in a separate thread.
4. The Processor iterates through `.html` files, parses with BeautifulSoup4 and lxml, and cleans data with Pandas.
5. The Processor commits batches to SQLite using SQLAlchemy and emits progress (e.g., "Processed 10/100 files").
6. UI updates non-blockingly. When the worker emits `finished`, the UI unlocks.

## Patterns to Follow

### Pattern 1: Qt Worker Threads
**What:** Offloading heavy CPU and I/O tasks to background threads.
**When:** Whenever parsing a directory or making database calls that might take more than 50ms.
**Example:**
```python
class WorkerSignals(QObject):
    progress = Signal(int)
    finished = Signal()

class PipelineWorker(QRunnable):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        # Heavy BS4 and SQLite processing here
        self.signals.progress.emit(10)
        self.signals.finished.emit()
```

### Pattern 2: SQLAlchemy Declarative Models
**What:** Defining the schema in Python classes rather than raw SQL strings.
**When:** For maintaining structure as data is normalized for future ML modeling.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Blocking the Event Loop
**What:** Running the BS4 parsing logic directly inside a PySide6 button click handler.
**Why bad:** The UI will instantly freeze, Windows will report the app as "Not Responding," and progress bars won't update.
**Instead:** Use `QThreadPool` or `QThread` and communicate via Signals and Slots.

### Anti-Pattern 2: Global Database Connections
**What:** Opening a single `sqlite3.connect()` globally and passing it around threads.
**Why bad:** SQLite restricts multithreaded writes heavily, and global connections cause thread-safety violations.
**Instead:** Open and close SQLAlchemy Sessions scoped specifically to the background worker thread.

## Scalability Considerations

| Concern | 100 HTML files | 10,000 HTML files |
|---------|----------------|-------------------|
| Memory | Process all files and commit once. | Batch commit to SQLite every 500 files. Drop references to parsed BS4 trees immediately to avoid memory leaks. |
| UI Responsiveness | Quick execution, negligible lockups if single-threaded. | Essential to use QThreads and batch UI progress updates to prevent signal flooding. |

## Sources

- Qt for Python Multi-threading Guidelines
- SQLAlchemy Scoped Session Documentation
