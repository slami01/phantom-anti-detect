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
    # Настройки для WebEngine
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--disable-blink-features=AutomationControlled "
        "--disable-features=VizDisplayCompositor "
        "--disable-gpu-vsync "
        "--disable-site-isolation-trials "
        "--disable-web-security "
        "--no-sandbox "
        "--disable-setuid-sandbox "
        "--allow-running-insecure-content "
        "--ignore-certificate-errors "
        "--disable-features=TranslateUI "
        "--disable-background-networking "
        "--disable-sync "
        "--disable-default-apps "
        "--disable-extensions "
        "--disable-component-update "
        "--disable-domain-reliability "
        "--no-default-browser-check "
        "--no-first-run "
        "--disable-logging "
        "--log-level=3"
    )
    
    # Отключаем GPU для стабильности
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    
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