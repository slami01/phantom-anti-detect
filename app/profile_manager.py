"""
Менеджер профилей — эмуляция Multilogin/GoLogin/AdsPower
"""
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from app.fingerprint_engine import FingerprintEngine, Fingerprint
from app.cookie_jar import CookieJar


@dataclass
class BrowserProfile:
    """Профиль браузера (как в Multilogin/GoLogin)"""
    id: str
    name: str
    group: str = "Default"
    
    # Статус
    created_at: str = ""
    last_used: str = ""
    is_active: bool = True
    
    # Браузер
    browser_type: str = "chromium"  # chromium, firefox, webkit
    
    # Прокси
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    
    # Fingerprint
    fingerprint_template: str = "random"  # random, windows_desktop, macbook_pro, custom
    
    # Дополнительно
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = str(uuid.uuid4())


class ProfileManager:
    """
    Управление профилями браузеров
    
    Эмулирует функционал:
    - Multilogin: изолированные профили, fingerprint
    - GoLogin: облачное хранение, группы
    - AdsPower: массовое управление, теги
    """
    
    def __init__(self, base_dir: str = "profiles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, BrowserProfile] = {}
        
        self._load_profiles()
    
    def _load_profiles(self):
        """Загрузка всех профилей"""
        # Загружаем из profiles.json
        profiles_file = self.base_dir / "profiles.json"
        if profiles_file.exists():
            with open(profiles_file) as f:
                data = json.load(f)
            
            for p_data in data.get('profiles', []):
                profile = BrowserProfile(**p_data)
                self.profiles[profile.id] = profile
        
        # Обнаруживаем директории профилей
        for d in self.base_dir.iterdir():
            if d.is_dir() and d.name not in ['.', '..']:
                profile_id = d.name
                if profile_id not in self.profiles:
                    # Создаём запись для ненайденного профиля
                    self.profiles[profile_id] = BrowserProfile(
                        id=profile_id,
                        name=d.name,
                        created_at=datetime.fromtimestamp(
                            d.stat().st_mtime
                        ).isoformat()
                    )
        
        self._save_profiles_list()
    
    def _save_profiles_list(self):
        """Сохранение списка профилей"""
        with open(self.base_dir / "profiles.json", "w") as f:
            json.dump({
                'profiles': [asdict(p) for p in self.profiles.values()]
            }, f, indent=2)
    
    def create_profile(
        self,
        name: str,
        group: str = "Default",
        browser_type: str = "chromium",
        fingerprint_template: str = "random",
        proxy: dict = None
    ) -> BrowserProfile:
        """Создание нового профиля"""
        profile_id = str(uuid.uuid4())[:8]
        
        profile = BrowserProfile(
            id=profile_id,
            name=name,
            group=group,
            browser_type=browser_type,
            fingerprint_template=fingerprint_template
        )
        
        # Прокси
        if proxy:
            profile.proxy_host = proxy.get('host')
            profile.proxy_port = proxy.get('port')
            profile.proxy_username = proxy.get('username')
            profile.proxy_password = proxy.get('password')
        
        # Создаём директорию профиля
        profile_dir = self.base_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем fingerprint
        engine = FingerprintEngine(str(profile_dir))
        if fingerprint_template == "random":
            engine.generate_random()
        else:
            engine.from_template(fingerprint_template)
        
        # Инициализируем CookieJar
        jar = CookieJar(str(profile_dir))
        jar.save()
        
        self.profiles[profile_id] = profile
        self._save_profiles_list()
        
        return profile
    
    def delete_profile(self, profile_id: str) -> bool:
        """Удаление профиля"""
        if profile_id not in self.profiles:
            return False
        
        # Удаляем директорию
        profile_dir = self.base_dir / profile_id
        if profile_dir.exists():
            shutil.rmtree(profile_dir)
        
        del self.profiles[profile_id]
        self._save_profiles_list()
        return True
    
    def duplicate_profile(self, profile_id: str, new_name: str) -> Optional[BrowserProfile]:
        """Дублирование профиля (с новым fingerprint)"""
        if profile_id not in self.profiles:
            return None
        
        original = self.profiles[profile_id]
        new_profile = self.create_profile(
            name=new_name,
            group=original.group,
            browser_type=original.browser_type
        )
        
        # Копируем куки и хранилища
        src_dir = self.base_dir / profile_id
        dst_dir = self.base_dir / new_profile.id
        
        if (src_dir / "cookies.json").exists():
            shutil.copy(src_dir / "cookies.json", dst_dir / "cookies.json")
        
        # Обновляем данные
        new_profile.fingerprint_template = original.fingerprint_template
        new_profile.proxy_host = original.proxy_host
        new_profile.proxy_port = original.proxy_port
        new_profile.proxy_username = original.proxy_username
        new_profile.proxy_password = original.proxy_password
        new_profile.tags = original.tags.copy()
        
        self._save_profiles_list()
        return new_profile
    
    def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Получить профиль по ID"""
        return self.profiles.get(profile_id)
    
    def get_all_profiles(self) -> List[BrowserProfile]:
        """Все профили"""
        return list(self.profiles.values())
    
    def get_profiles_by_group(self, group: str) -> List[BrowserProfile]:
        """Профили по группе"""
        return [p for p in self.profiles.values() if p.group == group]
    
    def get_profile_fingerprint(self, profile_id: str) -> Optional[Fingerprint]:
        """Загрузить отпечаток профиля"""
        if profile_id not in self.profiles:
            return None
        
        profile_dir = self.base_dir / profile_id
        engine = FingerprintEngine(str(profile_dir))
        return engine.load()
    
    def get_profile_cookies(self, profile_id: str) -> CookieJar:
        """Загрузить куки профиля"""
        profile_dir = self.base_dir / profile_id
        return CookieJar(str(profile_dir))
    
    def bulk_create(self, count: int, name_prefix: str, **kwargs) -> List[BrowserProfile]:
        """Массовое создание профилей"""
        profiles = []
        for i in range(count):
            profile = self.create_profile(
                name=f"{name_prefix}_{i+1}",
                **kwargs
            )
            profiles.append(profile)
        return profiles
    
    def import_from_multilogin(self, filepath: str) -> List[BrowserProfile]:
        """Импорт профилей из Multilogin"""
        with open(filepath) as f:
            data = json.load(f)
        
        imported = []
        for entry in data:
            profile = self.create_profile(
                name=entry.get('name', 'Imported'),
                fingerprint_template='custom'
            )
            imported.append(profile)
        
        return imported
    
    def export_to_json(self, profile_id: str, output_path: str):
        """Экспорт профиля в JSON (для переноса)"""
        profile = self.get_profile(profile_id)
        if not profile:
            return
        
        profile_dir = self.base_dir / profile_id
        export_data = {
            'profile': asdict(profile),
            'cookies': {},
            'fingerprint': {}
        }
        
        # Куки
        if (profile_dir / "cookies.json").exists():
            with open(profile_dir / "cookies.json") as f:
                export_data['cookies'] = json.load(f)
        
        # Fingerprint
        if (profile_dir / "fingerprint.json").exists():
            with open(profile_dir / "fingerprint.json") as f:
                export_data['fingerprint'] = json.load(f)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)