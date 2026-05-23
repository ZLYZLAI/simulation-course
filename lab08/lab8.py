import tkinter as tk
from tkinter import ttk, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import poisson


# ==========
# Логика

def generate_poisson_stream(lam, T1):
    """
    Моделирует простейший пуассоновский поток на интервале [0, T1].

    Ключевое свойство простейшего потока: интервалы между событиями имеют экспоненциальное распределение с параметром lambda.

    Возвращает массив моментов времени всех событий в [0, T1].
    """
    events = []
    t = 0.0
    while t < T1:
        # Генерирует интервал до следующего события: tau ~ Exp(lambda)
        # scale = 1/lambda - это математическое ожидание Exp-распределения
        tau = np.random.exponential(scale=1.0 / lam)
        t += tau
        if t < T1:
            events.append(t)
    return np.array(events)


def algorithm_2(lam, T, N):
    """
    Алгоритм 2:
      1 Генерирет один длинный поток длиной T1 >> T.
      2 Повторяет N раз
      3 Нормирует: Freq[i] /= N  - получает эмпирические вероятности.

    Возвращает массив counts (сырые числа событий для каждого эксперимента) и массив событий stream (чтобы не перегенерировать).
    """

    # Выбираю T1 так, чтобы он был сильно больше T.
    T1 = max(500.0 * T, 5000.0 / lam)

    # Генерирует длинный поток событий один раз
    stream = generate_poisson_stream(lam, T1)

    counts = np.empty(N, dtype=int)

    for k in range(N):
        # Случайно выбираю начало окна на оси времени
        a = np.random.uniform(0.0, T1 - T)

        # Считаю число событий, попавших в полуинтервал [a, a+T)
        left  = np.searchsorted(stream, a,     side='left')
        right = np.searchsorted(stream, a + T, side='left')
        counts[k] = right - left

    return counts, stream


def compute_statistics(counts, lam, T):
    """
    Вычисляет эмпирические и теоретические характеристики.
    Теоретические характеристики пуассоновского распределения:
        Теор. среднее   = lambda * T
        Теор. дисперсия = lambda * T
    (у Пуассона среднее равно дисперсии и равно параметру mu = lambda*T)

    Эмпирические считает по выборке counts[0..N-1]:
        emp_mean = (1/N) * sum(counts_i)
        emp_var  = (1/N) * sum((counts_i - emp_mean)^2)  - несмещённая через N-1
    """

    # Эмпирические характеристики
    emp_mean  = np.mean(counts)
    emp_var   = np.var(counts, ddof=1)   # ddof=1 -> несмещённая дисперсия (N-1)
    emp_std   = np.std(counts,  ddof=1)
    emp_min   = int(np.min(counts))
    emp_max   = int(np.max(counts))

    # Теоретические характеристики пуассоновского потока
    # Параметр Пуассона mu = lambda * T
    mu        = lam * T
    theor_mean = mu          # E[X] = mu
    theor_var  = mu          # D[X] = mu  (свойство Пуассона)

    # Отклонения
    delta_mean    = emp_mean - theor_mean          # абсолютное отклонение среднего
    rel_err_mean  = abs(delta_mean) / theor_mean * 100.0  # относительная ошибка, %

    delta_var     = emp_var - theor_var            # абсолютное отклонение дисперсии
    rel_err_var   = abs(delta_var)  / theor_var  * 100.0  # относительная ошибка, %

    return {
        "emp_mean":     emp_mean,
        "emp_var":      emp_var,
        "emp_std":      emp_std,
        "emp_min":      emp_min,
        "emp_max":      emp_max,
        "theor_mean":   theor_mean,
        "theor_var":    theor_var,
        "delta_mean":   delta_mean,
        "rel_err_mean": rel_err_mean,
        "delta_var":    delta_var,
        "rel_err_var":  rel_err_var,
        "mu":           mu,
    }


def build_frequencies(counts):
    """
    Строит эмпирическое распределение числа событий.

    Возвращает:
        values   - уникальные значения (0, 1, 2, ...)
        emp_probs  - эмпирические вероятности P*(X = k)
        theor_probs - теоретические вероятности Пуассона P(X = k) = e^{-mu}*mu^k/k!
        mu   - параметр Пуассона (lambda*T), берётся из уже посчитанного среднего но передаётся снаружи явно
    """
    # Диапазон наблюдаемых значений
    min_val = int(counts.min())
    max_val = int(counts.max())
    values = np.arange(min_val, max_val + 1)

    N = len(counts)
    # Подсчитывает число попаданий в каждое значение и делит на N -> частота
    emp_probs = np.array([np.sum(counts == k) / N for k in values])

    return values, emp_probs


def theor_probs_poisson(values, mu):
    """
    Теоретические вероятности Пуассона для заданных значений k и параметра mu
    """
    return poisson.pmf(values, mu)


def make_conclusion(stats, threshold_pct=10.0):
    """
    Формирет текстовый вывод: подтверждается ли пуассоновское распределение.
    Критерий: относительные ошибки по среднему и дисперсии не превышают порог.
    """
    ok_mean = stats["rel_err_mean"] <= threshold_pct
    ok_var  = stats["rel_err_var"]  <= threshold_pct

    lines = []
    if ok_mean and ok_var:
        lines.append(
            f"Результаты моделирования ПОДТВЕРЖДАЮТ теоретические характеристики "
            f"пуассоновского потока. Относительные ошибки по среднему "
            f"({stats['rel_err_mean']:.2f}%) и дисперсии ({stats['rel_err_var']:.2f}%) "
            f"не превышают {threshold_pct:.0f}%, что говорит о хорошем соответствии "
            f"эмпирического распределения теоретическому закону Пуассона."
        )
    else:
        bad = []
        if not ok_mean:
            bad.append(f"среднему ({stats['rel_err_mean']:.2f}%)")
        if not ok_var:
            bad.append(f"дисперсии ({stats['rel_err_var']:.2f}%)")
        lines.append(
            f"Наблюдается ЗНАЧИТЕЛЬНОЕ отклонение по {' и '.join(bad)} "
            f"(порог {threshold_pct:.0f}%). Возможно, число экспериментов N "
            f"слишком мало или выбраны нетипичные параметры. "
            f"Рекомендуется увеличить N."
        )
    return "\n".join(lines)


# ========
# GUI и тд

class App:
    def __init__(self, root):
        # Главное окно
        root.title("Лабораторная №8 (Пуассоновский поток)")
        root.resizable(True, True)

        # Основной контейнер: левая панель + правая (график)
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Левая панель
        left_frame = tk.Frame(main_frame, width=320)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_frame.pack_propagate(False)

        # Правая панель (график)
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Блок ввода параметров
        self._build_inputs(left_frame)

        # Блок статистики
        self._build_stats(left_frame)

        # Блок графика
        self._build_plot(right_frame)

    def _build_inputs(self, parent):
        # Фрейм параметров
        inp_frame = ttk.LabelFrame(parent, text="Параметры")
        inp_frame.pack(fill=tk.X, pady=(0, 8))

        # Интенсивность lambda
        ttk.Label(inp_frame, text="Интенсивность λ (заявок/ед. вр.):").grid(
            row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self.lam_var = tk.StringVar(value="5.0")
        ttk.Entry(inp_frame, textvariable=self.lam_var, width=10).grid(
            row=0, column=1, padx=6, pady=4)

        # Интервал T
        ttk.Label(inp_frame, text="Интервал T (ед. вр.):").grid(
            row=1, column=0, sticky=tk.W, padx=6, pady=4)
        self.T_var = tk.StringVar(value="2.0")
        ttk.Entry(inp_frame, textvariable=self.T_var, width=10).grid(
            row=1, column=1, padx=6, pady=4)

        # Число экспериментов N
        ttk.Label(inp_frame, text="Число экспериментов N:").grid(
            row=2, column=0, sticky=tk.W, padx=6, pady=4)
        self.N_var = tk.StringVar(value="1000")
        ttk.Entry(inp_frame, textvariable=self.N_var, width=10).grid(
            row=2, column=1, padx=6, pady=4)

        # Кнопка запуска
        self.run_btn = ttk.Button(inp_frame, text="Запустить моделирование",
                                  command=self._run)
        self.run_btn.grid(row=3, column=0, columnspan=2, pady=8)

    def _build_stats(self, parent):
        # Текстовое поле для вывода статистики
        stats_frame = ttk.LabelFrame(parent, text="Результаты")
        stats_frame.pack(fill=tk.BOTH, expand=True)

        self.stats_text = scrolledtext.ScrolledText(
            stats_frame, width=38, height=28, state=tk.DISABLED,
            font=("Courier New", 9), wrap=tk.WORD
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_plot(self, parent):
        # Создаёт фигуру matplotlib
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.fig.tight_layout(pad=3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_empty_plot()

    def _draw_empty_plot(self):
        # Пустой график до первого запуска
        self.ax.clear()
        self.ax.set_title("Распределение числа заявок за интервал T")
        self.ax.set_xlabel("Число заявок k")
        self.ax.set_ylabel("Вероятность P(X = k)")
        self.ax.text(0.5, 0.5, "Нажмите «Запустить моделирование»",
                     transform=self.ax.transAxes,
                     ha="center", va="center", color="gray", fontsize=11)
        self.canvas.draw()

    def _run(self):
        # Читает и валидирет параметры
        try:
            lam = float(self.lam_var.get())
            T   = float(self.T_var.get())
            N   = int(self.N_var.get())
            assert lam > 0 and T > 0 and N > 0
        except Exception:
            self._write_stats("Ошибка: введите корректные положительные значения параметров.")
            return

        self.run_btn.config(state=tk.DISABLED, text="Идёт моделирование...")
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, "Моделирование запущено...\n")
        self.stats_text.config(state=tk.DISABLED)
        self.fig.canvas.flush_events()

        # Запускает алгоритм 2 и сразу строит статистику
        self._run_btn_after(lam, T, N)

    def _run_btn_after(self, lam, T, N):
        # Алгоритм 2: получает массив counts по N экспериментам
        counts, _ = algorithm_2(lam, T, N)

        # Считает все характеристики
        stats = compute_statistics(counts, lam, T)

        # Строит частоты и теоретические вероятности
        values, emp_probs = build_frequencies(counts)
        t_probs = theor_probs_poisson(values, stats["mu"])

        # Вывод графика
        self._update_plot(values, emp_probs, t_probs, stats["mu"])

        # Вывод статистики в текстовое поле
        conclusion = make_conclusion(stats)
        self._write_stats(stats, lam, T, N, conclusion)

        self.run_btn.config(state=tk.NORMAL, text="Запустить моделирование")

    def _update_plot(self, values, emp_probs, t_probs, mu):
        # Очищает оси и рисует новые данные
        self.ax.clear()

        width = 0.4
        x = np.arange(len(values))

        # Эмпирическое распределение - синие столбцы
        bars = self.ax.bar(x - width / 2, emp_probs, width=width,
                           color="#4C72B0", alpha=0.85, label="Эмпирическое P*(X=k)")

        # Теоретическое распределение Пуассона - красные столбцы
        self.ax.bar(x + width / 2, t_probs, width=width,
                    color="#DD8452", alpha=0.85, label=f"Теоретическое P(X=k), μ={mu:.2f}")

        # Теоретическая линия поверх столбцов - для наглядности
        self.ax.plot(x + width / 2, t_probs, "o--",
                     color="#C44E52", linewidth=1.2, markersize=4, alpha=0.7)

        # Подписи осей и заголовок
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(values)
        self.ax.set_xlabel("Число заявок k", fontsize=11)
        self.ax.set_ylabel("Вероятность P(X = k)", fontsize=11)
        self.ax.set_title("Распределение числа заявок за интервал T\n"
                          "(пуассоновский поток)", fontsize=12)
        self.ax.legend(fontsize=9)
        self.ax.grid(axis="y", linestyle="--", alpha=0.4)
        self.fig.tight_layout()
        self.canvas.draw()

    def _write_stats(self, stats_or_msg, lam=None, T=None, N=None, conclusion=None):
        # Вывод результатов в текстовое поле
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)

        if isinstance(stats_or_msg, str):
            # Просто сообщение об ошибке
            self.stats_text.insert(tk.END, stats_or_msg)
            self.stats_text.config(state=tk.DISABLED)
            return

        s = stats_or_msg

        lines = []
        lines.append(f"Параметры: λ={lam}, T={T}, N={N}")
        lines.append("")

        lines.append("ЭМПИРИЧЕСКИЕ ХАРАКТЕРИСТИКИ:")
        lines.append(f"  Среднее число заявок : {s['emp_mean']:.4f}")
        lines.append(f"  Дисперсия            : {s['emp_var']:.4f}")
        lines.append(f"  Среднеквадратическое откл.    : {s['emp_std']:.4f}")
        lines.append(f"  Минимум              : {s['emp_min']}")
        lines.append(f"  Максимум             : {s['emp_max']}")
        lines.append("")

        lines.append("ТЕОРЕТИЧЕСКИЕ ХАРАКТЕРИСТИКИ:")
        lines.append(f"  Теор. среднее        : {s['theor_mean']:.4f}")
        lines.append(f"  Теор. дисперсия      : {s['theor_var']:.4f}")
        lines.append("")

        lines.append("ОТКЛОНЕНИЯ:")
        lines.append(f"  Откл. среднего       : {s['delta_mean']:+.4f}")
        lines.append(f"  Отн. ошибка ср. (%)  : {s['rel_err_mean']:.2f}%")
        lines.append(f"  Откл. дисперсии      : {s['delta_var']:+.4f}")
        lines.append(f"  Отн. ошибка дисп.(%) : {s['rel_err_var']:.2f}%")
        lines.append("")

        lines.append("ВЫВОД:")
        lines.append(conclusion)

        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)


# ============
# Точка входа

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1100x620")
    app = App(root)
    root.mainloop()
