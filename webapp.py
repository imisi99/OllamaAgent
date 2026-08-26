import sys

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QKeySequence, QShortcut


class MainWindow(QMainWindow):
    def __init__(self, url: str = ""):
        super().__init__()

        self.setWindowTitle("OllamaAgent")
        self.resize(800, 600)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))

        self.browser.setZoomFactor(0.8)

        self.setCentralWidget(self.browser)

        QShortcut(
            QKeySequence("Ctrl+R"),
            self,
            activated=self.browser.reload,
        )

        QShortcut(
            QKeySequence("Ctrl++"),
            self,
            activated=self.zoom_in,
        )

        QShortcut(
            QKeySequence("Ctrl+-"),
            self,
            activated=self.zoom_out,
        )

        QShortcut(
            QKeySequence("Ctrl+0"),
            self,
            activated=self.reset_zoom,
        )

        QShortcut(
            QKeySequence("Alt+Left"),
            self,
            activated=self.browser.back,
        )

        QShortcut(
            QKeySequence("Alt+Right"),
            self,
            activated=self.browser.forward,
        )

    def zoom_in(self):
        self.browser.setZoomFactor(min(self.browser.zoomFactor() + 0.1, 5.0))

    def zoom_out(self):
        self.browser.setZoomFactor(max(self.browser.zoomFactor() - 0.1, 0.25))

    def reset_zoom(self):
        self.browser.setZoomFactor(1.0)


app = QApplication(sys.argv)

window = MainWindow("http://localhost:8501")

window.show()

sys.exit(app.exec())
