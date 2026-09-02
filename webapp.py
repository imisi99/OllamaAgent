import json
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

            process = subprocess.Popen(
                ["docker", "compose", "up", "-d"],
                cwd=PROJECT_DIR,
                text=True,
                stdout=subprocess.PIPE,
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

                if process.poll() is not None and process.returncode != 0:
                    output = process.stdout.read() if process.stdout else ""
                    self.failed.emit(f"Docker failed to start:\n{output}")
                    return

                healthy_count = sum(1 for s in statuses.values() if s == "healthy")
                progress = min(int((healthy_count / len(statuses)) * 100), 99)

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

        result = {name: "starting" for name in containers}

        try:
            output = subprocess.check_output(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=PROJECT_DIR,
                text=True,
                timeout=10,
                stderr=subprocess.DEVNULL,
            )

            for line in output.strip().splitlines():
                info = json.loads(line)
                name = info.get("Name")
                if name in result:
                    health = info.get("Health", "")
                    result[name] = (
                        health.lower() if health else info.get("State", "starting")
                    )

        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ):
            pass

        return result


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OllamaAgent")
        self.setFixedSize(480, 440)
        self.setStyleSheet("""
            QWidget {
                background-color: #12141c;
                color: #e4e6eb;
                font-family: -apple-system, "Segoe UI", sans-serif;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #1f2230;
                height: 10px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E3192, stop:1 #1BFFFF
                );
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(4)

        title = QLabel("OllamaAgent")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title)

        self.message = QLabel("Starting services...")
        self.message.setStyleSheet(
            "color: #8b8fa3; font-size: 13px; margin-top: 4px; margin-bottom: 20px;"
        )
        layout.addWidget(self.message)

        self.mongo = QLabel("○ MongoDB")
        self.redis = QLabel("○ Redis")
        self.qdrant = QLabel("○ Qdrant")
        self.server = QLabel("○ Server")
        self.app = QLabel("○ Streamlit")

        for label in (self.mongo, self.redis, self.qdrant, self.server, self.app):
            label.setStyleSheet("font-size: 13px; padding: 4px 0px;")
            layout.addWidget(label)

        self.service_labels = {
            "agent_mongo": (self.mongo, "MongoDB"),
            "agent_redis": (self.redis, "Redis"),
            "agent_qdrant": (self.qdrant, "Qdrant"),
            "agent_server": (self.server, "Server"),
            "agent_app": (self.app, "Streamlit"),
        }

        for label, name in self.service_labels.values():
            label.setText(f"○ {name}")

        layout.addSpacing(16)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

    def update_status(self, status: dict):
        for container, (label, name) in self.service_labels.items():
            self.update_service(label, name, status.get(container, "starting"))

    @staticmethod
    def update_service(label: QLabel, name: str, status: str):
        styles = {
            "healthy": ("✓", "#4ade80"),
            "unhealthy": ("✗", "#f87171"),
            "starting": ("○", "#8b8fa3"),
            "running": ("○", "f5c451"),
        }

        symbol, color = styles.get(status, ("○", "#8b8fa3"))
        label.setStyleSheet(f"font-size: 14px; padding: 4px 0px; color: {color};")
        label.setText(f"{symbol}  {name}")


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
                subprocess.Popen(["docker", "compose", "down"], cwd=PROJECT_DIR)

            except subprocess.CalledProcessError:
                QMessageBox.warning(self, "Docker", "Failed to stop Docker containers.")
            except Exception as e:
                logging.error(f"Failed to stop Docker containers -> {e}")
                QMessageBox.warning(self, "Error", "Failed to stop Docker containers.")

        event.accept()


def startapp():

    app = QApplication(sys.argv)
    app.setDesktopFileName("ollamaagent")

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
