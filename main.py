import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui     import QFont
from ui import Dashboard


def load_qss(app, path):
    try:
        with open(path) as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass


app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", 10))
load_qss(app, "style.qss")

window = Dashboard()
window.show()
print(1)
sys.exit(app.exec_())
