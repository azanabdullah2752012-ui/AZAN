import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

def create_hexagon_icon():
    pixmap = QPixmap(22, 22)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(QColor(111, 177, 255))
    painter.drawEllipse(4, 4, 14, 14) 
    painter.end()
    return QIcon(pixmap)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

print("Tray available:", QSystemTrayIcon.isSystemTrayAvailable())

tray_icon = QSystemTrayIcon(create_hexagon_icon(), app)
menu = QMenu()
menu.addAction("Quit").triggered.connect(app.quit)
tray_icon.setContextMenu(menu)
tray_icon.show()

print("Tray shown. Executing event loop...")
sys.exit(app.exec())
