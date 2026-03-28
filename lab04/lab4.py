import tkinter as tk
from tkinter import ttk
import random
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

#  БАЗОВЫЙ ДАТЧИК СЛУЧАЙНЫХ ЧИСЕЛ (ЛКГ)
class BasicRNG:
    def __init__(self, seed=42):
        # Инициализируем начальное значение (seed)
        self.state = seed
        
        # Задаем константы для линейного конгруэнтного генератора (LCG)
        self.a = 1664525        # Множитель
        self.c = 1013904223     # Приращение
        self.m = 2**32          # Модуль

    def next(self):
        # Сама формула генератора: X_next = (a * X_prev + c) mod m
        self.state = (self.a * self.state + self.c) % self.m
        # Нам нужны числа в диапазоне [0, 1), поэтому делим на m
        return self.state / self.m

# МАТЕМАТИЧЕСКАЯ СТАТИСТИКА
def calculate_mean(data):
    # Выборочное среднее: сумма всех элементов деленная на их количество
    return sum(data) / len(data)

def calculate_variance(data, mean):
    # Выборочная дисперсия
    # Считаем сумму квадратов отклонений от среднего
    n = len(data)
    sum_sq_diff = sum((x - mean) ** 2 for x in data)
    return sum_sq_diff / (n - 1)

# ОСНОВНАЯ ЛОГИКА И ГЕНЕРАЦИЯ ВЫБОРОК
def run_experiment():
    N = 100000 # Размер выборки
    
    # Теоретические значения для равномерного распределения на [0, 1]
    # Среднее = (a+b)/2 = (0+1)/2 = 0.5
    # Дисперсия = (b-a)^2 / 12 = 1/12
    theoretical_mean = 0.5
    theoretical_var = 1 / 12

    # Создаем кастомный генератор
    my_rng = BasicRNG(seed=12345)
    
    # Генерируем выборки
    # Выборка нашего датчика
    sample_custom = [my_rng.next() for _ in range(N)]
    # Выборка встроенного в Python датчика
    sample_builtin = [random.random() for _ in range(N)]

    # Считаем статистику для нашего генератора
    mean_custom = calculate_mean(sample_custom)
    var_custom = calculate_variance(sample_custom, mean_custom)
    
    # Считаем статистику для встроенного генератора
    mean_builtin = calculate_mean(sample_builtin)
    var_builtin = calculate_variance(sample_builtin, mean_builtin)

    # Вычисляем разницу (ошибку) между полученными результатами и теорией
    # Берём по модулю, чтобы на графике было наглядно видно именно величину отклонения
    diff_mean_custom = abs(mean_custom - theoretical_mean)
    diff_var_custom = abs(var_custom - theoretical_var)
    
    diff_mean_builtin = abs(mean_builtin - theoretical_mean)
    diff_var_builtin = abs(var_builtin - theoretical_var)

    return {
        "custom": (mean_custom, var_custom, diff_mean_custom, diff_var_custom),
        "builtin": (mean_builtin, var_builtin, diff_mean_builtin, diff_var_builtin),
        "theory": (theoretical_mean, theoretical_var)
    }

# ПОЛЬЗОВАТЕЛЬСКИЙ ИНТЕРФЕЙС
def create_gui():
    # Проводим эксперимент и получаем все циферки
    results = run_experiment()

    # Создаем главное окно приложения
    root = tk.Tk()
    root.title("Анализ датчиков случайных чисел")
    root.geometry("800x700") # Размер окошка по умолчанию

    # ФУНКЦИЯ ЗАКРЫТИЯ
    def on_closing():
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    # Создание таблицы
    columns = ("generator", "mean", "variance", "diff_mean", "diff_var")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=3)
    
    # Настраиваем заголовки колонок
    tree.heading("generator", text="Датчик")
    tree.heading("mean", text="Выборочное среднее")
    tree.heading("variance", text="Дисперсия")
    tree.heading("diff_mean", text="Отклонение (Среднее)")
    tree.heading("diff_var", text="Отклонение (Дисперсия)")

    # Настраиваем ширину колонок для аккуратности
    for col in columns:
        tree.column(col, width=150, anchor="center")

    # Вставляем данные в таблицу (6 знаков после запятой, чтобы влезло)
    # 1 Теория
    tree.insert("", "end", values=(
        "Теоретический (Идеал)", 
        f"{results['theory'][0]:.6f}", 
        f"{results['theory'][1]:.6f}", 
        "-", "-"
    ))
    # 2 Наш ЛКГ
    tree.insert("", "end", values=(
        "Базовый датчик (ЛКГ)", 
        f"{results['custom'][0]:.6f}", 
        f"{results['custom'][1]:.6f}", 
        f"{results['custom'][2]:.6f}", 
        f"{results['custom'][3]:.6f}"
    ))
    # 3 Встроенный в Python
    tree.insert("", "end", values=(
        "Встроенный (Python)", 
        f"{results['builtin'][0]:.6f}", 
        f"{results['builtin'][1]:.6f}", 
        f"{results['builtin'][2]:.6f}", 
        f"{results['builtin'][3]:.6f}"
    ))

    # Упаковываем таблицу в верхнюю часть окна с отступами
    tree.pack(pady=20, padx=10, fill="x")

    # Построение графика
    # Создаем фигуру matplotlib
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Подготавливаем данные для графика.
    labels = [
        'Ср. значение (Базовый)', 'Ср. значение (Python)', 
        'Дисперсия (Базовый)', 'Дисперсия (Python)'
    ]
    # Собираем отклонения в один список
    diffs = [
        results['custom'][2], results['builtin'][2],
        results['custom'][3], results['builtin'][3]
    ]
    # Раскрас
    colors = ['#1f77b4', '#ff7f0e', '#1f77b4', '#ff7f0e']

    # Строим горизонтальную столбчатую диаграмму
    bars = ax.barh(labels, diffs, color=colors)
    ax.set_xlabel('Абсолютное отклонение от теории')
    ax.set_title('Сравнение точности генераторов (меньше отклонение = лучше)')
    ax.grid(axis='x', linestyle='--', alpha=0.7) # Добавим сетку для удобства чтения
    fig.tight_layout()
    # Встраиваем график matplotlib в окно tkinter
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    root.mainloop()

if __name__ == "__main__":
    create_gui()