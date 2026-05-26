"""
Главное окно приложения
"""
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit,
    QSplitter, QFrame, QMenu, QMessageBox,
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QScrollArea, QApplication,
    QToolBar, QStatusBar, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QFont, QIcon

from app.browser_tab import BrowserTab
from app.profile_manager import ProfileManager, BrowserProfile
from app.proxy_manager import ProxyManager
from app.fingerprint_engine import FingerprintEngine
from app.cookie_jar import CookieJar
from app.human_emulator import HumanEmulator
from app.security_audit import SecurityAudit
from app.lab_server import LAB_PROFILES, LabServer


class MainWindow(QMainWindow):
    """
    Phantom Anti-Detect Browser Framework
    Главное окно приложения
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Phantom Anti-Detect Browser v3.0")
        self.setGeometry(100, 50, 1600, 950)
        
        # Устанавливаем тёмную тему
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 8px 20px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #0078d4;
            }
            QTreeWidget {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                color: #cccccc;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #4d4d4d;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        
        # Менеджеры
        self.profile_manager = ProfileManager("profiles")
        self.proxy_manager = ProxyManager("proxies/pool.json")
        self.security_audit = SecurityAudit()
        self.lab_server = None
        
        # Текущий профиль
        self.current_profile: Optional[BrowserProfile] = None
        self.current_fingerprint = None
        
        # Вкладки браузеров
        self.browser_tabs: Dict[str, BrowserTab] = {}
        self.last_audit_report = None
        
        self._init_ui()
        self._create_menu()
        self._create_toolbar()
        self._create_statusbar()
        
        # Загружаем профили в дерево
        self._refresh_profile_tree()
    
    def _init_ui(self):
        """Инициализация основного интерфейса"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === ЛЕВАЯ ПАНЕЛЬ ===
        left_panel = QFrame()
        left_panel.setMaximumWidth(350)
        left_panel.setMinimumWidth(280)
        left_panel.setStyleSheet("background-color: #252526; border-right: 1px solid #3d3d3d;")
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        # Заголовок
        title = QLabel("👤 ПРОФИЛИ")
        title.setStyleSheet("color: #0078d4; font-size: 14px; font-weight: bold; padding: 5px;")
        left_layout.addWidget(title)
        
        # Дерево профилей
        self.profile_tree = QTreeWidget()
        self.profile_tree.setHeaderLabels(["Профиль", "Статус"])
        self.profile_tree.setColumnWidth(0, 180)
        self.profile_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.profile_tree.customContextMenuRequested.connect(self._profile_context_menu)
        self.profile_tree.itemDoubleClicked.connect(self._open_profile)
        left_layout.addWidget(self.profile_tree)
        
        # Кнопки управления профилями
        btn_layout = QHBoxLayout()
        
        self.btn_new_profile = QPushButton("+ Новый")
        self.btn_new_profile.clicked.connect(self._create_profile_dialog)
        
        self.btn_delete_profile = QPushButton("🗑 Удалить")
        self.btn_delete_profile.clicked.connect(self._delete_profile)
        
        btn_layout.addWidget(self.btn_new_profile)
        btn_layout.addWidget(self.btn_delete_profile)
        left_layout.addLayout(btn_layout)
        
        # === ИНФОРМАЦИЯ О ПРОФИЛЕ ===
        info_group = QGroupBox("Информация о профиле")
        info_group.setStyleSheet("QGroupBox { color: #0078d4; border: 1px solid #3d3d3d; border-radius: 4px; margin-top: 10px; padding-top: 15px; }")
        
        info_layout = QVBoxLayout(info_group)
        
        self.info_label = QLabel("Выберите профиль...")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        left_layout.addWidget(info_group)
        
        # === ПРОКСИ ===
        proxy_group = QGroupBox("Прокси")
        proxy_group.setStyleSheet("QGroupBox { color: #0078d4; border: 1px solid #3d3d3d; border-radius: 4px; margin-top: 10px; padding-top: 15px; }")
        
        proxy_layout = QVBoxLayout(proxy_group)
        
        self.proxy_status = QLabel("Прокси: не настроен")
        proxy_layout.addWidget(self.proxy_status)
        
        self.btn_set_proxy = QPushButton("Настроить прокси")
        self.btn_set_proxy.clicked.connect(self._set_proxy_dialog)
        proxy_layout.addWidget(self.btn_set_proxy)
        
        left_layout.addWidget(proxy_group)
        
        # === ОСНОВНАЯ ОБЛАСТЬ (ВКЛАДКИ БРАУЗЕРОВ) ===
        self.browser_tabs_widget = QTabWidget()
        self.browser_tabs_widget.setTabsClosable(True)
        self.browser_tabs_widget.tabCloseRequested.connect(self._close_browser_tab)
        self.browser_tabs_widget.currentChanged.connect(self._on_tab_changed)
        
        # Приветственная вкладка
        welcome_tab = self._create_welcome_tab()
        self.browser_tabs_widget.addTab(welcome_tab, "🏠 Главная")
        
        # === СБОРКА ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.browser_tabs_widget)
        splitter.setSizes([300, 1300])
        
        main_layout.addWidget(splitter)
    
    def _create_welcome_tab(self) -> QWidget:
        """Приветственная вкладка"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome = QLabel("""
        <h1 style='color: #0078d4;'>🛡 Phantom Anti-Detect Browser</h1>
        <p style='color: #cccccc; font-size: 14px;'>Framework для тестирования защитных механизмов веб-приложений</p>
        <br>
        <p style='color: #888888;'>
        <b>Возможности:</b><br>
        • Изолированные профили браузеров (Multilogin/GoLogin/AdsPower)<br>
        • Подмена цифровых отпечатков (Canvas, WebGL, Audio, Fonts)<br>
        • Эмуляция поведения человека (мышь, скролл, печать)<br>
        • Управление куками и сессиями<br>
        • Ротация прокси с проверкой здоровья<br>
        • Обнаружение CAPTCHA для ручного прохождения<br>
        • Мультиаккаунтинг<br>
        • Встроенные окна браузеров<br>
        </p>
        <br>
        <p style='color: #00cc66;'>Выберите профиль слева или создайте новый для начала работы.</p>
        """)
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)
        
        return tab
    
    def _create_menu(self):
        """Главное меню"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #cccccc;
                border-bottom: 1px solid #3d3d3d;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
        """)
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        new_profile_action = QAction("Новый профиль", self)
        new_profile_action.triggered.connect(self._create_profile_dialog)
        file_menu.addAction(new_profile_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Импорт профилей (Multilogin)", self)
        import_action.triggered.connect(self._import_profiles)
        file_menu.addAction(import_action)
        
        export_action = QAction("Экспорт профиля", self)
        export_action.triggered.connect(self._export_profile)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Профили
        profile_menu = menubar.addMenu("Профили")
        
        create_action = QAction("Создать профиль", self)
        create_action.triggered.connect(self._create_profile_dialog)
        profile_menu.addAction(create_action)
        
        bulk_action = QAction("Массовое создание...", self)
        bulk_action.triggered.connect(self._bulk_create_dialog)
        profile_menu.addAction(bulk_action)
        
        profile_menu.addSeparator()
        
        fingerprint_action = QAction("Редактировать отпечаток", self)
        fingerprint_action.triggered.connect(self._edit_fingerprint)
        profile_menu.addAction(fingerprint_action)
        
        cookie_action = QAction("Управление куками", self)
        cookie_action.triggered.connect(self._manage_cookies)
        profile_menu.addAction(cookie_action)
        
        # Прокси
        proxy_menu = menubar.addMenu("Прокси")
        
        add_proxy_action = QAction("Добавить прокси", self)
        add_proxy_action.triggered.connect(self._add_proxy_dialog)
        proxy_menu.addAction(add_proxy_action)
        
        check_proxy_action = QAction("Проверить все прокси", self)
        check_proxy_action.triggered.connect(self._check_all_proxies)
        proxy_menu.addAction(check_proxy_action)
        
        # Инструменты
        tools_menu = menubar.addMenu("Инструменты")

        lab_action = QAction("Запустить учебный стенд", self)
        lab_action.triggered.connect(self._open_lab_stand)
        tools_menu.addAction(lab_action)

        stop_lab_action = QAction("Остановить учебный стенд", self)
        stop_lab_action.triggered.connect(self._stop_lab_stand)
        tools_menu.addAction(stop_lab_action)

        tools_menu.addSeparator()

        audit_action = QAction("Аудит текущей страницы", self)
        audit_action.triggered.connect(self._run_security_audit)
        tools_menu.addAction(audit_action)

        behavior_action = QAction("Включить запись поведения", self)
        behavior_action.triggered.connect(self._install_behavior_recorder)
        tools_menu.addAction(behavior_action)

        export_audit_action = QAction("Экспорт JSON-аудита", self)
        export_audit_action.triggered.connect(self._export_security_audit)
        tools_menu.addAction(export_audit_action)

        tools_menu.addSeparator()
        
        stealth_action = QAction("Проверить стелс-режим", self)
        stealth_action.triggered.connect(self._check_stealth)
        tools_menu.addAction(stealth_action)
        
        captcha_action = QAction("Тест CAPTCHA", self)
        captcha_action.triggered.connect(self._test_captcha)
        tools_menu.addAction(captcha_action)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Панель инструментов"""
        toolbar = QToolBar()
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
                spacing: 5px;
                padding: 3px;
            }
        """)
        self.addToolBar(toolbar)
        
        # Кнопки быстрого доступа
        new_btn = QPushButton("➕ Новый профиль")
        new_btn.clicked.connect(self._create_profile_dialog)
        toolbar.addWidget(new_btn)
        
        toolbar.addSeparator()
        
        open_btn = QPushButton("📂 Открыть профиль")
        open_btn.clicked.connect(lambda: self._open_profile_from_tree())
        toolbar.addWidget(open_btn)
        
        toolbar.addSeparator()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL для быстрого перехода...")
        self.url_input.setMaximumWidth(400)
        self.url_input.returnPressed.connect(self._quick_navigate)
        toolbar.addWidget(self.url_input)
        
        go_btn = QPushButton("→ Перейти")
        go_btn.clicked.connect(self._quick_navigate)
        toolbar.addWidget(go_btn)
    
    def _create_statusbar(self):
        """Строка состояния"""
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #0078d4;
                color: white;
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Готов к работе | Профилей: 0 | Прокси: 0")
    
    def _refresh_profile_tree(self):
        """Обновление дерева профилей"""
        self.profile_tree.clear()
        
        profiles = self.profile_manager.get_all_profiles()
        
        # Группируем по группам
        groups = {}
        for p in profiles:
            if p.group not in groups:
                groups[p.group] = []
            groups[p.group].append(p)
        
        for group_name, group_profiles in groups.items():
            group_item = QTreeWidgetItem(self.profile_tree)
            group_item.setText(0, f"📁 {group_name}")
            group_item.setText(1, f"({len(group_profiles)})")
            group_item.setExpanded(True)
            
            for profile in group_profiles:
                item = QTreeWidgetItem(group_item)
                item.setText(0, f"👤 {profile.name}")
                item.setText(1, "✓" if profile.is_active else "✗")
                item.setData(0, Qt.ItemDataRole.UserRole, profile.id)
        
        self.statusbar.showMessage(
            f"Готов | Профилей: {len(profiles)} | Прокси: {len(self.proxy_manager.proxies)}"
        )
    
    def _create_profile_dialog(self):
        """Диалог создания профиля"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Создание профиля")
        dialog.setFixedSize(450, 400)
        dialog.setStyleSheet("background-color: #2d2d2d; color: white;")
        
        layout = QFormLayout(dialog)
        
        # Имя
        name_input = QLineEdit()
        name_input.setPlaceholderText("Введите имя профиля")
        name_input.setStyleSheet("background: #1e1e1e; color: white; padding: 5px; border: 1px solid #3d3d3d;")
        layout.addRow("Имя профиля:", name_input)
        
        # Группа
        group_input = QComboBox()
        group_input.addItems(["Default", "Work", "Personal", "Bots", "Testing"])
        group_input.setStyleSheet("background: #1e1e1e; color: white;")
        layout.addRow("Группа:", group_input)
        
        # Тип браузера
        browser_input = QComboBox()
        browser_input.addItems(["chromium", "firefox", "webkit"])
        browser_input.setStyleSheet("background: #1e1e1e; color: white;")
        layout.addRow("Браузер:", browser_input)
        
        # Шаблон отпечатка
        fingerprint_input = QComboBox()
        fingerprint_input.addItems([
            "random", "windows_desktop", "macbook_pro", "iphone_15"
        ])
        fingerprint_input.setStyleSheet("background: #1e1e1e; color: white;")
        layout.addRow("Отпечаток:", fingerprint_input)
        
        # Прокси
        proxy_group = QGroupBox("Прокси (опционально)")
        proxy_group.setStyleSheet("QGroupBox { color: #0078d4; border: 1px solid #3d3d3d; margin-top: 10px; }")
        proxy_layout = QFormLayout(proxy_group)
        
        proxy_host = QLineEdit()
        proxy_host.setPlaceholderText("host")
        proxy_host.setStyleSheet("background: #1e1e1e; color: white; padding: 3px;")
        proxy_layout.addRow("Хост:", proxy_host)
        
        proxy_port = QSpinBox()
        proxy_port.setRange(1, 65535)
        proxy_port.setValue(8080)
        proxy_port.setStyleSheet("background: #1e1e1e; color: white;")
        proxy_layout.addRow("Порт:", proxy_port)
        
        proxy_user = QLineEdit()
        proxy_user.setPlaceholderText("login")
        proxy_user.setStyleSheet("background: #1e1e1e; color: white; padding: 3px;")
        proxy_layout.addRow("Логин:", proxy_user)
        
        proxy_pass = QLineEdit()
        proxy_pass.setPlaceholderText("password")
        proxy_pass.setEchoMode(QLineEdit.EchoMode.Password)
        proxy_pass.setStyleSheet("background: #1e1e1e; color: white; padding: 3px;")
        proxy_layout.addRow("Пароль:", proxy_pass)
        
        layout.addRow(proxy_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Создать")
        create_btn.setStyleSheet("background: #0078d4; color: white; padding: 8px 20px;")
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("background: #3d3d3d; color: white; padding: 8px 20px;")
        
        create_btn.clicked.connect(lambda: self._do_create_profile(
            name_input.text(),
            group_input.currentText(),
            browser_input.currentText(),
            fingerprint_input.currentText(),
            {
                'host': proxy_host.text(),
                'port': proxy_port.value(),
                'username': proxy_user.text(),
                'password': proxy_pass.text()
            } if proxy_host.text() else None,
            dialog
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.exec()
    
    def _do_create_profile(self, name, group, browser, fingerprint, proxy, dialog):
        """Создание профиля"""
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя профиля")
            return
        
        profile = self.profile_manager.create_profile(
            name=name,
            group=group,
            browser_type=browser,
            fingerprint_template=fingerprint,
            proxy=proxy
        )
        
        self._refresh_profile_tree()
        dialog.accept()
        
        self.statusbar.showMessage(f"Профиль '{name}' создан | ID: {profile.id}")
    
    def _open_profile(self, item, column):
        """Открытие профиля (двойной клик)"""
        profile_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not profile_id:
            return
        
        self._load_profile(profile_id)
    
    def _open_profile_from_tree(self):
        """Открытие выбранного профиля"""
        selected = self.profile_tree.selectedItems()
        if not selected:
            return
        
        profile_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if profile_id:
            self._load_profile(profile_id)
    
    def _load_profile(self, profile_id: str):
        """Загрузка профиля и открытие вкладки браузера"""
        profile = self.profile_manager.get_profile(profile_id)
        if not profile:
            QMessageBox.warning(self, "Ошибка", f"Профиль {profile_id} не найден")
            return
        
        self.current_profile = profile
        
        # Загружаем fingerprint
        engine = FingerprintEngine(f"profiles/{profile_id}")
        fp = engine.load()
        if not fp:
            fp = engine.generate_random()
        
        self.current_fingerprint = fp
        
        # JS-подмена fingerprint отключена по умолчанию: она ломает Cloudflare и
        # современные приложения, если параметры не совпадают с реальным WebEngine.
        stealth_script = ""
        
        # Создаём вкладку браузера
        tab_name = profile.name
        if tab_name in self.browser_tabs:
            for i in range(self.browser_tabs_widget.count()):
                if self.browser_tabs_widget.tabText(i) == f"🌐 {tab_name}":
                    self.browser_tabs_widget.setCurrentIndex(i)
                    return
        
        try:
            browser_tab = BrowserTab(
                profile_dir=f"profiles/{profile_id}",
                fingerprint_script=stealth_script
            )
            
            # Подключаем обнаружение капчи
            browser_tab.webview.loadFinished.connect(
                lambda ok: self._on_page_loaded(ok, browser_tab)
            )
            
            self.browser_tabs[tab_name] = browser_tab
            
            index = self.browser_tabs_widget.addTab(browser_tab, f"🌐 {tab_name}")
            self.browser_tabs_widget.setCurrentIndex(index)
            
            # Обновляем информацию
            self.info_label.setText(f"""
            <b>Имя:</b> {profile.name}<br>
            <b>ID:</b> {profile.id}<br>
            <b>Группа:</b> {profile.group}<br>
            <b>Браузер:</b> {profile.browser_type}<br>
            <b>Отпечаток:</b> {profile.fingerprint_template}<br>
            <b>User-Agent:</b> {fp.user_agent[:80] if fp.user_agent else 'N/A'}...<br>
            <b>WebGL:</b> {fp.webgl_renderer}<br>
            <b>Разрешение:</b> {fp.screen_width}x{fp.screen_height}<br>
            <b>Часовой пояс:</b> {fp.timezone}<br>
            <b>Язык:</b> {fp.language}<br>
            <b>Прокси:</b> {'Настроен' if profile.proxy_host else 'Нет'}<br>
            """)
            
            self.statusbar.showMessage(f"Профиль '{profile.name}' загружен")
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать вкладку браузера:\n{str(e)}")
    
    def _on_page_loaded(self, ok, browser_tab):
        """Detect CAPTCHA widgets after a page load."""
        if not ok:
            return
        
        # Проверяем наличие капчи
        browser_tab.page.runJavaScript("""
            (function() {
                if (document.querySelector('iframe[src*="recaptcha"]') ||
                    document.querySelector('iframe[src*="hcaptcha"]') ||
                    document.querySelector('.g-recaptcha') ||
                    document.querySelector('#turnstile-wrapper')) {
                    return true;
                }
                return false;
            })()
        """, lambda detected: self._handle_captcha_detected(detected, browser_tab))
    
    def _handle_captcha_detected(self, detected, browser_tab):
        """Обработка обнаруженной капчи"""
        if detected:
            self.statusbar.showMessage("⚠️ Обнаружена CAPTCHA. Пройдите проверку вручную во вкладке.")
        else:
            self.statusbar.showMessage("✓ Капча не обнаружена")
    
    def _close_browser_tab(self, index):
        """Закрытие вкладки браузера"""
        tab_text = self.browser_tabs_widget.tabText(index)
        tab_name = tab_text.replace("🌐 ", "")
        
        if tab_name in self.browser_tabs:
            del self.browser_tabs[tab_name]
        
        self.browser_tabs_widget.removeTab(index)
    
    def _on_tab_changed(self, index):
        """Смена активной вкладки"""
        if index < 0:
            return
        
        tab_text = self.browser_tabs_widget.tabText(index)
        # Обновляем URL в тулбаре
        tab = self.browser_tabs_widget.widget(index)
        if hasattr(tab, 'url_bar'):
            self.url_input.setText(tab.url_bar.text())
    
    def _quick_navigate(self):
        """Быстрый переход по URL"""
        url = self.url_input.text().strip()
        if not url:
            return
        
        current_index = self.browser_tabs_widget.currentIndex()
        current_tab = self.browser_tabs_widget.widget(current_index)
        
        if not hasattr(current_tab, 'navigate'):
            profile = self._get_navigation_profile()
            if not profile:
                QMessageBox.warning(self, "Ошибка", "Сначала создайте профиль браузера")
                return

            self._load_profile(profile.id)
            current_tab = self.browser_tabs_widget.currentWidget()

        if hasattr(current_tab, 'navigate'):
            current_tab.navigate(url)
    
    def _get_navigation_profile(self):
        """Return selected profile or the first available profile for quick navigation."""
        selected = self.profile_tree.selectedItems()
        if selected:
            profile_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
            if profile_id:
                profile = self.profile_manager.get_profile(profile_id)
                if profile:
                    return profile

        profiles = self.profile_manager.get_all_profiles()
        return profiles[0] if profiles else None
    
    def _profile_context_menu(self, position):
        """Контекстное меню профиля"""
        item = self.profile_tree.itemAt(position)
        if not item:
            return
        
        profile_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not profile_id:
            return
        
        menu = QMenu()
        
        open_action = menu.addAction("Открыть")
        duplicate_action = menu.addAction("Дублировать")
        export_action = menu.addAction("Экспорт")
        menu.addSeparator()
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec(self.profile_tree.mapToGlobal(position))
        
        if action == open_action:
            self._load_profile(profile_id)
        elif action == duplicate_action:
            self.profile_manager.duplicate_profile(
                profile_id,
                f"{self.profile_manager.get_profile(profile_id).name} (копия)"
            )
            self._refresh_profile_tree()
        elif action == export_action:
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт профиля", "", "JSON (*.json)"
            )
            if path:
                self.profile_manager.export_to_json(profile_id, path)
        elif action == delete_action:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Удалить профиль? Данные будут потеряны.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.profile_manager.delete_profile(profile_id)
                self._refresh_profile_tree()
    
    def _delete_profile(self):
        """Удаление выбранного профиля"""
        selected = self.profile_tree.selectedItems()
        if not selected:
            return
        
        profile_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not profile_id:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить выбранный профиль?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.profile_manager.delete_profile(profile_id)
            self._refresh_profile_tree()
    
    def _set_proxy_dialog(self):
        """Диалог настройки прокси"""
        QMessageBox.information(
            self, "Прокси",
            "Управление прокси осуществляется через меню 'Прокси'.\n"
            "Доступные функции:\n"
            "• Добавление прокси в пул\n"
            "• Проверка здоровья\n"
            "• Привязка к профилям"
        )
    
    def _add_proxy_dialog(self):
        """Добавление прокси"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить прокси")
        dialog.setFixedSize(350, 250)
        
        layout = QFormLayout(dialog)
        
        host = QLineEdit()
        layout.addRow("Хост:", host)
        
        port = QSpinBox()
        port.setRange(1, 65535)
        port.setValue(8080)
        layout.addRow("Порт:", port)
        
        user = QLineEdit()
        layout.addRow("Логин:", user)
        
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Пароль:", password)
        
        protocol = QComboBox()
        protocol.addItems(["http", "https", "socks5"])
        layout.addRow("Протокол:", protocol)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(lambda: (
            self.proxy_manager.add_proxy(
                host.text(), port.value(),
                user.text() or None,
                password.text() or None,
                protocol.currentText()
            ),
            dialog.accept()
        ))
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.exec()
    
    def _check_all_proxies(self):
        """Проверка всех прокси"""
        self.statusbar.showMessage("Проверка прокси...")
        
        # Запускаем в фоновом потоке
        import threading
        
        def check():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                self.proxy_manager.check_all_proxies()
            )
            loop.close()
            
            working = sum(1 for v in results.values() if v)
            self.statusbar.showMessage(
                f"Проверка завершена | Работает: {working}/{len(results)}"
            )
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _open_lab_stand(self, checked=False):
        """Start the closed local lab target and open it in a browser profile."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Учебный стенд защиты")
        dialog.setFixedSize(420, 190)

        layout = QFormLayout(dialog)
        profile_input = QComboBox()
        for key, profile in LAB_PROFILES.items():
            profile_input.addItem(profile["name"], key)
        layout.addRow("Сценарий:", profile_input)

        info = QLabel(
            "Локальный сайт собирает fingerprint, storage, поведение и считает risk score. "
            "Он предназначен для закрытой демонстрации с преподавателем."
        )
        info.setWordWrap(True)
        layout.addRow(info)

        btn_layout = QHBoxLayout()
        start_btn = QPushButton("Открыть")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def open_selected():
            profile_key = profile_input.currentData()
            dialog.accept()
            self._start_lab_and_navigate(profile_key)

        start_btn.clicked.connect(open_selected)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def _start_lab_and_navigate(self, profile_key="clean"):
        """Open a lab URL in the current tab or create a profile tab first."""
        if self.lab_server is None:
            self.lab_server = LabServer()

        try:
            self.lab_server.start()
        except OSError as e:
            QMessageBox.critical(self, "Учебный стенд", f"Не удалось запустить локальный сервер:\n{e}")
            return

        url = self.lab_server.url(profile_key)
        current_tab = self.browser_tabs_widget.currentWidget()
        if not hasattr(current_tab, "navigate"):
            profile = self._get_navigation_profile()
            if not profile:
                QMessageBox.warning(self, "Учебный стенд", "Сначала создайте профиль браузера.")
                return
            self._load_profile(profile.id)
            current_tab = self.browser_tabs_widget.currentWidget()

        if hasattr(current_tab, "navigate"):
            current_tab.navigate(url)
            self.statusbar.showMessage(f"Учебный стенд открыт: {url}")

    def _stop_lab_stand(self, checked=False):
        """Stop the local lab target."""
        if self.lab_server:
            self.lab_server.stop()
            self.lab_server = None
            self.statusbar.showMessage("Учебный стенд остановлен")
        else:
            self.statusbar.showMessage("Учебный стенд не запущен")

    def _current_browser_tab(self):
        """Return the active BrowserTab, or show a clear warning."""
        current_index = self.browser_tabs_widget.currentIndex()
        current_tab = self.browser_tabs_widget.widget(current_index)
        if hasattr(current_tab, "page") and hasattr(current_tab, "webview"):
            return current_tab

        QMessageBox.warning(
            self,
            "Аудит страницы",
            "Откройте профиль и загрузите сайт во вкладке браузера."
        )
        return None

    def _install_behavior_recorder(self, checked=False):
        """Install passive behavior event recording on the current page."""
        browser_tab = self._current_browser_tab()
        if not browser_tab:
            return

        self.statusbar.showMessage("Включаю запись поведения на текущей странице...")
        browser_tab.page.runJavaScript(
            self.security_audit.install_behavior_recorder_script(),
            lambda result: self.statusbar.showMessage(
                "Запись поведения включена" if result in ("installed", "already_installed")
                else f"Не удалось включить запись поведения: {result}"
            )
        )

    def _run_security_audit(self, checked=False, export=False):
        """Collect defensive audit signals from the current page."""
        browser_tab = self._current_browser_tab()
        if not browser_tab:
            return

        self.statusbar.showMessage("Собираю аудит текущей страницы...")
        browser_tab.page.runJavaScript(
            self.security_audit.browser_signal_script(),
            lambda report: self._on_security_audit_ready(report, browser_tab, export)
        )

    def _on_security_audit_ready(self, report, browser_tab, export=False):
        """Attach behavior data and show or export the audit report."""
        if not isinstance(report, dict):
            QMessageBox.warning(self, "Аудит страницы", "Не удалось собрать данные страницы.")
            self.statusbar.showMessage("Аудит не собран")
            return

        def finish(behavior):
            if isinstance(behavior, dict):
                report["behavior"] = behavior
            else:
                report["behavior"] = {"installed": False}

            self.last_audit_report = report
            if export:
                path = self.security_audit.save_report(report)
                self.statusbar.showMessage(f"Аудит сохранен: {path.resolve()}")
                QMessageBox.information(self, "Экспорт аудита", f"Отчет сохранен:\n{path.resolve()}")
            else:
                self.statusbar.showMessage("Аудит текущей страницы собран")
                self._show_audit_report(report)

        browser_tab.page.runJavaScript(
            self.security_audit.collect_behavior_script(),
            finish
        )

    def _export_security_audit(self, checked=False):
        """Export last audit, or collect a fresh one if needed."""
        if self.last_audit_report:
            path = self.security_audit.save_report(self.last_audit_report)
            self.statusbar.showMessage(f"Аудит сохранен: {path.resolve()}")
            QMessageBox.information(self, "Экспорт аудита", f"Отчет сохранен:\n{path.resolve()}")
            return

        self._run_security_audit(export=True)

    def _show_audit_report(self, report):
        """Show a readable audit report with raw JSON for lab verification."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Аудит текущей страницы")
        dialog.resize(900, 700)

        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            self.security_audit.format_report(report)
            + "\n\nRAW JSON\n"
            + json.dumps(report, ensure_ascii=False, indent=2)
        )
        layout.addWidget(text)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить JSON")
        close_btn = QPushButton("Закрыть")

        def save_report():
            path = self.security_audit.save_report(report)
            self.statusbar.showMessage(f"Аудит сохранен: {path.resolve()}")
            QMessageBox.information(dialog, "Экспорт аудита", f"Отчет сохранен:\n{path.resolve()}")

        save_btn.clicked.connect(save_report)
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()
    
    def _check_stealth(self):
        """Проверка стелс-режима"""
        current_index = self.browser_tabs_widget.currentIndex()
        current_tab = self.browser_tabs_widget.widget(current_index)
        
        if hasattr(current_tab, 'navigate'):
            current_tab.navigate("https://bot.sannysoft.com")
    
    def _test_captcha(self):
        """Тест CAPTCHA"""
        current_index = self.browser_tabs_widget.currentIndex()
        current_tab = self.browser_tabs_widget.widget(current_index)
        
        if hasattr(current_tab, 'navigate'):
            current_tab.navigate("https://www.google.com/recaptcha/api2/demo")
    
    def _bulk_create_dialog(self):
        """Массовое создание профилей"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Массовое создание профилей")
        dialog.setFixedSize(300, 200)
        
        layout = QFormLayout(dialog)
        
        count = QSpinBox()
        count.setRange(1, 100)
        count.setValue(10)
        layout.addRow("Количество:", count)
        
        prefix = QLineEdit()
        prefix.setText("bot")
        layout.addRow("Префикс имени:", prefix)
        
        group = QComboBox()
        group.addItems(["Default", "Bots", "Testing"])
        layout.addRow("Группа:", group)
        
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Создать")
        create_btn.clicked.connect(lambda: (
            self.profile_manager.bulk_create(
                count.value(), prefix.text(),
                group=group.currentText()
            ),
            self._refresh_profile_tree(),
            dialog.accept()
        ))
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.exec()
    
    def _import_profiles(self):
        """Импорт профилей"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт профилей", "", "JSON (*.json)"
        )
        if path:
            imported = self.profile_manager.import_from_multilogin(path)
            self._refresh_profile_tree()
            self.statusbar.showMessage(f"Импортировано профилей: {len(imported)}")
    
    def _export_profile(self):
        """Экспорт профиля"""
        selected = self.profile_tree.selectedItems()
        if not selected:
            return
        
        profile_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not profile_id:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт профиля", "", "JSON (*.json)"
        )
        if path:
            self.profile_manager.export_to_json(profile_id, path)
    
    def _edit_fingerprint(self):
        """Редактирование отпечатка"""
        QMessageBox.information(
            self, "Редактор отпечатков",
            "Редактор отпечатков в разработке.\n"
            "Используйте файл fingerprint.json в директории профиля."
        )
    
    def _manage_cookies(self):
        """Управление куками"""
        if not self.current_profile:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте профиль")
            return
        
        jar = self.profile_manager.get_profile_cookies(self.current_profile.id)
        analysis = jar.analyze_ages()
        
        msg = f"""
        <b>Анализ кук профиля '{self.current_profile.name}':</b><br><br>
        Всего кук: {analysis['total']}<br>
        Старейшая: {analysis['oldest_days']:.0f} дней<br>
        Средний возраст: {analysis['average_days']:.0f} дней<br>
        Старше 30 дней: {analysis['aged_30d_plus']}<br>
        Старше 90 дней: {analysis['aged_90d_plus']}<br>
        Trust Score: {analysis['trust_score']}/100<br>
        """
        
        QMessageBox.information(self, "Куки профиля", msg)
    
    def _show_about(self):
        """О программе"""
        QMessageBox.about(
            self,
            "Phantom Anti-Detect Browser",
            """
            <h2>Phantom Anti-Detect Browser v3.0</h2>
            <p>Framework для тестирования защитных механизмов веб-приложений</p>
            <p><b>Возможности:</b></p>
            <ul>
                <li>Изолированные профили (Multilogin/GoLogin/AdsPower)</li>
                <li>Аудит fingerprint (Canvas/WebGL/Audio)</li>
                <li>Запись поведенческих сигналов</li>
                <li>Локальный учебный стенд с risk scoring</li>
                <li>Встроенные окна браузеров</li>
            </ul>
            <p><i>Для образовательных целей и тестирования.</i></p>
            """
        )
