"""
Хранилище кук с анализом возраста, ротацией и инжекцией
"""
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class CookieRecord:
    """Запись о куке"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    http_only: bool = False
    secure: bool = True
    same_site: str = "Lax"
    
    # Метаданные для анализа
    first_seen: float = 0  # Когда впервые получена
    last_seen: float = 0  # Когда последний раз обновлялась
    hit_count: int = 0  # Сколько раз использовалась
    
    @property
    def age_days(self) -> float:
        """Возраст куки в днях"""
        if self.first_seen == 0:
            return 0
        return (time.time() - self.first_seen) / 86400
    
    @property
    def is_expired(self) -> bool:
        """Проверка на истечение срока"""
        if self.expires is None:
            return False
        return time.time() > self.expires


class CookieJar:
    """
    Управление куками профиля
    
    Функции:
    - Сохранение/загрузка кук
    - Анализ возраста (старые куки = больше доверия)
    - Инжекция в браузер
    - Ротация (обновление старых кук)
    - Импорт из браузеров (Chrome, Firefox)
    """
    
    def __init__(self, profile_dir: str = None):
        self.profile_dir = Path(profile_dir) if profile_dir else None
        self.cookies: Dict[str, CookieRecord] = {}
        self.session_history: List[Dict] = []
        
        if self.profile_dir:
            self.load()
    
    def load(self):
        """Загрузка кук из профиля"""
        cookies_file = self.profile_dir / "cookies.json"
        if cookies_file.exists():
            with open(cookies_file) as f:
                data = json.load(f)
            
            self.cookies = {
                f"{c['domain']}|{c['name']}": CookieRecord(**c)
                for c in data.get('cookies', [])
            }
            self.session_history = data.get('history', [])
    
    def save(self):
        """Сохранение кук в профиль"""
        if not self.profile_dir:
            return
        
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with open(self.profile_dir / "cookies.json", "w") as f:
            json.dump({
                'cookies': [asdict(c) for c in self.cookies.values()],
                'history': self.session_history,
                'saved_at': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_cookie(self, cookie: dict):
        """Добавление/обновление куки"""
        key = f"{cookie.get('domain', '')}|{cookie.get('name', '')}"
        now = time.time()
        
        if key in self.cookies:
            # Обновляем существующую
            record = self.cookies[key]
            record.value = cookie.get('value', '')
            record.last_seen = now
            record.hit_count += 1
        else:
            # Создаём новую
            record = CookieRecord(
                name=cookie.get('name', ''),
                value=cookie.get('value', ''),
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/'),
                expires=cookie.get('expires', -1) if cookie.get('expires', -1) > 0 else None,
                http_only=cookie.get('httpOnly', False),
                secure=cookie.get('secure', True),
                same_site=cookie.get('sameSite', 'Lax'),
                first_seen=now,
                last_seen=now,
                hit_count=1
            )
            self.cookies[key] = record
        
        self.save()
    
    def add_cookies_batch(self, cookies: List[dict]):
        """Пакетное добавление кук"""
        for cookie in cookies:
            self.add_cookie(cookie)
    
    def get_cookies_for_domain(self, domain: str) -> List[dict]:
        """Получить куки для домена"""
        result = []
        for key, record in self.cookies.items():
            if domain in record.domain or record.domain in domain:
                if not record.is_expired:
                    result.append({
                        'name': record.name,
                        'value': record.value,
                        'domain': record.domain,
                        'path': record.path,
                        'expires': record.expires,
                        'httpOnly': record.http_only,
                        'secure': record.secure,
                        'sameSite': record.same_site
                    })
        return result
    
    def get_all_valid_cookies(self) -> List[dict]:
        """Все неистекшие куки"""
        return [
            {
                'name': r.name,
                'value': r.value,
                'domain': r.domain,
                'path': r.path,
                'expires': r.expires,
                'httpOnly': r.http_only,
                'secure': r.secure,
                'sameSite': r.same_site
            }
            for r in self.cookies.values()
            if not r.is_expired
        ]
    
    def analyze_ages(self) -> dict:
        """Анализ возраста кук (старые = доверие)"""
        ages = [r.age_days for r in self.cookies.values()]
        
        if not ages:
            return {
                'total': 0,
                'oldest_days': 0,
                'average_days': 0,
                'aged_30d_plus': 0,
                'aged_90d_plus': 0,
                'trust_score': 0
            }
        
        aged_30 = sum(1 for a in ages if a >= 30)
        aged_90 = sum(1 for a in ages if a >= 90)
        
        # Trust score: 0-100, основан на возрасте кук
        trust_score = min(100, 
            (min(max(ages), 180) / 180) * 50 +  # Макс 50 за возраст
            (len(ages) / 20) * 30 +  # Макс 30 за количество
            (aged_30 / max(len(ages), 1)) * 20  # Макс 20 за старые куки
        )
        
        return {
            'total': len(ages),
            'oldest_days': max(ages),
            'average_days': sum(ages) / len(ages),
            'aged_30d_plus': aged_30,
            'aged_90d_plus': aged_90,
            'trust_score': round(trust_score, 1)
        }
    
    def inject_old_cookies(self, domain: str, age_days: int = 90):
        """
        Инжекция старых кук для повышения trust score
        
        Имитирует давнего пользователя, создавая куки с датой создания в прошлом.
        """
        old_time = time.time() - (age_days * 86400)
        
        # Стандартные трекинговые куки, которые сайты ожидают увидеть
        template_cookies = [
            ('_ga', f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(old_time)}'),
            ('_gid', f'GA1.2.{random.randint(100000000, 999999999)}.{int(old_time)}'),
            ('_fbp', f'fb.1.{int(old_time)}.{random.randint(1000000000, 9999999999)}'),
            ('_hjSession', f'{random.randint(100000, 999999)}'),
            ('_uetvid', f'{random.randint(1000000000000000, 9999999999999999)}'),
        ]
        
        for name, value in template_cookies:
            key = f"{domain}|{name}"
            if key not in self.cookies:
                record = CookieRecord(
                    name=name,
                    value=value,
                    domain=domain,
                    first_seen=old_time,
                    last_seen=time.time(),
                    hit_count=random.randint(5, 50)
                )
                self.cookies[key] = record
        
        self.save()
    
    def record_session(self, url: str, title: str = ""):
        """Запись в историю сессий"""
        self.session_history.append({
            'url': url,
            'title': title,
            'timestamp': time.time()
        })
        
        # Ограничиваем размер истории
        if len(self.session_history) > 1000:
            self.session_history = self.session_history[-500:]
        
        self.save()
    
    def get_session_graph(self) -> dict:
        """Граф сессий (посещённые домены и их связи)"""
        from collections import Counter
        domains = Counter()
        
        for entry in self.session_history:
            from urllib.parse import urlparse
            domain = urlparse(entry['url']).netloc
            domains[domain] += 1
        
        return {
            'total_sessions': len(self.session_history),
            'unique_domains': len(domains),
            'top_domains': domains.most_common(10)
        }
    
    def clear_expired(self):
        """Очистка истекших кук"""
        self.cookies = {
            k: v for k, v in self.cookies.items()
            if not v.is_expired
        }
        self.save()