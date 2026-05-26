"""
Решатель CAPTCHA с поддержкой разных провайдеров
"""
import asyncio
import base64
import time
from typing import Optional


class CaptchaSolver:
    """
    Автоматический обход CAPTCHA
    
    Поддерживаемые типы:
    - reCAPTCHA v2/v3
    - hCaptcha
    - Cloudflare Turnstile
    - Текстовые CAPTCHA
    
    Методы:
    - Автоматическое решение (через сервисы)
    - Эмуляция человеческого решения
    - Fallback: пауза и повтор
    """
    
    CAPTCHA_SELECTORS = {
        'recaptcha_v2': [
            'iframe[src*="recaptcha"]',
            '.g-recaptcha',
            '[data-sitekey]',
            '#g-recaptcha-response'
        ],
        'recaptcha_v3': [
            '.grecaptcha-badge',
            'script[src*="recaptcha/api.js"]'
        ],
        'hcaptcha': [
            'iframe[src*="hcaptcha"]',
            '.h-captcha',
            '[data-hcaptcha-widget-id]'
        ],
        'turnstile': [
            '#turnstile-wrapper',
            '.cf-turnstile',
            'script[src*="challenges.cloudflare.com"]'
        ]
    }
    
    def __init__(self, api_key: str = None, service: str = "2captcha"):
        self.api_key = api_key
        self.service = service
    
    async def detect_captcha(self, page) -> Optional[str]:
        """Определение типа CAPTCHA на странице"""
        for captcha_type, selectors in self.CAPTCHA_SELECTORS.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        return captcha_type
                except:
                    continue
        return None
    
    async def solve(self, page, captcha_type: str = None) -> bool:
        """
        Решение CAPTCHA
        
        Returns:
            True если CAPTCHA решена или не найдена
        """
        if captcha_type is None:
            captcha_type = await self.detect_captcha(page)
        
        if captcha_type is None:
            return True  # Нет CAPTCHA
        
        if captcha_type == 'recaptcha_v2':
            return await self._solve_recaptcha_v2(page)
        elif captcha_type == 'recaptcha_v3':
            return await self._handle_recaptcha_v3(page)
        elif captcha_type == 'hcaptcha':
            return await self._solve_hcaptcha(page)
        elif captcha_type == 'turnstile':
            return await self._solve_turnstile(page)
        
        return False
    
    async def _solve_recaptcha_v2(self, page) -> bool:
        """Решение reCAPTCHA v2"""
        # Пытаемся получить sitekey
        sitekey = await page.evaluate("""
            () => {
                const iframe = document.querySelector('iframe[src*="recaptcha"]');
                if (iframe) {
                    const match = iframe.src.match(/[?&]k=([^&]+)/);
                    return match ? match[1] : null;
                }
                const el = document.querySelector('[data-sitekey]');
                return el ? el.getAttribute('data-sitekey') : null;
            }
        """)
        
        if not sitekey:
            return False
        
        # Если есть API ключ — используем сервис
        if self.api_key:
            token = await self._request_captcha_service(
                sitekey=sitekey,
                page_url=page.url,
                captcha_type='recaptcha_v2'
            )
            if token:
                await page.evaluate(f"""
                    document.getElementById('g-recaptcha-response')
                        .innerHTML = '{token}';
                    document.querySelector('.g-recaptcha')
                        ?.dispatchEvent(new Event('submit'));
                """)
                return True
        
        # Без API ключа — кликаем и ждём (иногда Google пропускает)
        try:
            frame = await page.query_selector('iframe[src*="recaptcha"]')
            if frame:
                box = await frame.bounding_box()
                if box:
                    # Клик по чекбоксу
                    await page.mouse.click(
                        box['x'] + box['width'] / 2,
                        box['y'] + box['height'] / 2
                    )
                    await asyncio.sleep(3)
                    
                    # Проверяем, решилась ли
                    solved = await page.evaluate("""
                        () => document.getElementById('g-recaptcha-response')
                            ?.value?.length > 0
                    """)
                    return solved
        except:
            pass
        
        return False
    
    async def _handle_recaptcha_v3(self, page) -> bool:
        """reCAPTCHA v3 — невидимая, просто ждём"""
        # v3 не требует действий пользователя
        # Просто ждём и надеемся на хороший score
        await asyncio.sleep(2)
        return True
    
    async def _solve_hcaptcha(self, page) -> bool:
        """Решение hCaptcha"""
        sitekey = await page.evaluate("""
            () => {
                const el = document.querySelector('[data-sitekey]');
                return el ? el.getAttribute('data-sitekey') : null;
            }
        """)
        
        if sitekey and self.api_key:
            token = await self._request_captcha_service(
                sitekey=sitekey,
                page_url=page.url,
                captcha_type='hcaptcha'
            )
            if token:
                await page.evaluate(f"""
                    document.querySelector('[data-hcaptcha-response]')
                        .value = '{token}';
                    document.querySelector('.h-captcha')
                        ?.dispatchEvent(new Event('submit'));
                """)
                return True
        
        return False
    
    async def _solve_turnstile(self, page) -> bool:
        """Cloudflare Turnstile"""
        # Turnstile обычно решается автоматически браузером
        # Ждём пока появится токен
        for _ in range(10):
            token = await page.evaluate("""
                () => {
                    const input = document.querySelector('[name="cf-turnstile-response"]');
                    return input ? input.value : null;
                }
            """)
            if token:
                return True
            await asyncio.sleep(1)
        
        return False
    
    async def _request_captcha_service(
        self, sitekey: str, page_url: str, captcha_type: str
    ) -> Optional[str]:
        """Запрос к сервису решения CAPTCHA"""
        # Заглушка — в реальности здесь запрос к 2captcha/anti-captcha
        import aiohttp
        
        if self.service == "2captcha":
            url = "https://2captcha.com/in.php"
            params = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': sitekey,
                'pageurl': page_url,
                'json': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as resp:
                    data = await resp.json()
                    if data.get('status') == 1:
                        request_id = data['request']
                        
                        # Ожидание решения
                        for _ in range(30):
                            await asyncio.sleep(5)
                            result = await session.get(
                                f"https://2captcha.com/res.php",
                                params={
                                    'key': self.api_key,
                                    'action': 'get',
                                    'id': request_id,
                                    'json': 1
                                }
                            )
                            result_data = await result.json()
                            if result_data.get('status') == 1:
                                return result_data['request']
        
        return None