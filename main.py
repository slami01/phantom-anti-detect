#!/usr/bin/env python3
"""
Phantom Anti-Detect Browser Framework
Главная точка входа
"""
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.main_window import MainWindow


def main():
    # Запуск приложения
    app = QApplication(sys.argv)
    app.setApplicationName("Phantom Anti-Detect Browser")
    app.setOrganizationName("Phantom")
    
    # Тёмная тема
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
