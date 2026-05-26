"""
Эмулятор человеческого поведения
Имитирует: мышь (кривые Безье), скролл (инерция), печать (ошибки), паузы
"""
import asyncio
import random
import math
import time
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class HumanConfig:
    """Конфигурация поведения человека"""
    # Мышь
    mouse_speed: float = 1.0  # Множитель скорости (1.0 = нормально)
    jitter_intensity: float = 1.5  # Интенсивность дрожания
    overshoot_probability: float = 0.15  # Вероятность промахнуться
    
    # Скролл
    scroll_speed: float = 1.0
    scroll_inertia: bool = True
    
    # Печать
    typing_speed: float = 1.0  # символов в секунду (~8 для нормального)
    typo_rate: float = 0.04  # 4% ошибок
    typo_correction_delay: Tuple[float, float] = (0.3, 0.8)  # задержка перед исправлением
    
    # Паузы
    reading_pause: Tuple[float, float] = (2.0, 8.0)  # пауза "чтения"
    micro_pause: Tuple[float, float] = (0.05, 0.25)  # микро-паузы
    action_gap: Tuple[float, float] = (0.1, 0.6)  # пауза между действиями


class HumanEmulator:
    """
    Эмулятор человека для Playwright
    
    Особенности:
    - Движения мыши по кубическим кривым Безье (не по прямой)
    - Микро-дрожание руки (нормальное распределение)
    - Овершутинг (промахивание мимо цели)
    - Скролл с инерцией и переменной скоростью
    - Печать текста с реалистичными ошибками и автокоррекцией
    - Случайные паузы разной длительности
    - Эмуляция "зависания" (человек задумался)
    """
    
    # Раскладки клавиатуры для эмуляции опечаток
    QWERTY_NEIGHBOURS = {
        'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx',
        'e': 'wrsdf', 'f': 'drtgc', 'g': 'ftyhbv', 'h': 'gyujnb',
        'i': 'ujklo', 'j': 'hyuikmn', 'k': 'jiolm', 'l': 'kop',
        'm': 'njk', 'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
        'q': 'aw', 'r': 'edft', 's': 'awedxza', 't': 'rfghy',
        'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
        'y': 'tghu', 'z': 'asx',
    }
    
    def __init__(self, config: HumanConfig = None):
        self.config = config or HumanConfig()
        self._last_mouse_pos = (0, 0)
        self._action_history = []
    
    async def move_mouse(
        self, page, target_x: int, target_y: int,
        duration: float = None
    ):
        """
        Перемещение мыши к целевой точке по кривой Безье
        
        Человек не водит мышью по прямой — траектория изогнута,
        скорость неравномерна, есть микро-дрожание.
        """
        # Определяем начальную позицию (где мышь сейчас)
        try:
            pos = await page.evaluate("() => ({x: window.mouseX || 100, y: window.mouseY || 100})")
            start_x, start_y = pos['x'], pos['y']
        except:
            start_x = random.randint(100, 300)
            start_y = random.randint(100, 300)
        
        # Добавляем овершутинг (15% шанс промахнуться и скорректироваться)
        overshoot = random.random() < self.config.overshoot_probability
        if overshoot:
            overshoot_x = target_x + random.randint(-30, 30)
            overshoot_y = target_y + random.randint(-20, 20)
        else:
            overshoot_x, overshoot_y = target_x, target_y
        
        # Контрольные точки для кубической кривой Безье
        cp1_x = start_x + random.randint(-200, 200)
        cp1_y = start_y + random.randint(-100, 100)
        cp2_x = overshoot_x + random.randint(-150, 150)
        cp2_y = overshoot_y + random.randint(-150, 150)
        
        # Количество шагов (больше = плавнее)
        distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
        steps = max(20, int(distance / 3))
        
        # Автоматическая длительность на основе расстояния и скорости
        if duration is None:
            duration = (distance / 1000) / self.config.mouse_speed
            duration = max(0.1, min(2.0, duration))
        
        step_delay = duration / steps
        
        for i in range(steps + 1):
            t = i / steps
            
            # Кубическая кривая Безье
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + \
                3*(1-t)*t**2 * cp2_x + t**3 * overshoot_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + \
                3*(1-t)*t**2 * cp2_y + t**3 * overshoot_y
            
            # Микро-дрожание (нормальное распределение)
            jitter_x = random.gauss(0, self.config.jitter_intensity)
            jitter_y = random.gauss(0, self.config.jitter_intensity)
            
            final_x = x + jitter_x
            final_y = y + jitter_y
            
            await page.mouse.move(final_x, final_y)
            
            # Сохраняем позицию
            await page.evaluate(
                f"window.mouseX = {final_x}; window.mouseY = {final_y};"
            )
            
            # Неравномерная задержка (ускорение в середине, замедление в начале/конце)
            progress_factor = 2 * abs(t - 0.5)  # 1 на краях, 0 в середине
            delay = step_delay * (0.5 + progress_factor)
            await asyncio.sleep(delay)
        
        # Если был овершутинг — возвращаемся к цели
        if overshoot:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await page.mouse.move(target_x, target_y, steps=random.randint(3, 7))
            await page.evaluate(
                f"window.mouseX = {target_x}; window.mouseY = {target_y};"
            )
    
    async def click(self, page, x: int, y: int, button: str = 'left'):
        """Человеческий клик с подводом мыши"""
        # Подводим мышь к цели
        await self.move_mouse(page, x, y)
        
        # Микро-пауза перед кликом (человек прицеливается)
        await self._pause(*self.config.micro_pause)
        
        # Клик
        await page.mouse.click(x, y, button=button)
        
        # Запись в историю
        self._action_history.append({
            'action': 'click',
            'x': x, 'y': y,
            'time': time.time()
        })
        
        # Пауза после клика
        await self._pause(*self.config.action_gap)
    
    async def type_text(self, page, text: str, selector: str = None):
        """
        Эмуляция человеческой печати с ошибками
        
        Особенности:
        - Переменная скорость (логи нормальное распределение задержек)
        - Опечатки (замена на соседние клавиши QWERTY)
        - Автокоррекция (backspace + повтор)
        - Паузы на "подумать" перед сложными словами
        """
        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.click()
                await self._pause(0.2, 0.5)
        
        for i, char in enumerate(text):
            # Пауза перед длинными словами (человек думает)
            if i > 0 and text[i-1] == ' ' and len(text[i:].split()[0]) > 8:
                await self._pause(0.2, 0.6)
            
            # Логнормальное распределение скорости печати
            base_delay = 1.0 / (8 * self.config.typing_speed)  # ~8 символов/сек
            delay = random.lognormvariate(base_delay, base_delay * 0.3)
            delay = max(0.03, min(0.5, delay))
            
            # Опечатка?
            actual_char = char
            if char.isalpha() and random.random() < self.config.typo_rate:
                # Замена на соседнюю клавишу
                neighbours = self.QWERTY_NEIGHBOURS.get(char.lower(), '')
                if neighbours:
                    actual_char = random.choice(neighbours)
                    if char.isupper():
                        actual_char = actual_char.upper()
                    
                    # Печатаем ошибочный символ
                    await page.keyboard.type(actual_char, delay=int(delay * 1000))
                    
                    # Задержка перед исправлением (человек заметил ошибку)
                    await self._pause(*self.config.typo_correction_delay)
                    
                    # Исправляем
                    await page.keyboard.press('Backspace')
                    await self._pause(0.05, 0.15)
            
            # Печатаем правильный символ
            await page.keyboard.type(char, delay=int(delay * 1000))
        
        self._action_history.append({
            'action': 'type',
            'text': text,
            'time': time.time()
        })
    
    async def scroll(self, page, distance: int, direction: str = 'down'):
        """
        Человеческий скролл с инерцией
        """
        if direction == 'up':
            distance = -distance
        
        # Разбиваем на шаги с переменной скоростью
        steps = random.randint(8, 20)
        sign = 1 if distance > 0 else -1
        
        for i in range(steps):
            # Инерция: ускорение в начале, замедление в конце
            t = i / steps
            if t < 0.3:
                # Ускорение
                factor = t / 0.3 * 0.8
            elif t > 0.7:
                # Замедление
                factor = (1 - t) / 0.3 * 0.8
            else:
                # Равномерно
                factor = 0.8
            
            step_distance = (abs(distance) / steps) * factor * self.config.scroll_speed
            step_distance = max(10, step_distance) * sign
            
            await page.mouse.wheel(0, step_distance)
            await asyncio.sleep(random.uniform(0.01, 0.06))
    
    async def hover(self, page, x: int, y: int, duration: float = None):
        """Наведение мыши на элемент (hover)"""
        await self.move_mouse(page, x, y, duration)
        await self._pause(0.3, 1.0)  # Задержка как при чтении
    
    async def random_micro_actions(self, page, count: int = 3):
        """Случайные микро-действия (шевеление мышью, микро-скроллы)"""
        for _ in range(count):
            action = random.choice(['wiggle', 'micro_scroll', 'pause'])
            
            if action == 'wiggle':
                # Небольшое движение мышью
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await self.move_mouse(page, x, y, duration=random.uniform(0.3, 1.0))
            
            elif action == 'micro_scroll':
                await self.scroll(page, random.randint(-100, 200))
            
            elif action == 'pause':
                await self._pause(0.5, 2.0)
    
    async def simulate_reading(self, page):
        """Эмуляция чтения страницы (скролл + паузы)"""
        # Скроллим вниз порциями
        for _ in range(random.randint(2, 5)):
            await self.scroll(page, random.randint(200, 500))
            # "Читаем"
            await self._pause(*self.config.reading_pause)
            # Иногда скроллим обратно (перечитываем)
            if random.random() < 0.2:
                await self.scroll(page, random.randint(50, 150), 'up')
                await self._pause(1.0, 2.0)
    
    async def human_form_fill(self, page, form_data: dict):
        """
        Заполнение формы как человек:
        - Перемещение между полями мышью (не Tab)
        - Паузы между полями
        - Иногда возврат к предыдущему полю
        """
        fields = list(form_data.items())
        
        for i, (selector, value) in enumerate(fields):
            # Клик по полю
            element = await page.query_selector(selector)
            if element:
                box = await element.bounding_box()
                if box:
                    await self.click(
                        page,
                        box['x'] + box['width'] / 2,
                        box['y'] + box['height'] / 2
                    )
            
            # Печать значения
            await self.type_text(page, value)
            
            # Пауза между полями (кроме последнего)
            if i < len(fields) - 1:
                await self._pause(0.5, 2.0)
            
            # Иногда возвращаемся и что-то меняем
            if random.random() < 0.1 and i > 0:
                prev_selector, prev_value = fields[i-1]
                prev_element = await page.query_selector(prev_selector)
                if prev_element:
                    box = await prev_element.bounding_box()
                    if box:
                        await self.click(
                            page,
                            box['x'] + box['width'] / 2,
                            box['y'] + box['height'] / 2
                        )
                        await self._pause(0.5, 1.0)
    
    async def _pause(self, min_sec: float, max_sec: float):
        """Случайная пауза"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    def get_action_log(self) -> list:
        """Получить историю действий"""
        return self._action_history