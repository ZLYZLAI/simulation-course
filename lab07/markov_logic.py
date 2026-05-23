"""
Единица времени = 1 день. Один шаг модели = один день.
Математическая основа:
    - Матрица переходных вероятностей P (стохастическая матрица):
        P[i][j] >= 0 - вероятность перехода из состояния i в j за один день
        sum_j(P[i][j]) = 1 для каждой строки i  (строки суммируются в 1)
    - На каждом шаге: X(t+1) выбирается согласно строке P[X(t)]
    - Стационарное распределение pi: pi * P = pi, sum(pi) = 1
"""

import numpy as np
import csv
import os
from datetime import datetime


# =============================
# Основной класс модели

class MarkovWeatherModel:
    """
    Дискретная цепь Маркова (ДЦМ) для трёхсостоянной модели погоды.

    Каждый шаг симуляции = один день.
    Переход в следующее состояние определяется строкой P[current_state].
    """

    # Названия состояний (используются для отображения и экспорта)
    STATE_NAMES = ['Ясно', 'Облачно', 'Пасмурно']

    # Количество состояний
    N = 3

    def __init__(self):
        # P[i][j] = вероятность перейти из состояния i в состояние j за один день.
        # Каждая строка суммируется в 1 (стохастическая матрица).
        #
        # Строка 0 (Ясно):     остаться ясным  - 60%, стать облачным - 30%, пасмурным - 10%
        # Строка 1 (Облачно):  стать ясным     - 40%, остаться       - 20%, пасмурным - 40%
        # Строка 2 (Пасмурно): стать ясным     - 10%, облачным       - 40%, остаться  - 50%
        self.P = np.array([
            [0.6, 0.3, 0.1],
            [0.4, 0.2, 0.4],
            [0.1, 0.4, 0.5],
        ], dtype=float)

        # Инициализирую переменные состояния
        self.reset()

    # ----------------------------------
    # Управление матрицей переходов P

    def set_transition_matrix(self, P):
        """
        Устанавливаю новую матрицу переходных вероятностей.
        Параметры:
            P: массив 3x3 с вероятностями переходов.
               Строки автоматически нормируются так, чтобы sum(P[i]) = 1.
        Отрицательные значения обнуляются перед нормировкой.
        """
        mat = np.array(P, dtype=float)

        # Вероятности не могут быть отрицательными
        mat = np.maximum(mat, 0.0)

        # Нормирую каждую строку так, чтобы сумма = 1.
        # Без нормировки sum(P[i]) != 1 вызовет ошибку в np.random.choice.
        row_sums = mat.sum(axis=1, keepdims=True)
        # Защита от нулевой строки (все элементы = 0) - делаем равномерную
        row_sums[row_sums < 1e-12] = 1.0
        self.P = mat / row_sums

    def get_P_display(self):
        """
        Возвращаю копию матрицы P для отображения в GUI.
        Копия нужна, чтобы внешний код не изменял внутреннее состояние.
        """
        return self.P.copy()

    # -----------------------------
    # Управление симуляцией

    def reset(self):
        """
        Сбрасываю симуляцию в начальное состояние.
        Начинаю с состояния 0 (Ясно), обнуляю все счётчики и историю.
        """
        # Текущее состояние: начинаю с "Ясно" (индекс 0)
        self.current_state = 0

        # Номер текущего дня (целое число, начинается с 0 до первого шага)
        self.day = 0

        # История: список пар (номер_дня, состояние).
        # После k шагов в списке k записей: [(1, s1), (2, s2), ..., (k, sk)].
        self.state_history = []

        # Количество дней, проведённых в каждом состоянии.
        # state_counts[i] += 1 каждый раз, когда новый день приходит в состояние i.
        self.state_counts = np.zeros(self.N, dtype=int)

        # Бегущие доли для графика сходимости.
        # running_fractions[i][k] = state_counts[i] / day после k-го шага.
        # По закону больших чисел эти значения сходятся к pi[i].
        self.running_fractions = [[] for _ in range(self.N)]

    # -----------------------------
    # Один шаг симуляции

    def step(self):
        """
        Выполняю один шаг ДЦМ - один день.
        Алгоритм:
        1. Текущее состояние = i.
        2. Следующее состояние j выбирается случайно согласно строке P[i]:
               P(X(t+1) = j | X(t) = i) = P[i][j]
        3. Увеличиваю счётчик дней, обновляю историю и статистику.
        4. Устанавливаю current_state = j.

        Это ключевое свойство марк: следующее состояние зависит только от текущего и не зависит от предыстории.

        Возвращает:
            int: следующее состояние (индекс 0, 1 или 2)
        """
        i = self.current_state

        # Строка P[i] задаёт вероятности переходов из состояния i.
        # np.random.choice выбирает индекс j с вероятностью P[i][j].
        probs = self.P[i]
        next_state = int(np.random.choice(self.N, p=probs))

        # Увеличиваю счётчик дней (каждый вызов step() = один день)
        self.day += 1

        # Записываю текущий день и новое состояние в историю
        self.state_history.append((self.day, next_state))

        # Засчитываю день в счётчик нового состояния
        self.state_counts[next_state] += 1

        # Обновляю бегущие доли: running_fractions[k] = state_counts[k] / day
        # Используется для графика сходимости - видно, как доли стремятся к pi[k].
        for k in range(self.N):
            frac = self.state_counts[k] / self.day
            self.running_fractions[k].append(frac)

        # Переходю в новое состояние
        self.current_state = next_state

        return next_state

    # ---------------------------
    # Математические расчёты

    def compute_stationary_distribution(self):
        """
        Вычисляю теоретическое стационарное распределение pi для матрицы P.
        Определение и смысл:
        Стационарное (равновесное) распределение pi удовлетворяет:
            pi * P = pi   (собственный вектор матрицы P^T для лямбда = 1)
            sum(pi) = 1   (условие нормировки)

        Физический смысл pi[i]:
            Доля дней, которую цепь в долгосрочной перспективе проводит в состоянии i.
            При day -> infinity:
                state_counts[i] / day  --->  pi[i].
            Это то, что я показываю на графике сходимости.

        Метод решения:
        Из pi * P = pi:
            pi * (P - I) = 0
            (P - I)^T * pi^T = 0   (то же, в столбцовой записи)

        Строю систему A * pi_col = b:
            A = (P - I)^T  с заменой последней строки на [1, 1, 1]
            b = [0, 0, ..., 0, 1]   (условие нормировки в последнем уравнении)

        Решаю LU-разложением через numpy.linalg.solve.

        Возвращает:
            np.ndarray: вектор pi длины N с pi[i] >= 0 и sum(pi) = 1
        """
        # Матрица системы: (P - I)^T
        A = (self.P - np.eye(self.N)).T.copy()

        # Правая часть (нулевая, кроме последней компоненты)
        b = np.zeros(self.N)

        # Заменяю последнюю строку A на условие нормировки: pi[0]+pi[1]+pi[2] = 1
        A[-1, :] = 1.0
        b[-1]    = 1.0

        try:
            pi = np.linalg.solve(A, b)

            # Исправляю возможные маленькие отрицательные значения (численные ошибки)
            pi = np.maximum(pi, 0.0)

            # Перенормирую на случай накопленных ошибок
            s = pi.sum()
            if s > 1e-12:
                pi /= s
            else:
                pi = np.ones(self.N) / self.N  # запасной вариант

        except np.linalg.LinAlgError:
            # Вырожденная матрица - возвращаю равномерное распределение
            pi = np.ones(self.N) / self.N

        return pi

    def get_empirical_fractions(self):
        """
        Возвращаю вектор эмпирических долей дней в каждом состоянии.
        empirical[i] = state_counts[i] / day

        По эргодической теореме для ДЦМ:
            empirical[i]  ->  pi[i]  при day -> infinity.
        Именно эта сходимость показана на третьем графике.

        Возвращает:
            np.ndarray: вектор длины N, каждый элемент в [0,1], сумма = 1 (или нули если нет данных)
        """
        if self.day == 0:
            return np.zeros(self.N)
        return self.state_counts / self.day

    # -----------------------
    # Сохранение в CSV

    def save_to_csv(self, folder='output'):
        """
        Сохраняю всю статистику симуляции в три CSV-файла.
        Содержимое файлов:
            1. history_*.csv  - история состояний по дням (день, состояние)
            2. stats_*.csv    - сводная статистика (дней в состоянии, эмпирика vs теория)
            3. p_matrix_*.csv - матрица переходов P и стационарное распределение
        """
        # Создаю папку, если она не существует
        os.makedirs(folder, exist_ok=True)

        # Временная метка для уникальности имён файлов
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        created = []  # список созданных файлов

        # Вычисляю статистику один раз
        empirical  = self.get_empirical_fractions()
        stationary = self.compute_stationary_distribution()

        # Файл 1: История состояний по дням
        history_path = os.path.join(folder, f'history_{ts}.csv')
        with open(history_path, 'w', newline='', encoding='utf-8-sig') as f:
            # utf-8-sig - BOM-маркер для корректного открытия в Excel
            w = csv.writer(f)
            w.writerow(['День', 'Состояние (имя)', 'Состояние (код 1-3)'])
            for (day, state) in self.state_history:
                w.writerow([
                    day,
                    self.STATE_NAMES[state],
                    state + 1   # 1-based: 1=Ясно, 2=Облачно, 3=Пасмурно
                ])
        created.append(os.path.abspath(history_path))

        # Файл 2: Сводная статистика
        stats_path = os.path.join(folder, f'stats_{ts}.csv')
        with open(stats_path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)

            # Общая информация
            w.writerow(['=== Общая информация ==='])
            w.writerow(['Всего дней', self.day])
            w.writerow([])

            # Сравниваю эмпирику с теоретическим стационарным распределением
            w.writerow(['=== Распределение дней по состояниям ==='])
            w.writerow([
                'Состояние',
                'Дней',
                'Эмпирич. доля',
                'Теорет. доля (стацион.)',
                '|Отклонение|'
            ])
            for i in range(self.N):
                deviation = abs(empirical[i] - stationary[i])
                w.writerow([
                    self.STATE_NAMES[i],
                    int(self.state_counts[i]),
                    f'{empirical[i]:.6f}',
                    f'{stationary[i]:.6f}',
                    f'{deviation:.6f}'
                ])
        created.append(os.path.abspath(stats_path))

        # Файл 3: Матрица переходов P и стационарное распределение
        pmat_path = os.path.join(folder, f'p_matrix_{ts}.csv')
        with open(pmat_path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)

            # Матрица P
            w.writerow(['P (строка=откуда, столбец=куда)'] + self.STATE_NAMES)
            for i in range(self.N):
                row = [self.STATE_NAMES[i]] + [f'{self.P[i, j]:.6f}' for j in range(self.N)]
                w.writerow(row)
            w.writerow([])

            # Стационарное распределение рядом с матрицей для удобства
            w.writerow(['Стационарное распределение pi (теория):'])
            w.writerow(['pi_' + name for name in self.STATE_NAMES])
            w.writerow([f'{stationary[i]:.6f}' for i in range(self.N)])
        created.append(os.path.abspath(pmat_path))

        return created
