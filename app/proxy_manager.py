"""
Менеджер прокси с ротацией, пулами и проверкой здоровья
"""
import json
import random
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Proxy:
    """Прокси-сервер"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    # Метаданные
    country: str = "Unknown"
    asn: str = ""
    provider: str = ""
    
    # Статистика
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0
    score: int = 100  # Репутация прокси
    is_working: bool = True
    
    @property
    def url(self) -> str:
        """URL прокси в формате Playwright"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def server_url(self) -> str:
        """URL для Playwright (server)"""
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyManager:
    """
    Управление прокси-серверами
    
    Функции:
    - Загрузка пула прокси
    - Ротация (round-robin, random, по score)
    - Проверка здоровья
    - Привязка прокси к профилю
    - Автоматическая смена при бане
    """
    
    ROTATION_MODES = ['random', 'round_robin', 'best_score', 'sticky']
    
    def __init__(self, pool_file: str = "proxies/pool.json"):
        self.pool_file = Path(pool_file)
        self.proxies: List[Proxy] = []
        self._rotation_index = 0
        self._profile_proxy_map: Dict[str, Proxy] = {}
        self.mode = "random"
        
        self.load()
    
    def load(self):
        """Загрузка прокси из файла"""
        if self.pool_file.exists():
            with open(self.pool_file) as f:
                data = json.load(f)
            
            self.proxies = [
                Proxy(**p) for p in data.get('proxies', [])
            ]
    
    def save(self):
        """Сохранение прокси в файл"""
        self.pool_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pool_file, 'w') as f:
            json.dump({
                'proxies': [
                    {
                        'host': p.host,
                        'port': p.port,
                        'username': p.username,
                        'password': p.password,
                        'protocol': p.protocol,
                        'country': p.country,
                        'asn': p.asn,
                        'provider': p.provider,
                    }
                    for p in self.proxies
                ]
            }, f, indent=2)
    
    def add_proxy(
        self, host: str, port: int,
        username: str = None, password: str = None,
        protocol: str = "http",
        country: str = "Unknown"
    ) -> Proxy:
        """Добавление прокси в пул"""
        proxy = Proxy(
            host=host, port=port,
            username=username, password=password,
            protocol=protocol, country=country
        )
        self.proxies.append(proxy)
        self.save()
        return proxy
    
    def remove_proxy(self, host: str, port: int):
        """Удаление прокси из пула"""
        self.proxies = [
            p for p in self.proxies
            if not (p.host == host and p.port == port)
        ]
        self.save()
    
    def get_proxy(self, profile_name: str = None, mode: str = None) -> Optional[Proxy]:
        """
        Получение прокси для профиля
        
        Args:
            profile_name: Имя профиля (для sticky-режима)
            mode: Режим выбора (random, round_robin, best_score, sticky)
        """
        mode = mode or self.mode
        
        # Фильтруем только работающие
        working = [p for p in self.proxies if p.is_working]
        if not working:
            return None
        
        # Sticky — привязанный к профилю
        if mode == 'sticky' and profile_name:
            if profile_name in self._profile_proxy_map:
                proxy = self._profile_proxy_map[profile_name]
                if proxy.is_working:
                    return proxy
            # Если привязанный не работает — выбираем новый
            proxy = self._select_proxy(working, 'best_score')
            self._profile_proxy_map[profile_name] = proxy
            return proxy
        
        return self._select_proxy(working, mode)
    
    def _select_proxy(self, proxies: List[Proxy], mode: str) -> Proxy:
        """Выбор прокси по режиму"""
        if mode == 'random':
            return random.choice(proxies)
        
        elif mode == 'round_robin':
            proxy = proxies[self._rotation_index % len(proxies)]
            self._rotation_index += 1
            return proxy
        
        elif mode == 'best_score':
            return max(proxies, key=lambda p: p.score)
        
        return random.choice(proxies)
    
    def report_success(self, proxy: Proxy):
        """Отметить успешное использование прокси"""
        proxy.success_count += 1
        proxy.score = min(100, proxy.score + 1)
        self.save()
    
    def report_failure(self, proxy: Proxy):
        """Отметить неудачное использование"""
        proxy.fail_count += 1
        proxy.score = max(0, proxy.score - 20)
        
        # Если много ошибок — помечаем как нерабочий
        if proxy.fail_count > 3:
            proxy.is_working = False
        
        self.save()
    
    def rotate_proxy(self, profile_name: str) -> Optional[Proxy]:
        """Принудительная смена прокси для профиля"""
        if profile_name in self._profile_proxy_map:
            old_proxy = self._profile_proxy_map[profile_name]
            old_proxy.is_working = False
        
        working = [p for p in self.proxies if p.is_working]
        if working:
            new_proxy = self._select_proxy(working, 'random')
            self._profile_proxy_map[profile_name] = new_proxy
            return new_proxy
        return None
    
    async def check_all_proxies(self) -> dict:
        """Проверка здоровья всех прокси"""
        results = {}
        for proxy in self.proxies:
            results[f"{proxy.host}:{proxy.port}"] = await self._check_proxy(proxy)
        return results
    
    async def _check_proxy(self, proxy: Proxy) -> bool:
        """Проверка одного прокси"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://httpbin.org/ip',
                    proxy=proxy.url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    proxy.is_working = resp.status == 200
                    return proxy.is_working
        except:
            proxy.is_working = False
            return False
    
    def get_statistics(self) -> dict:
        """Статистика по прокси"""
        total = len(self.proxies)
        working = sum(1 for p in self.proxies if p.is_working)
        return {
            'total': total,
            'working': working,
            'broken': total - working,
            'by_country': self._count_by_country()
        }
    
    def _count_by_country(self) -> dict:
        """Группировка по странам"""
        countries = {}
        for proxy in self.proxies:
            countries[proxy.country] = countries.get(proxy.country, 0) + 1
        return countries