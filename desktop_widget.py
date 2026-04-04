import os
import sys
import json
import threading
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QSizeGrip
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPalette, QFont

API_URL = "http://localhost:8000/chat/stream"
SESSION_ID = "desktop_" + str(os.getpid())

class WorkerSignals(QObject):
    stream_chunk = pyqtSignal(str)
    stream_finished = pyqtSignal()
    stream_error = pyqtSignal(str)

class ChatWorker(threading.Thread):
    def __init__(self, prompt, model="llama3"):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.signals = WorkerSignals()
        self.daemon = True

    def run(self):
        try:
            payload = {
                "prompt": self.prompt,
                "session_id": SESSION_ID,
                "model": self.model,
                "temperature": 0.5
            }
            with requests.post(API_URL, json=payload, stream=True, timeout=30) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "token" in data:
                                    self.signals.stream_chunk.emit(data["token"])
                            except json.JSONDecodeError:
                                pass
            self.signals.stream_finished.emit()
        except Exception as e:
            self.signals.stream_error.emit(str(e))

class JarvisWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self._drag_pos = None

    def initUI(self):
        # Frameless, Always on Top, and Tool (hides from taskbar/dock nicely)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(320, 480)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container to hold background style
        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: rgba(20, 20, 35, 230);
                border-radius: 15px;
                border: 1px solid rgba(100, 100, 255, 0.3);
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 10, 15, 15)
        
        # Header (Draggable)
        header_layout = QHBoxLayout()
        self.title_label = QLabel("⬡ JARVIS")
        self.title_label.setStyleSheet("color: #6fb1ff; font-weight: bold; font-family: 'SF Pro Display', sans-serif;")
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #888; border: none; font-weight: bold; }
            QPushButton:hover { color: #ff5555; }
        """)
        self.close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # Chat History Log
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 10, 20, 150);
                color: #e0e0e0;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 10px;
                font-family: 'SF Pro Text', sans-serif;
                font-size: 13px;
            }
        """)
        
        # Status Label
        self.status_label = QLabel(" ")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        
        # Input Box
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Ask JARVIS...")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 45, 200);
                color: white;
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 255, 0.5);
                padding: 8px 12px;
                font-family: 'SF Pro Text', sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #6fb1ff; }
        """)
        self.input_box.returnPressed.connect(self.send_message)
        
        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.chat_log)
        container_layout.addWidget(self.status_label)
        container_layout.addWidget(self.input_box)
        
        self.main_layout.addWidget(self.container)
        
        # Make the window draggable via mouse events
        self.container.mousePressEvent = self.mousePressEvent
        self.container.mouseMoveEvent = self.mouseMoveEvent
        
        self.append_html("<div style='color:#ccc'>JARVIS Online.</div>")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return
        
        self.input_box.clear()
        self.append_html(f"<div style='color:#fff; margin-top:8px;'><b>You:</b> {text}</div>")
        
        self.status_label.setText("Thinking...")
        self.input_box.setEnabled(False)
        
        # Add Assistant Header
        self.current_response = ""
        self.chat_log.append("<b>JARVIS:</b> ")
        
        # Start Worker
        self.worker = ChatWorker(text)
        self.worker.signals.stream_chunk.connect(self.handle_chunk)
        self.worker.signals.stream_finished.connect(self.handle_finished)
        self.worker.signals.stream_error.connect(self.handle_error)
        self.worker.start()

    def handle_chunk(self, chunk):
        self.current_response += chunk
        # Re-render the last block to show streaming
        # A simple hack for QTextEdit streaming is to insert plain text at cursor
        cursor = self.chat_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)

    def handle_finished(self):
        self.status_label.setText(" ")
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.append_html("<hr style='border:0; border-top:1px solid #333;' />")

    def handle_error(self, err_msg):
        self.status_label.setText("Error occurred.")
        self.append_html(f"<div style='color:#ff5555'><i>Error: {err_msg}</i></div>")
        self.input_box.setEnabled(True)

    def append_html(self, html):
        self.chat_log.append(html)


def main():
    app = QApplication(sys.argv)
    # macOS tweak: Don't show in dock
    app.setQuitOnLastWindowClosed(False)
    widget = JarvisWidget()
    
    # Move to top right corner of primary screen
    screen = app.primaryScreen().geometry()
    x = screen.width() - widget.width() - 20
    y = 40
    widget.move(x, y)
    
    widget.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
