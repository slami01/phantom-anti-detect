"""
Планировщик задач для массового парсинга
"""
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Task:
    """Задача на выполнение"""
    id: str
    url: str
    profile_id: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


class TaskScheduler:
    """
    Планировщик задач
    
    Функции:
    - Очередь задач
    - Параллельное выполнение с ограничением
    - Автоматические ретраи при ошибках
    - Сохранение результатов
    """
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.tasks: List[Task] = []
        self.running: Dict[str, asyncio.Task] = {}
        self._stop_flag = False
    
    def add_task(self, url: str, profile_id: str) -> Task:
        """Добавление задачи в очередь"""
        task = Task(
            id=f"task_{int(time.time())}_{len(self.tasks)}",
            url=url,
            profile_id=profile_id,
            created_at=datetime.now().isoformat()
        )
        self.tasks.append(task)
        return task
    
    def add_batch(self, urls: List[str], profile_ids: List[str]) -> List[Task]:
        """Пакетное добавление задач"""
        tasks = []
        for i, url in enumerate(urls):
            profile_id = profile_ids[i % len(profile_ids)] if profile_ids else "default"
            task = self.add_task(url, profile_id)
            tasks.append(task)
        return tasks
    
    async def run_all(self, executor: Callable, progress_callback: Callable = None):
        """
        Запуск всех pending задач
        
        Args:
            executor: async функция(task) -> result
            progress_callback: функция(task, status)
        """
        pending = [t for t in self.tasks if t.status == "pending"]
        
        # Ограничиваем параллелизм
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def run_task(task: Task):
            async with semaphore:
                if self._stop_flag:
                    return
                
                task.status = "running"
                task.started_at = datetime.now().isoformat()
                
                if progress_callback:
                    progress_callback(task, "started")
                
                try:
                    result = await executor(task)
                    task.status = "completed"
                    task.result = result
                    task.completed_at = datetime.now().isoformat()
                    
                    if progress_callback:
                        progress_callback(task, "completed")
                
                except Exception as e:
                    task.error = str(e)
                    task.retries += 1
                    
                    if task.retries < task.max_retries:
                        task.status = "pending"  # Вернём в очередь
                    else:
                        task.status = "failed"
                        task.completed_at = datetime.now().isoformat()
                    
                    if progress_callback:
                        progress_callback(task, "failed")
        
        # Запускаем все задачи
        coroutines = [run_task(t) for t in pending]
        await asyncio.gather(*coroutines, return_exceptions=True)
    
    def stop(self):
        """Остановка выполнения"""
        self._stop_flag = True
    
    def get_statistics(self) -> dict:
        """Статистика по задачам"""
        statuses = {}
        for task in self.tasks:
            statuses[task.status] = statuses.get(task.status, 0) + 1
        
        return {
            'total': len(self.tasks),
            'by_status': statuses,
            'completed': statuses.get('completed', 0),
            'failed': statuses.get('failed', 0),
            'pending': statuses.get('pending', 0),
            'running': statuses.get('running', 0),
        }
    
    def save(self, filepath: str):
        """Сохранение задач в файл"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'tasks': [asdict(t) for t in self.tasks]
            }, f, indent=2, ensure_ascii=False)
    
    def load(self, filepath: str):
        """Загрузка задач из файла"""
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        
        self.tasks = [Task(**t) for t in data.get('tasks', [])]