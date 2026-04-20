#! /usr/bin/env python
import sys
from pathlib import Path

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from ui import Dashboard


BASE_DIR = Path(__file__).resolve().parent


def load_qss(app, path):
    try:
        app.setStyleSheet(Path(path).read_text())
    except FileNotFoundError:
        return


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    load_qss(app, BASE_DIR / "style.qss")

    window = Dashboard()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
