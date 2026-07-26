#!/usr/bin/env python3
"""NotepadOMM — editor de texto/código para Linux (estilo Notepad++)."""

import os
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from main_window import MainWindow


def resource_path(rel):
    """Resolve caminho de recurso tanto no código-fonte quanto no binário."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NotepadOMM")
    app.setApplicationDisplayName("NotepadOMM")
    app.setDesktopFileName("notepadomm")

    icon_path = resource_path(os.path.join("assets", "notepadomm.svg"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    # Abre arquivos passados na linha de comando: notepadomm arquivo1 arquivo2
    for arg in sys.argv[1:]:
        window.open_path(arg)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
