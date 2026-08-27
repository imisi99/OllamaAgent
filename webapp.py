import logging
import time
import subprocess
import sys

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QKeySequence, QShortcut

PROJECT_DIR = "/home/knightmares/Documents/project/OllamaAgent"
MAX_WAIT = 120
CHECK_INTERVAL = 3
STREAMLIT_URL = "http://localhost:8501"


class DockerWorker(QThread):
    status = Signal(dict)
    message = Signal(str)
    progress = Signal(int)
    finished = Signal()
    failed = Signal(str)

    def run(self):
        try:
            self.message.emit("Starting Docker containers...")

            subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=PROJECT_DIR,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

            elapsed = 0

            while elapsed < MAX_WAIT:
                statuses = self.get_statuses()

                self.status.emit(statuses)

                app_status = statuses.get("agent_app", "starting")

                if app_status == "healthy":
                    self.progress.emit(100)
                    self.message.emit("OllamaAgent is ready.")
                    self.finished.emit()
                    return

                if app_status == "unhealthy":
                    self.failed.emit(
                        "The streamlit container reported an unhealthy status."
                    )
                    return

                progress = min(int((elapsed / MAX_WAIT) * 100), 99)

                self.progress.emit(progress)

                self.message.emit(f"Starting services... ({elapsed}s)")

                time.sleep(CHECK_INTERVAL)
                elapsed += CHECK_INTERVAL

            self.failed.emit(f"Timed out after {MAX_WAIT} seconds.")

        except subprocess.CalledProcessError as e:
            self.failed.emit(f"Failed to start Docker: \n{e}")
        except Exception as e:
            self.failed.emit(str(e))

    def get_statuses(self):
        containers = {
            "agent_mongo": "mongo",
            "agent_redis": "redis",
            "agent_qdrant": "qdrant",
            "agent_server": "server",
            "agent_app": "app",
        }

        result = {}

        for container, service in containers.items():
            try:
                output = subprocess.check_output(
                    [
                        "docker",
                        "inspect",
                        "-f",
                        "{{if .State.Health}}",
                        "{{.State.Health.Status}}",
                        "{{else}}",
                        "{{.State.Status}}",
                        "{{end}}",
                        container,
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )

                result[container] = output.strip()

            except subprocess.CalledProcessError:
                result[container] = "starting"

        return result


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OllamaAgent")
        self.setFixedSize(500, 420)

        layout = QVBoxLayout(self)

        title = QLabel("OllamaAgent")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            """)

        self.message = QLabel("Starting services...")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        self.mongo = QLabel("○ MongoDB")
        self.redis = QLabel("○ Redis")
        self.qdrant = QLabel("○ Qdrant")
        self.server = QLabel("○ Server")
        self.app = QLabel("○ Streamlit")

        layout.addWidget(title)
        layout.addSpacing(15)

        layout.addWidget(self.message)
        layout.addSpacing(10)

        layout.addWidget(self.mongo)
        layout.addWidget(self.redis)
        layout.addWidget(self.qdrant)
        layout.addWidget(self.server)
        layout.addWidget(self.app)

        layout.addSpacing(15)
        layout.addWidget(self.progress)

    def update_status(self, statuses: dict):
        self.update_service(self.mongo, statuses.get("agent_mongo", "starting"))
        self.update_service(self.redis, statuses.get("agent_redis", "starting"))
        self.update_service(self.qdrant, statuses.get("agent_qdrant", "starting"))
        self.update_service(self.server, statuses.get("agent_server", "starting"))
        self.update_service(self.app, statuses.get("agent_app", "starting"))

    @staticmethod
    def update_service(label: QLabel, status: str):
        names = {
            "healthy": "✓",
            "unhealthy": "✗",
            "starting": "○",
            "running": "○",
        }

        symbol = names.get(status, "○")

        label.setText(f"{symbol} {label.text().split(" ", 1)[1]} -- {status}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OllamaAgent")
        self.resize(1200, 800)

        self.browser = QWebEngineView()

        self.browser.setZoomFactor(0.8)

        self.setCentralWidget(self.browser)

        self.setup_shortcuts()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.browser.reload)

        QShortcut(QKeySequence("Ctrl++"), self, activated=self.zoom_in)

        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.zoom_out)

        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.reset_zoom)

        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)

    def zoom_in(self):
        self.browser.setZoomFactor(min(self.browser.zoomFactor() + 0.1, 5.0))

    def zoom_out(self):
        self.browser.setZoomFactor(max(self.browser.zoomFactor() - 0.1, 0.25))

    def reset_zoom(self):
        self.browser.setZoomFactor(1.0)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):
        answer = QMessageBox.question(
            self,
            "Stop OllamaAgent?",
            "Do you want to stop the Docker containers?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if answer == QMessageBox.Yes:
            try:
                subprocess.run(
                    ["docker", "compose", "down"], cwd=PROJECT_DIR, check=True
                )

            except subprocess.CalledProcessError:
                QMessageBox.warning(self, "Docker", "Failed to stop Docker containers.")
            except Exception as e:
                logging.error(f"Failed to stop Docker containers -> {e}")
                QMessageBox.warning(self, "Error", "Failed to stop Docker containers.")

        event.accept()


def startapp():

    app = QApplication(sys.argv)

    loading = LoadingScreen()
    loading.show()

    worker = DockerWorker()

    worker.status.connect(loading.update_status)

    worker.progress.connect(loading.progress.setValue)

    worker.message.connect(loading.message.setText)

    main_window = MainWindow()

    def ready():
        loading.close()

        main_window.browser.setUrl(QUrl(STREAMLIT_URL))

        main_window.show()

    def failed(message):
        loading.close()

        QMessageBox.critical(None, "OllamaAgent", message)

        sys.exit(1)

    worker.finished.connect(ready)
    worker.failed.connect(failed)

    worker.start()

    sys.exit(app.exec())


startapp()
