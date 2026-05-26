#!/usr/bin/env python3
"""
Установщик Phantom Anti-Detect Browser Framework
"""
import subprocess
import sys
import os
from pathlib import Path

def run(cmd, desc):
    print(f"\n[+] {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Ошибка: {result.stderr}")
        return False
    print(f"[✓] {desc} - OK")
    return True

def main():
    print("=" * 60)
    print("Phantom Anti-Detect Browser Framework - Установка")
    print("=" * 60)

    # 1. Установка Python-зависимостей
    run(f"{sys.executable} -m pip install --upgrade pip", "Обновление pip")
    run(f"{sys.executable} -m pip install -r requirements.txt", "Установка зависимостей")

    # 2. Установка Playwright браузеров
    run("playwright install chromium", "Установка Chromium (Playwright)")
    run("playwright install firefox", "Установка Firefox (Playwright)")

    # 3. Создание структуры папок
    dirs = [
        "profiles/default",
        "profiles/default/indexeddb",
        "proxies",
        "logs",
        "exports"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"[✓] Создана директория: {d}")

    # 4. Создание конфигов по умолчанию
    import json

    # Профиль по умолчанию
    default_profile = {
        "name": "default",
        "os": "Windows 10",
        "browser": "Chrome 124",
        "screen": {"width": 1920, "height": 1080},
        "timezone": "Europe/Moscow",
        "locale": "ru-RU",
        "language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "platform": "Win32",
        "hardware_concurrency": 16,
        "device_memory": 16,
        "webgl_vendor": "NVIDIA Corporation",
        "webgl_renderer": "NVIDIA GeForce RTX 4070/PCIe/SSE2",
        "audio_vendor": "Google Inc.",
        "fonts": ["Arial", "Times New Roman", "Courier New", "Verdana", "Georgia"],
        "canvas_noise": 0.003,
        "webrtc_ips": [],
        "do_not_track": False,
        "cookies_enabled": True,
        "proxy": None
    }

    with open("profiles/default/fingerprint.json", "w") as f:
        json.dump(default_profile, f, indent=2)

    # Пустой пул прокси
    with open("proxies/pool.json", "w") as f:
        json.dump({"proxies": []}, f, indent=2)

    print("\n" + "=" * 60)
    print("[✓] Установка завершена!")
    print("[>] Запуск: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    main()