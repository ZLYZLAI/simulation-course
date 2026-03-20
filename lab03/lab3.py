import tkinter as tk
import random

# Константы состояний
EMPTY = 0
TREE = 1
FIRE = 2
ASH = 3
WATER = 4

# Словарь цветов
COLORS = {
    EMPTY: "white",
    TREE: "#00FF00", 
    FIRE: "red",
    ASH: "black",    # Пепел
    WATER: "blue"    # Водная преграда
}

class ForestFireApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Клеточный автомат: Лесные пожары")
        
        # Настройки темной темы
        self.bg_color = "#2b2b2b"
        self.fg_color = "#e0e0e0"
        self.root.configure(bg=self.bg_color)
        
        # Параметры сетки: 60x60 с размером ячейки 10px = поле 60x60 = 3600 клеток
        self.rows = 60
        self.cols = 60
        self.cell_size = 10
        
        # Внутреннее состояние системы (сразу инициализируется пустотой)
        self.grid = [[EMPTY for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Массив для хранения ID прямоугольников (нужно для быстрого обновления цвета)
        self.rect_ids = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Переменные симуляции
        self.is_running = False
        self.tick_count = 0
        self.tree_count = 0
        self.fire_count = 0
        
        # Переменная для хранения текущего режима рисования мышки
        self.draw_mode = tk.IntVar(value=WATER) # Ставим воду
        
        # Запускаем сборку интерфейса
        self._build_ui()
        self._init_grid()
        
    def _build_ui(self):
        # Сборка инерфейса: разделим окно на левый фрейм (анимация) и правый (управление)
        
        # Левый фрейм для холста
        left_frame = tk.Frame(self.root, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.canvas = tk.Canvas(
            left_frame, 
            width=self.cols * self.cell_size, 
            height=self.rows * self.cell_size,
            bg="white", 
            highlightthickness=1, 
            highlightbackground="#555555"
        )
        self.canvas.pack()
        
        # Привязываем события мыши для интерактивного рисования
        self.canvas.bind("<Button-1>", self.on_mouse_draw)
        self.canvas.bind("<B1-Motion>", self.on_mouse_draw)
        
        # Правый фрейм для панелей управления
        right_frame = tk.Frame(self.root, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        # Блок статистики 
        stats_frame = tk.LabelFrame(right_frame, text="Статистика", bg=self.bg_color, fg=self.fg_color)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_ticks = tk.Label(stats_frame, text="Тики: 0", bg=self.bg_color, fg=self.fg_color)
        self.lbl_ticks.pack(anchor=tk.W, padx=5)
        
        self.lbl_trees = tk.Label(stats_frame, text="Деревья: 0", bg=self.bg_color, fg=self.fg_color)
        self.lbl_trees.pack(anchor=tk.W, padx=5)
        
        self.lbl_fires = tk.Label(stats_frame, text="Горящие деревья: 0", bg=self.bg_color, fg=self.fg_color)
        self.lbl_fires.pack(anchor=tk.W, padx=5)
        
        # Блок управления параметрами
        # Scale сразу показывает текущее числовое значение (параметр resolution и showvalue)
        params_frame = tk.LabelFrame(right_frame, text="Параметры среды", bg=self.bg_color, fg=self.fg_color)
        params_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(params_frame, text="Скорость (тиков/сек):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W)
        self.scale_speed = tk.Scale(params_frame, from_=1, to=60, orient=tk.HORIZONTAL, bg=self.bg_color, fg=self.fg_color, highlightthickness=0)
        self.scale_speed.set(10)
        self.scale_speed.pack(fill=tk.X)
        
        tk.Label(params_frame, text="Вероятность роста p (%):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W)
        self.scale_p = tk.Scale(params_frame, from_=0.1, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, bg=self.bg_color, fg=self.fg_color, highlightthickness=0)
        self.scale_p.set(1.0)
        self.scale_p.pack(fill=tk.X)
        
        tk.Label(params_frame, text="Вероятность молнии f (%):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W)
        self.scale_f = tk.Scale(params_frame, from_=0.01, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, bg=self.bg_color, fg=self.fg_color, highlightthickness=0)
        self.scale_f.set(0.1)
        self.scale_f.pack(fill=tk.X)
        
        # Дополнительные правила
        tk.Label(params_frame, text="Влажность (%):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W)
        self.scale_humidity = tk.Scale(params_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg=self.bg_color, fg=self.fg_color, highlightthickness=0)
        self.scale_humidity.set(30)
        self.scale_humidity.pack(fill=tk.X)
        
        tk.Label(params_frame, text="Температура (°C):", bg=self.bg_color, fg=self.fg_color).pack(anchor=tk.W)
        self.scale_temp = tk.Scale(params_frame, from_=-50, to=50, orient=tk.HORIZONTAL, bg=self.bg_color, fg=self.fg_color, highlightthickness=0)
        self.scale_temp.set(20)
        self.scale_temp.pack(fill=tk.X)
        
        # Блок инструментов
        tools_frame = tk.LabelFrame(right_frame, text="Инструменты кисти", bg=self.bg_color, fg=self.fg_color)
        tools_frame.pack(fill=tk.X, pady=5)
        
        tk.Radiobutton(tools_frame, text="Водная преграда", variable=self.draw_mode, value=WATER, bg=self.bg_color, fg=self.fg_color, selectcolor="#444444").pack(anchor=tk.W)
        tk.Radiobutton(tools_frame, text="Ластик (Удалить)", variable=self.draw_mode, value=EMPTY, bg=self.bg_color, fg=self.fg_color, selectcolor="#444444").pack(anchor=tk.W)
        
        # Блок кнопок
        buttons_frame = tk.Frame(right_frame, bg=self.bg_color)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = tk.Button(buttons_frame, text="Старт", command=self.toggle_simulation, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_start.pack(fill=tk.X, pady=2)
        
        tk.Button(buttons_frame, text="Очистить поле", command=self.clear_grid, bg="#f44336", fg="white").pack(fill=tk.X, pady=2)
        tk.Button(buttons_frame, text="Сгенерировать лес", command=self.generate_forest, bg="#2196F3", fg="white").pack(fill=tk.X, pady=2)

    def _init_grid(self):
        # Первичная отрисовка прямоугольников на холсте. Вызывается один раз
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = c * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                # Сохраняем ID каждого прямоугольника, чтобы потом просто менять им параметр fill.
                # Outline убираем (""), чтобы не было сетки (без неё вроде прикольнее)
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLORS[EMPTY], outline="")
                self.rect_ids[r][c] = rect

    def on_mouse_draw(self, event):
        # Обработчик рисования мышкой. Вычисляем координаты ячейки по координатам клика
        c = event.x // self.cell_size
        r = event.y // self.cell_size
        
        # Проверяем границы, чтобы не словить IndexError, если мышь выйдет за пределы холста
        if 0 <= r < self.rows and 0 <= c < self.cols:
            state = self.draw_mode.get()
            self.grid[r][c] = state
            self.canvas.itemconfig(self.rect_ids[r][c], fill=COLORS[state])

    def toggle_simulation(self):
        # Переключатель состояния симуляции (play/pause)
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_start.config(text="Пауза", bg="#FF9800")
            self.tick() # Запускаем цикл
        else:
            self.btn_start.config(text="Старт", bg="#4CAF50")

    def clear_grid(self):
        # Полная очистка сброс счетчиков
        self.is_running = False
        self.btn_start.config(text="Старт", bg="#4CAF50")
        self.tick_count = 0
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = EMPTY
                self.canvas.itemconfig(self.rect_ids[r][c], fill=COLORS[EMPTY])
        self.update_stats()

    def generate_forest(self):
        # Заполняем поле деревьями - воду не трогаем
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != WATER:
                    # 40% вероятность появления дерева при генерации
                    new_state = TREE if random.random() < 0.4 else EMPTY
                    self.grid[r][c] = new_state
                    self.canvas.itemconfig(self.rect_ids[r][c], fill=COLORS[new_state])
        self.update_stats()

    def update_stats(self):
        # Обновляет текстовые лейблы статистики
        self.lbl_ticks.config(text=f"Тики: {self.tick_count}")
        self.lbl_trees.config(text=f"Деревья: {self.tree_count}")
        self.lbl_fires.config(text=f"Горящие деревья: {self.fire_count}")

    def tick(self): 
        # Главный метод симуляции. Срабатывает каждый тик
        # Реализована схема, похожая на явный метод Эйлера: мы читаем старый слой (self.grid)
        # и пишем в новый слой (new_grid), чтобы изменения не влияли на соседей в рамках одного шага времени
        if not self.is_running:
            return

        # Считываем актуальные параметры с ползунков
        # Делим на 100, так как ползунки в процентах, а random() 0..1.
        p_grow = self.scale_p.get() / 100.0
        p_lightning = self.scale_f.get() / 100.0
        
        temp = self.scale_temp.get()
        humidity = self.scale_humidity.get()
        
        # Реализация дополнительных правил (температура и влажность)
        # Формируем вероятность возгорания дерева от горящего соседа.
        # Пусть базовая вероятность будет 0.6.
        # Высокая температура добавляет до +0.5 к вероятности. Низкая отнимает до -0.5.
        # Влажность отнимает от 0.0 до 1.0.
        # Таким образом, при влажности 100% огонь почти не распространяется, а при +50C жесть как да
        spread_prob = 0.6 + (temp / 100.0) - (humidity / 100.0)
        
        # Ограничиваем вероятность от 1% до 100%.
        spread_prob = max(0.01, min(1.0, spread_prob))

        # Создаем пустой массив для нового поколения
        new_grid = [[EMPTY for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Локальные счетчики для быстрой статистики в этом тике
        trees = 0
        fires = 0

        # Проходим по всем клеткам сетки
        for r in range(self.rows):
            for c in range(self.cols):
                current = self.grid[r][c]
                
                # 1. Вода остается водой и блокирует всё
                if current == WATER:
                    new_grid[r][c] = WATER
                    continue
                
                # 2. Пепел развеивается и становится пустотой на следующий тик
                elif current == ASH:
                    new_grid[r][c] = EMPTY
                    
                # 3. Горящее дерево сгорает и оставляет пепел
                elif current == FIRE:
                    new_grid[r][c] = ASH
                    
                # 4. Пустая клетка может зарости деревом с вероятностью p
                elif current == EMPTY:
                    if random.random() < p_grow:
                        new_grid[r][c] = TREE
                        trees += 1
                    else:
                        new_grid[r][c] = EMPTY
                        
                # 5. Дерево может загореться
                elif current == TREE:
                    # Ищем горящих соседей (окрестность Мура - 8 клеток)
                    burning_neighbors = 0
                    # Вложенные циклы для обхода соседей. Проверка `0 <= nr < self.rows` защищает от выхода за границы массива
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                if self.grid[nr][nc] == FIRE:
                                    burning_neighbors += 1

                    # Загорается от соседа (с учетом погодных условий)
                    if burning_neighbors > 0 and random.random() < spread_prob:
                        new_grid[r][c] = FIRE
                        fires += 1
                    # Загорается от молнии с вероятностью f, даже без соседей
                    elif random.random() < p_lightning:
                        new_grid[r][c] = FIRE
                        fires += 1
                    # Иначе дерево остается целым
                    else:
                        new_grid[r][c] = TREE
                        trees += 1

        # Оптимизация отрисовки: сравниваем старую сетку с новой, 
        # и дергаем функции canvas только если цвет поменялся
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != new_grid[r][c]:
                    self.canvas.itemconfig(self.rect_ids[r][c], fill=COLORS[new_grid[r][c]])
        
        # Обновляем состояние
        self.grid = new_grid
        self.tick_count += 1
        self.tree_count = trees
        self.fire_count = fires
        
        self.update_stats()

        # Планируем следующий вызов tick(). Переводим тики/сек в задержку в миллисекундах
        delay_ms = int(1000 / self.scale_speed.get())
        self.root.after(delay_ms, self.tick)

if __name__ == "__main__":
    # Точка входа приложения
    root = tk.Tk()
    app = ForestFireApp(root)
    # Запрещаем менять размер окна, чтобы не сбивалась сетка канваса
    root.resizable(False, False)
    root.mainloop()