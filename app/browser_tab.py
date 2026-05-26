"""
Вкладка с встроенным браузером через PyQt6 WebEngine
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings, QWebEngineScript
from PyQt6.QtCore import QUrl, Qt, pyqtSignal


class BrowserTab(QWidget):
    """
    Вкладка со встроенным браузером
    """
    
    url_changed = pyqtSignal(str)
    title_changed = pyqtSignal(str)
    loading_finished = pyqtSignal(bool)
    
    def __init__(self, profile_dir: str = None, fingerprint_script: str = ""):
        super().__init__()
        
        self.profile_dir = profile_dir
        self.fingerprint_script = fingerprint_script
        
        # Создаём изолированный профиль WebEngine
        profile_name = f"phantom_{id(self)}"
        
        # Пробуем создать профиль с путём к хранилищу
        if profile_dir:
            abs_path = os.path.abspath(profile_dir)
            os.makedirs(abs_path, exist_ok=True)
            
            # В разных версиях PyQt6 методы называются по-разному
            try:
                # Новый способ (PyQt6 6.5+)
                self.profile = QWebEngineProfile(profile_name)
                self.profile.setPersistentStoragePath(abs_path)
                self.profile.setCachePath(os.path.join(abs_path, "cache"))
            except:
                try:
                    # Старый способ
                    self.profile = QWebEngineProfile(profile_name)
                    self.profile.setHttpCachePath(os.path.join(abs_path, "cache"))
                except:
                    # Запасной вариант
                    self.profile = QWebEngineProfile(profile_name)
        else:
            self.profile = QWebEngineProfile(profile_name)
        
        # Настройки профиля: сохраняем данные как обычный браузер.
        try:
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        except Exception:
            pass
        try:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
        except Exception:
            pass
        
        # Настройки WebEngine
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, False)
        
        # Страница
        self.page = QWebEnginePage(self.profile, self)
        
        # WebView
        self.webview = QWebEngineView()
        self.webview.setPage(self.page)
        
        self._init_ui()
        self._connect_signals()
        
        # Внедрение стелс-скрипта
        if fingerprint_script:
            self._inject_stealth_script(fingerprint_script)
    
    def _init_ui(self):
        """Построение интерфейса вкладки"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Панель навигации
        navbar = QFrame()
        navbar.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
                padding: 5px;
            }
        """)
        navbar.setMaximumHeight(45)
        
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        
        # Кнопки навигации
        self.btn_back = QPushButton("◀")
        self.btn_back.setFixedSize(30, 28)
        self.btn_back.setStyleSheet("background: #3d3d3d; color: white; border: none; border-radius: 4px;")
        
        self.btn_forward = QPushButton("▶")
        self.btn_forward.setFixedSize(30, 28)
        self.btn_forward.setStyleSheet("background: #3d3d3d; color: white; border: none; border-radius: 4px;")
        
        self.btn_reload = QPushButton("↻")
        self.btn_reload.setFixedSize(30, 28)
        self.btn_reload.setStyleSheet("background: #3d3d3d; color: white; border: none; border-radius: 4px;")
        
        self.btn_home = QPushButton("⌂")
        self.btn_home.setFixedSize(30, 28)
        self.btn_home.setStyleSheet("background: #3d3d3d; color: white; border: none; border-radius: 4px;")
        
        # Адресная строка
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите URL...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 15px;
                padding: 5px 15px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        
        # Кнопка перехода
        self.btn_go = QPushButton("→")
        self.btn_go.setFixedSize(40, 28)
        self.btn_go.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084e0;
            }
        """)
        
        # Добавляем на панель
        nav_layout.addWidget(self.btn_back)
        nav_layout.addWidget(self.btn_forward)
        nav_layout.addWidget(self.btn_reload)
        nav_layout.addWidget(self.btn_home)
        nav_layout.addWidget(self.url_bar)
        nav_layout.addWidget(self.btn_go)
        
        # Строка состояния
        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                padding: 2px 10px;
                background-color: #2d2d2d;
            }
        """)
        self.status_label.setMaximumHeight(22)
        
        # Добавляем виджеты
        layout.addWidget(navbar)
        layout.addWidget(self.webview)
        layout.addWidget(self.status_label)
    
    def _connect_signals(self):
        """Подключение сигналов"""
        self.url_bar.returnPressed.connect(self._navigate)
        self.btn_go.clicked.connect(self._navigate)
        self.btn_back.clicked.connect(self.webview.back)
        self.btn_forward.clicked.connect(self.webview.forward)
        self.btn_reload.clicked.connect(self.webview.reload)
        self.btn_home.clicked.connect(lambda: self.navigate("about:blank"))
        
        self.webview.urlChanged.connect(self._on_url_changed)
        self.webview.titleChanged.connect(self._on_title_changed)
        self.webview.loadStarted.connect(lambda: self.status_label.setText("Загрузка..."))
        self.webview.loadFinished.connect(self._on_load_finished)
    
    def _navigate(self):
        """Переход по URL"""
        url = self.url_bar.text().strip()
        if not url:
            return
        
        self.navigate(url)
    
    def navigate(self, url: str):
        """Навигация на URL"""
        qurl = self._normalize_url(url)
        if not qurl.isValid():
            self.status_label.setText("✗ Неверный URL")
            return

        self.url_bar.setText(qurl.toString())
        self.webview.load(qurl)

    @staticmethod
    def _normalize_url(url: str) -> QUrl:
        """Convert user input like google.com into a loadable QUrl."""
        value = (url or "").strip()
        if value.startswith(("about:", "data:", "file:", "blob:", "qrc:")):
            return QUrl(value)
        return QUrl.fromUserInput(value)
    
    def _on_url_changed(self, url: QUrl):
        """Обновление адресной строки"""
        self.url_bar.setText(url.toString())
        self.url_changed.emit(url.toString())
    
    def _on_title_changed(self, title: str):
        """Обновление заголовка"""
        self.title_changed.emit(title)
    
    def _on_load_finished(self, ok: bool):
        """Завершение загрузки"""
        if ok:
            self.status_label.setText("✓ Загружено")
        else:
            self.status_label.setText("✗ Ошибка загрузки")
        self.loading_finished.emit(ok)
    
    def _inject_stealth_script(self, script: str):
        """Внедрение стелс-скрипта"""
        qscript = QWebEngineScript()
        qscript.setSourceCode(script)
        qscript.setName("stealth_script")
        qscript.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        qscript.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        qscript.setRunsOnSubFrames(True)
        
        self.profile.scripts().insert(qscript)
    
    def execute_js(self, script: str, callback=None):
        """Выполнение JavaScript на странице"""
        if callback:
            self.page.runJavaScript(script, callback)
        else:
            self.page.runJavaScript(script)
    
    def get_html(self, callback):
        """Получить HTML страницы"""
        self.page.toHtml(callback)
    
    def clear_data(self):
        """Очистка данных профиля"""
        self.profile.clearHttpCache()
        self.profile.cookieStore().deleteAllCookies()
