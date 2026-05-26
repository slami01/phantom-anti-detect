"""
Генератор цифровых отпечатков браузера
Эмулирует: Multilogin + AdsPower + GoLogin
"""
import json
import random
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

@dataclass
class Fingerprint:
    """Полный цифровой отпечаток браузера"""
    # Системные
    os: str = "Windows 10"
    platform: str = "Win32"
    user_agent: str = ""
    app_version: str = ""
    
    # Экран
    screen_width: int = 1920
    screen_height: int = 1080
    avail_width: int = 1920
    avail_height: int = 1040
    color_depth: int = 24
    pixel_ratio: float = 1.0
    
    # Время и язык
    timezone: str = "Europe/Moscow"
    timezone_offset: int = 180
    locale: str = "ru-RU"
    language: str = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    languages: list = field(default_factory=lambda: ["ru-RU", "ru", "en-US", "en"])
    
    # Железо
    hardware_concurrency: int = 16
    device_memory: int = 16
    max_touch_points: int = 0
    
    # GPU/WebGL
    webgl_vendor: str = "NVIDIA Corporation"
    webgl_renderer: str = "NVIDIA GeForce RTX 4070/PCIe/SSE2"
    webgl2_max_texture_size: int = 16384
    webgl2_max_viewport_dims: list = field(default_factory=lambda: [16384, 16384])
    
    # Аудио
    audio_vendor: str = "Google Inc."
    audio_sample_rate: int = 44100
    audio_noise: float = 0.002
    
    # Canvas
    canvas_noise: float = 0.003
    canvas_hash: str = ""
    
    # Шрифты
    fonts: list = field(default_factory=lambda: [
        "Arial", "Arial Black", "Arial Narrow", "Book Antiqua",
        "Calibri", "Cambria", "Century Gothic", "Comic Sans MS",
        "Consolas", "Courier New", "Georgia", "Helvetica",
        "Impact", "Lucida Console", "Palatino Linotype",
        "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS",
        "Verdana", "Wingdings"
    ])
    
    # Сеть
    webrtc_private_ips: bool = False
    do_not_track: Optional[str] = None
    
    # Плагины
    plugins: list = field(default_factory=lambda: [
        "Chrome PDF Plugin", "Chrome PDF Viewer",
        "Native Client"
    ])
    mime_types: list = field(default_factory=lambda: [
        "application/pdf", "text/pdf"
    ])


class FingerprintEngine:
    """
    Генератор и менеджер цифровых отпечатков
    
    Режимы:
    - random: Генерация случайного отпечатка
    - template: Загрузка из шаблона (Multilogin-совместимый)
    - device: Имитация конкретного устройства
    """
    
    DEVICE_TEMPLATES = {
        "windows_desktop": {
            "os": "Windows 10",
            "platform": "Win32",
            "screen_width": 1920, "screen_height": 1080,
            "hardware_concurrency": 16, "device_memory": 16,
            "webgl_vendor": "NVIDIA Corporation",
            "webgl_renderer": "NVIDIA GeForce RTX 4070/PCIe/SSE2",
            "timezone": "Europe/Moscow",
            "locale": "ru-RU",
            "fonts": ["Arial", "Times New Roman", "Verdana", "Georgia", "Consolas", "Segoe UI"],
        },
        "macbook_pro": {
            "os": "Mac OS X 10.15.7",
            "platform": "MacIntel",
            "screen_width": 1680, "screen_height": 1050,
            "hardware_concurrency": 10, "device_memory": 16,
            "webgl_vendor": "Apple",
            "webgl_renderer": "Apple M2 Pro",
            "timezone": "America/New_York",
            "locale": "en-US",
            "fonts": ["Arial", "Helvetica", "Times", "Courier", "Georgia", "Verdana"],
        },
        "iphone_15": {
            "os": "iOS 17.2",
            "platform": "iPhone",
            "screen_width": 393, "screen_height": 852,
            "pixel_ratio": 3.0,
            "hardware_concurrency": 6, "device_memory": 8,
            "max_touch_points": 5,
            "webgl_vendor": "Apple",
            "webgl_renderer": "Apple A17 Pro",
            "timezone": "Europe/London",
            "locale": "en-GB",
            "fonts": ["Arial", "Helvetica", "Times New Roman", "Courier"],
        }
    }
    
    def __init__(self, profile_dir: str = None):
        self.profile_dir = Path(profile_dir) if profile_dir else None
        self.current_fingerprint = None
        
    def generate_random(self) -> Fingerprint:
        """Генерация случайного уникального отпечатка"""
        # Случайный выбор ОС
        os_choice = random.choice([
            ("Windows 10", "Win32"),
            ("Windows 11", "Win32"),
            ("Mac OS X 10.15.7", "MacIntel"),
        ])
        
        # Случайное разрешение экрана
        resolutions = [
            (1920, 1080), (2560, 1440), (1366, 768),
            (1440, 900), (1680, 1050), (3840, 2160)
        ]
        screen_w, screen_h = random.choice(resolutions)
        
        # Случайные GPU
        gpus = [
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 4070/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
            ("AMD", "AMD Radeon RX 6800 XT"),
            ("Intel", "Intel Iris Xe Graphics"),
        ]
        gpu_vendor, gpu_renderer = random.choice(gpus)
        
        # Случайный часовой пояс
        timezones = [
            ("Europe/Moscow", 180),
            ("Europe/London", 0),
            ("America/New_York", -300),
            ("Asia/Tokyo", 540),
        ]
        tz_name, tz_offset = random.choice(timezones)
        
        # Случайные языки
        languages = random.choice([
            ["ru-RU", "ru", "en-US", "en"],
            ["en-US", "en", "es", "fr"],
            ["de-DE", "de", "en-US", "en"],
        ])
        
        # Создание отпечатка
        fp = Fingerprint(
            os=os_choice[0],
            platform=os_choice[1],
            screen_width=screen_w,
            screen_height=screen_h,
            avail_width=screen_w,
            avail_height=screen_h - 40,  # Минус панель задач
            timezone=tz_name,
            timezone_offset=tz_offset,
            locale=languages[0].replace("-", "_"),
            language=",".join([f"{l};q={1.0 - i*0.1}" for i, l in enumerate(languages)]),
            languages=languages,
            hardware_concurrency=random.choice([4, 8, 12, 16, 24, 32]),
            device_memory=random.choice([4, 8, 16, 32]),
            webgl_vendor=gpu_vendor,
            webgl_renderer=gpu_renderer,
            canvas_noise=random.uniform(0.001, 0.005),
            audio_noise=random.uniform(0.001, 0.003),
        )
        
        # Генерация canvas hash (имитация)
        fp.canvas_hash = hashlib.sha256(
            f"{fp.webgl_renderer}{fp.screen_width}{fp.fonts}{fp.canvas_noise}".encode()
        ).hexdigest()[:16]
        
        # Генерация User-Agent
        chrome_versions = ["124.0.6367.91", "124.0.6367.78", "123.0.6312.122"]
        chrome_ver = random.choice(chrome_versions)
        
        if fp.platform == "Win32":
            fp.user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
        elif fp.platform == "MacIntel":
            fp.user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
        
        self.current_fingerprint = fp
        
        # Сохраняем в профиль
        if self.profile_dir:
            self.save(fp)
            
        return fp
    
    def from_template(self, template_name: str) -> Fingerprint:
        """Загрузка отпечатка из шаблона устройства"""
        if template_name not in self.DEVICE_TEMPLATES:
            raise ValueError(f"Шаблон '{template_name}' не найден. Доступные: {list(self.DEVICE_TEMPLATES.keys())}")
        
        template = self.DEVICE_TEMPLATES[template_name]
        fp = Fingerprint(**template)
        
        # Дополняем недостающие поля
        if not fp.user_agent:
            chrome_ver = "124.0.6367.91"
            if fp.platform == "Win32":
                fp.user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
            elif fp.platform == "MacIntel":
                fp.user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
            elif fp.platform == "iPhone":
                fp.user_agent = f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        
        self.current_fingerprint = fp
        
        if self.profile_dir:
            self.save(fp)
            
        return fp
    
    def save(self, fingerprint: Fingerprint):
        """Сохранение отпечатка в профиль"""
        if not self.profile_dir:
            return
        
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with open(self.profile_dir / "fingerprint.json", "w") as f:
            json.dump(asdict(fingerprint), f, indent=2)
    
    def load(self) -> Optional[Fingerprint]:
        """Загрузка отпечатка из профиля"""
        if not self.profile_dir:
            return None
        
        fp_file = self.profile_dir / "fingerprint.json"
        if not fp_file.exists():
            return None
        
        with open(fp_file) as f:
            data = json.load(f)
        
        self.current_fingerprint = Fingerprint(**data)
        return self.current_fingerprint
    
    def get_stealth_script(self) -> str:
        """Генерация JavaScript для внедрения в страницу (обход fingerprint-проверок)"""
        if not self.current_fingerprint:
            return ""
        
        fp = self.current_fingerprint
        
        return f"""
// ============================================
// Phantom Anti-Detect Browser - Stealth Script
// ============================================

// 1. navigator.webdriver = false
Object.defineProperty(navigator, 'webdriver', {{
    get: () => undefined
}});

// 2. navigator.platform
Object.defineProperty(navigator, 'platform', {{
    get: () => '{fp.platform}'
}});

// 3. screen metrics
Object.defineProperty(screen, 'width', {{ get: () => {fp.screen_width} }});
Object.defineProperty(screen, 'height', {{ get: () => {fp.screen_height} }});
Object.defineProperty(screen, 'availWidth', {{ get: () => {fp.avail_width} }});
Object.defineProperty(screen, 'availHeight', {{ get: () => {fp.avail_height} }});
Object.defineProperty(screen, 'colorDepth', {{ get: () => {fp.color_depth} }});
Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {fp.pixel_ratio} }});

// 4. navigator.hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {{
    get: () => {fp.hardware_concurrency}
}});

// 5. navigator.deviceMemory
Object.defineProperty(navigator, 'deviceMemory', {{
    get: () => {fp.device_memory}
}});

// 6. navigator.maxTouchPoints
Object.defineProperty(navigator, 'maxTouchPoints', {{
    get: () => {fp.max_touch_points}
}});

// 7. navigator.language и languages
Object.defineProperty(navigator, 'language', {{
    get: () => '{fp.languages[0]}'
}});
Object.defineProperty(navigator, 'languages', {{
    get: () => {json.dumps(fp.languages)}
}});

// 8. WebGL vendor/renderer
const getParameterProxyHandler = {{
    apply: function(target, thisArg, args) {{
        const param = args[0];
        // UNMASKED_VENDOR_WEBGL = 37445
        if (param === 37445) return '{fp.webgl_vendor}';
        // UNMASKED_RENDERER_WEBGL = 37446
        if (param === 37446) return '{fp.webgl_renderer}';
        return Reflect.apply(target, thisArg, args);
    }}
}};

if (WebGLRenderingContext) {{
    WebGLRenderingContext.prototype.getParameter = new Proxy(
        WebGLRenderingContext.prototype.getParameter,
        getParameterProxyHandler
    );
}}
if (WebGL2RenderingContext) {{
    WebGL2RenderingContext.prototype.getParameter = new Proxy(
        WebGL2RenderingContext.prototype.getParameter,
        getParameterProxyHandler
    );
}}

// 9. Canvas fingerprint noise
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
const originalToBlob = HTMLCanvasElement.prototype.toBlob;
const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

HTMLCanvasElement.prototype.toDataURL = function() {{
    addCanvasNoise(this, {fp.canvas_noise});
    return originalToDataURL.apply(this, arguments);
}};

HTMLCanvasElement.prototype.toBlob = function() {{
    addCanvasNoise(this, {fp.canvas_noise});
    return originalToBlob.apply(this, arguments);
}};

CanvasRenderingContext2D.prototype.getImageData = function() {{
    addCanvasNoise(this.canvas, {fp.canvas_noise});
    return originalGetImageData.apply(this, arguments);
}};

function addCanvasNoise(canvas, noise) {{
    try {{
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        for (let i = 0; i < imageData.data.length; i += 4) {{
            if (Math.random() < noise) {{
                imageData.data[i] ^= 1;
                imageData.data[i+1] ^= 1;
                imageData.data[i+2] ^= 1;
            }}
        }}
        ctx.putImageData(imageData, 0, 0);
    }} catch(e) {{}}
}}

// 10. AudioContext fingerprint noise
if (AudioContext || webkitAudioContext) {{
    const AudioCtx = AudioContext || webkitAudioContext;
    const originalCreateOscillator = AudioCtx.prototype.createOscillator;
    AudioCtx.prototype.createOscillator = function() {{
        const osc = originalCreateOscillator.apply(this, arguments);
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {{
            const data = originalGetChannelData.call(this, channel);
            for (let i = 0; i < data.length; i++) {{
                data[i] += (Math.random() - 0.5) * {fp.audio_noise};
            }}
            return data;
        }};
        return osc;
    }};
}}

// 11. Плагины
Object.defineProperty(navigator, 'plugins', {{
    get: () => {{
        const plugins = {json.dumps(fp.plugins)};
        return Object.assign([...plugins], {{
            item: (i) => plugins[i] || null,
            namedItem: (name) => plugins.find(p => p === name) || null,
            refresh: () => {{}}
        }});
    }}
}});

// 12. doNotTrack
Object.defineProperty(navigator, 'doNotTrack', {{
    get: () => '{fp.do_not_track or "unspecified"}'
}});

// 13. permissions
if (navigator.permissions && navigator.permissions.query) {{
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = function(parameters) {{
        if (parameters.name === 'notifications') {{
            return Promise.resolve({{ state: Notification.permission }});
        }}
        return originalQuery.call(this, parameters);
    }};
}}

// 14. timezone offset
Date.prototype.getTimezoneOffset = function() {{
    return {fp.timezone_offset};
}};

// 15. chrome объект
window.chrome = {{
    runtime: {{}},
    loadTimes: function() {{}},
    csi: function() {{}},
    app: {{}}
}};

// 16. Интеграция Google Analytics/Meta Pixel (пропускаем трекеры)
// Не блокируем, а пропускаем с подменой — это менее подозрительно
if (window.ga) {{
    const originalGA = window.ga;
    window.ga = function() {{
        try {{ return originalGA.apply(this, arguments); }} catch(e) {{}}
    }};
}}

console.log('[Phantom] Stealth script injected successfully');
"""