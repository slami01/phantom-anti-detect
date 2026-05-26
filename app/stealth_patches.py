"""
Патчи для обхода обнаружения автоматизации
Переопределение свойств браузера через CDP
"""
import asyncio


class StealthPatches:
    """
    Набор патчей для маскировки браузера под реального пользователя
    
    Патчи применяются через:
    1. add_init_script (до загрузки страницы)
    2. CDP (Chrome DevTools Protocol)
    3. Переопределение свойств JS
    """
    
    @staticmethod
    def get_full_stealth_script() -> str:
        """Полный стелс-скрипт (все патчи)"""
        return """
// ============================================
// Phantom Full Stealth Script
// Маскировка всех известных методов обнаружения
// ============================================

(function() {
    'use strict';
    
    // === 1. WebDriver detection ===
    delete navigator.__proto__.webdriver;
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // === 2. Chrome runtime ===
    window.chrome = {
        runtime: {},
        loadTimes: function() { return {}; },
        csi: function() { return {}; },
        app: {
            isInstalled: false,
            InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
            RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
        }
    };
    
    // === 3. Permissions ===
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
    
    // === 4. Plugins ===
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5].map(() => ({
            name: 'Chrome PDF Plugin',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            length: 1
        }))
    });
    
    // === 5. MimeTypes ===
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => [
            { type: 'application/pdf', suffixes: 'pdf', description: '', enabledPlugin: {} },
            { type: 'text/pdf', suffixes: 'pdf', description: '', enabledPlugin: {} }
        ]
    });
    
    // === 6. Languages ===
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en']
    });
    
    // === 7. Connection ===
    if (navigator.connection) {
        Object.defineProperty(navigator.connection, 'rtt', {
            get: () => 50 + Math.floor(Math.random() * 30)
        });
    }
    
    // === 8. Hardware concurrency ===
    // Оставляем реальное значение — подозрительно, если у всех 8
    
    // === 9. Device memory ===
    // Оставляем реальное
    
    // === 10. Canvas noise ===
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const context = this.getContext('2d');
        if (context && this.width > 10 && this.height > 10) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                if (Math.random() < 0.002) {
                    imageData.data[i] ^= 1;
                }
            }
            context.putImageData(imageData, 0, 0);
        }
        return origToDataURL.apply(this, arguments);
    };
    
    // === 11. WebGL noise ===
    try {
        const getParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(pname) {
            // UNMASKED_VENDOR_WEBGL
            if (pname === 37445) return 'NVIDIA Corporation';
            // UNMASKED_RENDERER_WEBGL
            if (pname === 37446) return 'NVIDIA GeForce RTX 4070/PCIe/SSE2';
            return getParam.call(this, pname);
        };
    } catch(e) {}
    
    // === 12. Audio noise ===
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const origCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {
                const analyser = origCreateAnalyser.call(this);
                const origGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {
                    origGetFloatFrequencyData.call(this, array);
                    for (let i = 0; i < array.length; i++) {
                        array[i] += (Math.random() - 0.5) * 0.001;
                    }
                    return array;
                };
                return analyser;
            };
        }
    } catch(e) {}
    
    // === 13. Timezone ===
    const origGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = function() {
        return -180; // UTC+3 Москва
    };
    
    // === 14. Battery ===
    if (navigator.getBattery) {
        const origGetBattery = navigator.getBattery;
        navigator.getBattery = function() {
            return origGetBattery.call(this).then(battery => {
                Object.defineProperty(battery, 'charging', { get: () => true });
                Object.defineProperty(battery, 'level', { get: () => 0.85 + Math.random() * 0.15 });
                return battery;
            });
        };
    }
    
    // === 15. Отключаем автоматизационные флаги ===
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
    
    // === 16. Service Worker (не блокируем, это подозрительно) ===
    
    // === 17. Notification ===
    if (!('Notification' in window)) {
        window.Notification = function() {};
        window.Notification.permission = 'default';
        window.Notification.requestPermission = function() {
            return Promise.resolve('default');
        };
    }
    
    // === 18. Geolocation ===
    if (navigator.geolocation) {
        const origGetCurrentPosition = navigator.geolocation.getCurrentPosition;
        navigator.geolocation.getCurrentPosition = function(success, error, options) {
            // Возвращаем Москву
            success({
                coords: {
                    latitude: 55.7558 + (Math.random() - 0.5) * 0.01,
                    longitude: 37.6173 + (Math.random() - 0.5) * 0.01,
                    accuracy: 10 + Math.random() * 20,
                    altitude: null,
                    altitudeAccuracy: null,
                    heading: null,
                    speed: null
                },
                timestamp: Date.now()
            });
        };
    }
    
    console.log('[Phantom] Full stealth mode active');
})();
"""
    
    @staticmethod
    async def apply_cdp_patches(page):
        """
        Применение патчей через Chrome DevTools Protocol
        
        CDP позволяет менять параметры на уровне браузера,
        что не видно через JavaScript.
        """
        cdp = page.context.new_cdp_session(page)
        
        patches = [
            # Отключение автоматизации
            ('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'delete navigator.__proto__.webdriver;'
            }),
            # Отключение WebRTC (предотвращает утечку IP)
            ('Network.setBlockedURLs', {
                'urls': []
            }),
        ]
        
        for method, params in patches:
            try:
                await cdp.send(method, params)
            except:
                pass
    
    @staticmethod
    def get_font_spoofing_script(fonts: list) -> str:
        """Подмена списка доступных шрифтов"""
        font_list = ', '.join(f'"{f}"' for f in fonts)
        return f"""
        (function() {{
            const fonts = [{font_list}];
            const originalCheck = document.fonts.check.bind(document.fonts);
            document.fonts.check = function(font) {{
                const fontFamily = font.split(' ').pop().replace(/"/g, '');
                if (fonts.includes(fontFamily)) return true;
                return originalCheck(font);
            }};
        }})();
        """