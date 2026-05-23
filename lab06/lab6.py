import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from scipy import stats
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math

# четыре объёма выборки, для которых прогоняем моделирование
NS = [10, 100, 1000, 10000]

# уровень значимости для критерия хи-квадрат
ALPHA = 0.05


def generate_dsv(values, probs, n):
    """Генерирует n значений ДСВ методом инверсии (накопленных вероятностей).

    Строим кумулятивный ряд F[i] = p[0]+...+p[i], затем для каждого
    случайного alpha из [0,1) ищем первый индекс i, где alpha < F[i].
    """
    cumulative = np.cumsum(probs)
    # генерируем n равномерных чисел из [0, 1) - базовый датчик
    alphas = np.random.uniform(0.0, 1.0, n)
    # searchsorted возвращает индекс первой позиции, куда можно вставить alpha,
    # не нарушив порядок - это ровно тот интервал, в который попало alpha
    indices = np.searchsorted(cumulative, alphas)
    # clip на случай численной погрешности (alpha очень близко к 1)
    indices = np.clip(indices, 0, len(values) - 1)
    return np.array(values)[indices]


def box_muller(mu, sigma, n):
    """Генерирует n значений нормального распределения N(mu, sigma^2).

    Используется точный метод Бокса–Мюллера:
        eta1 = sqrt(-2 * ln(U1)) * cos(2*pi*U2)  ~ N(0, 1)
        eta2 = sqrt(-2 * ln(U1)) * sin(2*pi*U2)  ~ N(0, 1)
    Затем масштабируем к нужному распределению: xi = mu + sigma * eta
    """
    pairs = math.ceil(n / 2)
    # U1 начинается от 1e-10, чтобы избежать log(0) = -inf
    u1 = np.random.uniform(1e-10, 1.0, pairs)
    u2 = np.random.uniform(0.0, 1.0, pairs)
    r = np.sqrt(-2.0 * np.log(u1))
    theta = 2.0 * np.pi * u2
    eta1 = r * np.cos(theta)
    eta2 = r * np.sin(theta)
    # объединяем оба набора и берём ровно n значений
    standard = np.concatenate([eta1, eta2])[:n]
    return mu + sigma * standard


def central_limit(mu, sigma, n):
    """Генерирует n значений N(mu, sigma^2) через центральную предельную теорему.

    Идея: сумма 12 равномерных [0,1) имеет M = 6, D = 1, поэтому sum_12 - 6 приближённо равна N(0, 1).
    Метод проще в понимании, но даёт менее точные хвосты, чем Бокс–Мюллер.
    """
    u = np.random.uniform(0.0, 1.0, (n, 12))
    standard = u.sum(axis=1) - 6.0
    return mu + sigma * standard


def chi2_discrete(observed, probs, n):
    """Критерий хи-квадрат для ДСВ.
    Формула: chi2 = sum( (n_i - N*p_i)^2 / (N*p_i) )
    Степени свободы: df = m - 1, где m - число значений СВ.
    Возвращает: (наблюдаемое_chi2, критическое_chi2, df, отвергается_ли)
    """
    expected = n * np.array(probs, dtype=float)
    mask = expected > 0
    chi2_obs = float(np.sum((observed[mask] - expected[mask]) ** 2 / expected[mask]))
    df = int(np.sum(mask)) - 1
    chi2_crit = stats.chi2.ppf(1.0 - ALPHA, df)
    return chi2_obs, chi2_crit, df, chi2_obs > chi2_crit


def chi2_normal(sample, mu, sigma, n_bins=10):
    """Критерий хи-квадрат для нормальной НепрСВ.
    Разбиваем выборку на интервалы, для каждого считаем теоретическую вероятность через CDF нормального распределения.
    Степени свободы: df = k - 2 - 1, где k - число интервалов, вычитаем 2, потому что оцениваем два параметра (mu и sigma).
    Возвращает: (chi2_obs, chi2_crit, df, отвергается_ли)
    """
    counts, bin_edges = np.histogram(sample, bins=n_bins)
    # вероятность попасть в каждый интервал по нормальному CDF
    theo_probs = np.diff(stats.norm.cdf(bin_edges, loc=mu, scale=sigma))
    expected = theo_probs / theo_probs.sum() * len(sample)
    mask = expected >= 1.0
    if mask.sum() < 2:
        return None, None, None, None
    chi2_obs = float(np.sum((counts[mask] - expected[mask]) ** 2 / expected[mask]))
    df = max(1, int(mask.sum()) - 2 - 1)
    chi2_crit = stats.chi2.ppf(1.0 - ALPHA, df)
    return chi2_obs, chi2_crit, df, chi2_obs > chi2_crit


class Lab61Tab(ttk.Frame):
    """Вкладка лабораторной 6.1 - дискретные случайные величины."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # панель ввода параметров
        input_frame = ttk.LabelFrame(self, text=" Параметры распределения ")
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 4))

        # заголовки столбцов таблицы ввода
        ttk.Label(input_frame, text="  i  ", font=("Arial", 9, "bold")).grid(
            row=0, column=0, padx=6, pady=(6, 2))
        ttk.Label(input_frame, text="  xᵢ  ", font=("Arial", 9, "bold")).grid(
            row=0, column=1, padx=6, pady=(6, 2))
        ttk.Label(input_frame, text="  pᵢ  ", font=("Arial", 9, "bold")).grid(
            row=0, column=2, padx=6, pady=(6, 2))

        self.x_entries = []  # поля ввода значений xᵢ
        self.p_entries = []  # поля ввода вероятностей pᵢ

        # стартовые значения - равномерное распределение по умолчанию
        default_x = [1, 2, 3, 4, 5]
        default_p = [0.20, 0.12, 0.28, 0.20]  # p5 = 1 - сумма этих четырёх

        for i in range(5):
            ttk.Label(input_frame, text=str(i + 1)).grid(
                row=i + 1, column=0, padx=8, pady=2)

            xe = ttk.Entry(input_frame, width=8)
            xe.insert(0, str(default_x[i]))
            xe.grid(row=i + 1, column=1, padx=4, pady=2)
            self.x_entries.append(xe)

            pe = ttk.Entry(input_frame, width=8)
            if i < 4:
                pe.insert(0, str(default_p[i]))
                # при каждом нажатии клавиши пересчитываем p5
                pe.bind("<KeyRelease>", self._recalc_p5)
            else:
                # p5 заблокировано - оно вычисляется автоматически
                pe.config(state="disabled")
            pe.grid(row=i + 1, column=2, padx=4, pady=2)
            self.p_entries.append(pe)

        # подпись-подсказка рядом с p5
        ttk.Label(input_frame, text="← 1 − (p₁+p₂+p₃+p₄)",
                  foreground="#888", font=("Arial", 8)).grid(
            row=5, column=3, sticky="w", padx=4)

        # рассчитываем p5 сразу при запуске, чтобы поле не было пустым
        self._recalc_p5()

        # кнопка запуска
        ttk.Button(input_frame, text="▶  Запустить моделирование",
                   command=self._run).grid(
            row=1, column=4, rowspan=5, padx=20, pady=4)

        # теоретические значения, обновляем при запуске
        self.theo_label = ttk.Label(input_frame, text="", font=("Courier", 9),
                                    foreground="#444")
        self.theo_label.grid(row=1, column=5, rowspan=5, padx=10, sticky="w")

        # таблица результатов, пакуется раньше графика, чтобы pack(side=BOTTOM) отдал ей место до того, как canvas займёт всё
        bottom_frame = ttk.LabelFrame(self, text=" Результаты по всем N ")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4, 10))

        cols = ("N", "M_теор", "M_эмп", "Err_M%",
                "D_теор", "D_эмп", "Err_D%",
                "χ²_набл", "χ²_крит", "Вывод")
        headers = ("N", "M теор.", "M эмп.", "Погр. M %",
                   "D теор.", "D эмп.", "Погр. D %",
                   "χ² набл.", "χ² крит.", "Критерий")

        self.tree = ttk.Treeview(bottom_frame, columns=cols,
                                 show="headings", height=4)
        for col, h in zip(cols, headers):
            self.tree.heading(col, text=h)
            w = 60 if col == "N" else 110
            self.tree.column(col, width=w, anchor="center")

        # добавляем теги для цветовой подсветки строк (пройден / отклонён)
        self.tree.tag_configure("ok",  background="#e8f5e9")  # светло-зелёный
        self.tree.tag_configure("bad", background="#ffebee")  # светло-красный

        self.tree.pack(fill=tk.X, padx=4, pady=4)

        # matplotlib-фигура с четырьмя подграфиками 2×2
        self.fig = Figure(figsize=(14, 7), dpi=96)
        self.axes = [
            self.fig.add_subplot(2, 2, 1),
            self.fig.add_subplot(2, 2, 2),
            self.fig.add_subplot(2, 2, 3),
            self.fig.add_subplot(2, 2, 4),
        ]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True,
                                         padx=12, pady=4)

    def _recalc_p5(self, event=None):
        """Пересчитывает p5 = 1 − (p1+p2+p3+p4) при изменении любого из p1..p4."""
        try:
            s = sum(float(self.p_entries[i].get()) for i in range(4))
            p5 = round(1.0 - s, 6)
            self.p_entries[4].config(state="normal")
            self.p_entries[4].delete(0, tk.END)
            self.p_entries[4].insert(0, str(p5))
            self.p_entries[4].config(state="disabled")
        except ValueError:
            pass  # пользователь ещё набирает число, ждём финального ввода

    def _run(self):
        """Считывает параметры, запускает моделирование, заполняет графики и таблицу."""
        # читаем значения xᵢ
        try:
            values = [float(self.x_entries[i].get()) for i in range(5)]
        except ValueError:
            messagebox.showerror("Ошибка", "Значения xᵢ должны быть числами!")
            return

        # перед чтением p5 убеждаемся, что он пересчитан
        self._recalc_p5()
        try:
            self.p_entries[4].config(state="normal")
            probs = [float(self.p_entries[i].get()) for i in range(5)]
            self.p_entries[4].config(state="disabled")
        except ValueError:
            messagebox.showerror("Ошибка", "Вероятности pᵢ должны быть числами!")
            return

        values = np.array(values)
        probs = np.array(probs)

        # проверка: все вероятности неотрицательны
        if np.any(probs < -1e-9):
            messagebox.showerror(
                "Ошибка",
                "Одна из вероятностей отрицательна!\n"
                "Проверьте, что p₁ + p₂ + p₃ + p₄ ≤ 1.")
            return

        probs = np.clip(probs, 0.0, None)
        probs /= probs.sum()  # нормируем на случай накопленной погрешности

        # теоретические характеристики - вычисляются аналитически по заданному ряду
        m_teor = float(np.sum(values * probs))
        d_teor = float(np.sum(values ** 2 * probs) - m_teor ** 2)

        # обновляем подпись с теоретическими значениями
        self.theo_label.config(
            text=f"M[X] = {m_teor:.4f}\nD[X] = {d_teor:.4f}")

        # очищаем таблицу перед новым запуском
        self.tree.delete(*self.tree.get_children())

        # прогоняем моделирование для каждого N
        for i, N in enumerate(NS):
            ax = self.axes[i]
            ax.clear()

            # генерируем выборку из N значений ДСВ
            sample = generate_dsv(values, probs, N)

            # считаем, сколько раз каждое значение встретилось
            observed = np.array([np.sum(sample == v) for v in values], dtype=float)
            emp_probs = observed / N  # эмпирические вероятности

            # эмпирическое среднее и дисперсия
            m_emp = float(np.sum(values * emp_probs))
            d_emp = float(np.sum(values ** 2 * emp_probs) - m_emp ** 2)

            # относительные погрешности в процентах
            err_m = abs(m_emp - m_teor) / (abs(m_teor) + 1e-15) * 100
            err_d = abs(d_emp - d_teor) / (abs(d_teor) + 1e-15) * 100

            # критерий хи-квадрат
            chi2_obs, chi2_crit, df, rejected = chi2_discrete(observed, probs, N)

            verdict = "ОТКЛОНЁН" if rejected else "ПРОЙДЕН"
            tag = "bad" if rejected else "ok"

            self.tree.insert("", "end", tags=(tag,), values=(
                N,
                f"{m_teor:.4f}",
                f"{m_emp:.4f}",
                f"{err_m:.1f}",
                f"{d_teor:.4f}",
                f"{d_emp:.4f}",
                f"{err_d:.1f}",
                f"{chi2_obs:.3f}",
                f"{chi2_crit:.3f}",
                verdict,
            ))

            # рисуем сдвоенную гистограмму: теоретические и эмпирические вероятности
            x_pos = np.arange(len(values))
            ax.bar(x_pos - 0.2, probs, 0.38,
                   label="Теория", color="steelblue", alpha=0.85)
            ax.bar(x_pos + 0.2, emp_probs, 0.38,
                   label="Эмп.", color="orange", alpha=0.85)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(
                [f"{v:.0f}" if v == int(v) else str(v) for v in values],
                fontsize=9)
            ax.set_ylabel("P", fontsize=9)
            ax.set_title(f"N = {N}", fontsize=10, fontweight="bold")
            ax.legend(fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            # подписываем хи-квадрат прямо на графике
            color = "#c0392b" if rejected else "#27ae60"
            ax.set_xlabel(
                f"χ²={chi2_obs:.2f}  крит={chi2_crit:.2f}  →  {verdict}",
                fontsize=8, color=color)

        self.fig.tight_layout(pad=2.5)
        self.canvas.draw()


class Lab62Tab(ttk.Frame):
    """Вкладка лабораторной 6.2 - нормальная случайная величина."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # панель ввода параметров
        input_frame = ttk.LabelFrame(self, text=" Параметры распределения ")
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 4))

        ttk.Label(input_frame, text="Среднее (μ):").grid(
            row=0, column=0, padx=(12, 4), pady=8, sticky="e")
        self.mu_entry = ttk.Entry(input_frame, width=10)
        self.mu_entry.insert(0, "0")
        self.mu_entry.grid(row=0, column=1, padx=4, pady=8)

        ttk.Label(input_frame, text="Ст. откл. (σ):").grid(
            row=0, column=2, padx=(16, 4), pady=8, sticky="e")
        self.sigma_entry = ttk.Entry(input_frame, width=10)
        self.sigma_entry.insert(0, "1")
        self.sigma_entry.grid(row=0, column=3, padx=4, pady=8)

        ttk.Label(input_frame, text="Метод генерации:").grid(
            row=0, column=4, padx=(16, 4), pady=8, sticky="e")
        self.method_var = tk.StringVar(value="Бокс–Мюллер")
        method_combo = ttk.Combobox(
            input_frame, textvariable=self.method_var,
            values=["Бокс–Мюллер", "Суммирование (ЦПТ)"],
            state="readonly", width=18)
        method_combo.grid(row=0, column=5, padx=4, pady=8)

        ttk.Button(input_frame, text="▶  Запустить моделирование",
                   command=self._run).grid(row=0, column=6, padx=20, pady=8)

        # таблица результатов
        bottom_frame = ttk.LabelFrame(self, text=" Результаты по всем N ")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4, 10))

        cols = ("N", "M_теор", "M_эмп", "Err_M%",
                "D_теор", "D_эмп", "Err_D%",
                "χ²_набл", "χ²_крит", "Вывод")
        headers = ("N", "M теор.", "M эмп.", "Погр. M %",
                   "D теор.", "D эмп.", "Погр. D %",
                   "χ² набл.", "χ² крит.", "Критерий")

        self.tree = ttk.Treeview(bottom_frame, columns=cols,
                                 show="headings", height=4)
        for col, h in zip(cols, headers):
            self.tree.heading(col, text=h)
            w = 60 if col == "N" else 110
            self.tree.column(col, width=w, anchor="center")

        self.tree.tag_configure("ok",  background="#e8f5e9")
        self.tree.tag_configure("bad", background="#ffebee")
        self.tree.pack(fill=tk.X, padx=4, pady=4)

        # четыре подграфика 2×2 для четырёх значений N
        self.fig = Figure(figsize=(14, 7), dpi=96)
        self.axes = [
            self.fig.add_subplot(2, 2, 1),
            self.fig.add_subplot(2, 2, 2),
            self.fig.add_subplot(2, 2, 3),
            self.fig.add_subplot(2, 2, 4),
        ]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True,
                                         padx=12, pady=4)

    def _run(self):
        """Считывает параметры, генерирует выборки и строит гистограммы."""
        try:
            mu    = float(self.mu_entry.get())
            sigma = float(self.sigma_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "μ и σ должны быть числами!")
            return

        if sigma <= 0:
            messagebox.showerror("Ошибка", "Стандартное отклонение σ должно быть > 0!")
            return

        self.tree.delete(*self.tree.get_children())

        for i, N in enumerate(NS):
            ax = self.axes[i]
            ax.clear()

            # генерируем выборку выбранным методом
            if self.method_var.get() == "Бокс–Мюллер":
                sample = box_muller(mu, sigma, N)
            else:
                sample = central_limit(mu, sigma, N)

            # эмпирические характеристики по выборке
            m_emp = float(np.mean(sample))
            d_emp = float(np.var(sample))

            # теоретические значения - это заданные параметры распределения
            m_teor = mu
            d_teor = sigma ** 2

            # относительные погрешности в процентах
            err_m = abs(m_emp - m_teor) / (abs(m_teor) + 1e-15) * 100
            err_d = abs(d_emp - d_teor) / (abs(d_teor) + 1e-15) * 100

            # хи-квадрат: число интервалов по формуле Стёрджеса
            k = max(5, min(15, 1 + int(math.floor(math.log2(N)))))
            chi2_obs, chi2_crit, df, rejected = chi2_normal(sample, mu, sigma, k)

            if chi2_obs is not None:
                verdict = "ОТКЛОНЁН" if rejected else "ПРОЙДЕН"
                tag = "bad" if rejected else "ok"
                chi2_obs_str  = f"{chi2_obs:.3f}"
                chi2_crit_str = f"{chi2_crit:.3f}"
            else:
                verdict = "-"
                tag = "ok"
                chi2_obs_str  = "-"
                chi2_crit_str = "-"

            self.tree.insert("", "end", tags=(tag,), values=(
                N,
                f"{m_teor:.4f}",
                f"{m_emp:.4f}",
                f"{err_m:.1f}",
                f"{d_teor:.4f}",
                f"{d_emp:.4f}",
                f"{err_d:.1f}",
                chi2_obs_str,
                chi2_crit_str,
                verdict,
            ))

            # гистограмма с нормировкой density=True - по оси Y плотность, масштаб совпадает с кривой нормального распределения
            n_bins = max(10, min(50, N // 20 + 5))
            ax.hist(sample, bins=n_bins, density=True,
                    color="steelblue", alpha=0.65, label="Выборка")

            # теоретическая кривая N(mu, sigma^2)
            x_line = np.linspace(mu - 4.5 * sigma, mu + 4.5 * sigma, 400)
            ax.plot(x_line, stats.norm.pdf(x_line, mu, sigma),
                    color="red", linewidth=1.8, label=f"N({mu}, {sigma}²)")

            # вертикальные линии: теоретическое среднее и выборочное среднее
            ax.axvline(mu,    color="orange", linestyle="--",
                       linewidth=1.2, label=f"μ={mu}")
            ax.axvline(m_emp, color="green",  linestyle=":",
                       linewidth=1.2, label=f"x̄={m_emp:.3f}")

            ax.set_title(f"N = {N}", fontsize=10, fontweight="bold")
            ax.set_ylabel("Плотность", fontsize=9)
            ax.legend(fontsize=7.5)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            # подпись хи-квадрат под графиком
            if chi2_obs is not None:
                color = "#c0392b" if rejected else "#27ae60"
                ax.set_xlabel(
                    f"χ²={chi2_obs:.2f}  крит={chi2_crit:.2f}  →  {verdict}",
                    fontsize=8, color=color)

        self.fig.tight_layout(pad=2.5)
        self.canvas.draw()


class App:
    """Главное окно: две вкладки - дискретная и нормальная СВ."""

    def __init__(self, root):
        self.root = root
        root.title("Лабораторная работа №6 - Стохастическое моделирование")
        # большое окно
        root.geometry("1500x1000")
        root.minsize(1100, 750)

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook.Tab", font=("Arial", 10), padding=[14, 6])
        style.configure("TLabelframe.Label", font=("Arial", 9, "bold"))

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tab1 = Lab61Tab(notebook)
        tab2 = Lab62Tab(notebook)

        notebook.add(tab1, text="lab06-1  Дискретная СВ")
        notebook.add(tab2, text="lab06-2  Нормальная СВ")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
