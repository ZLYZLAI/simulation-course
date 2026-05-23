import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from markov_logic import MarkovWeatherModel


# Цветовая схема

# Цвета заливки для каждого состояния (жёлтый / голубой / серый)
STATE_COLORS = ['#FFD700', '#87CEEB', '#778899']

# Цвета кривых для графика сходимости (чуть темнее)
CONV_COLORS  = ['#B8860B', '#2171B5', '#525252']

# Цвета столбцов гистограммы
BAR_EMP_COLOR = '#64B5F6'
BAR_STA_COLOR = '#EF9A9A'

# Текст/фон для лейбла текущего состояния
STATE_BADGE = [
    ('#7B5800', '#FFF3CD'),
    ('#0A3D6B', '#DBEAFE'),
    ('#2C2C2C', '#D1D5DB'),
]

STATE_NAMES = ['Ясно', 'Облачно', 'Пасмурно']


# Главное окно

class MarkovApp(tk.Tk):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.title('Марковская модель погоды (НВЦМ)')

        self._maximize_window()

        self.model     = MarkovWeatherModel()
        self.running   = False
        self._after_id = None

        self._build_layout()
        self._refresh_diag_labels()
        self._update_ui()
        self._redraw_plots()

    def _maximize_window(self):
        """Разворачиваю окно на весь экран (кросс-платформенно)."""
        try:
            self.state('zoomed')
        except tk.TclError:
            try:
                self.attributes('-zoomed', True)
            except tk.TclError:
                w, h = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f'{w}x{h}+0+0')

    # Построение интерфейса

    def _build_layout(self):
        """Двухколоночный лэйаут: управление слева, графики справа."""
        self.columnconfigure(0, weight=0, minsize=375)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = tk.Frame(self, bd=1, relief='groove', bg='#F9FAFB')
        left.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)

        right = tk.Frame(self, bg='white')
        right.grid(row=0, column=1, sticky='nsew', padx=(4, 8), pady=8)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_control_panel(left)
        self._build_plot_panel(right)

    #  Левая панель 

    def _build_control_panel(self, p):
        kw = dict(bg='#F9FAFB')

        # Заголовок
        tk.Label(p, text='Марковская модель погоды',
                 font=('Segoe UI', 13, 'bold'), **kw).pack(padx=10, pady=(10, 1))
        tk.Label(p, text='Непрерывная цепь Маркова (НВЦМ)',
                 font=('Segoe UI', 8, 'italic'), fg='#6B7280', **kw).pack()

        self._sep(p)
        self._build_q_section(p, kw)
        self._sep(p)
        self._build_state_section(p, kw)
        self._sep(p)
        self._build_buttons_section(p)
        self._sep(p)
        self._build_speed_section(p, kw)
        self._sep(p)

        # Кнопка сохранения
        tk.Button(p, text='💾   Сохранить статистику в CSV',
                  command=self._save_csv,
                  bg='#D97706', fg='white',
                  activebackground='#B45309', activeforeground='white',
                  font=('Segoe UI', 10, 'bold'),
                  pady=7, relief='flat', cursor='hand2',
                  ).pack(fill='x', padx=12, pady=(4, 2))
        tk.Label(p, text='Файлы сохраняются в папку ./output/',
                 font=('Segoe UI', 8), fg='#9CA3AF', **kw).pack(pady=(0, 6))

    def _build_q_section(self, p, kw):
        """Секция: таблица ввода матрицы интенсивностей Q."""
        tk.Label(p, text='Матрица интенсивностей Q  (1/день):',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(padx=10, pady=(4, 0))
        tk.Label(p,
                 text='Вне диагонали: λ_ij >= 0 (ввожу вручную)\n'
                      'Диагональ: q_ii = −Σλ_ij  (вычисляется авто)',
                 font=('Segoe UI', 8), fg='#6B7280', justify='left', **kw).pack(padx=12)

        mf = tk.Frame(p, bg='#F9FAFB')
        mf.pack(pady=4)

        # Шапка столбцов
        tk.Label(mf, text='', width=9, bg='#F9FAFB').grid(row=0, column=0)
        for j, name in enumerate(STATE_NAMES):
            tk.Label(mf, text=name, width=9, font=('Segoe UI', 9, 'bold'),
                     fg=self._text_color(STATE_COLORS[j]),
                     bg='#F9FAFB').grid(row=0, column=j + 1, padx=2)

        # Ячейки: вне диагонали - Entry, диагональ - Label (read-only)
        self._q_vars    = []
        self._diag_lbls = []

        off = self.model.get_off_diag_display()

        for i in range(3):
            row_vars = []
            tk.Label(mf, text=STATE_NAMES[i], width=9,
                     font=('Segoe UI', 9, 'bold'),
                     fg=self._text_color(STATE_COLORS[i]),
                     bg='#F9FAFB').grid(row=i + 1, column=0)

            for j in range(3):
                if i == j:
                    lbl = tk.Label(mf, text='-0.400', width=9,
                                   bg='#E5E7EB', fg='#6B7280',
                                   font=('Courier', 9), relief='sunken')
                    lbl.grid(row=i + 1, column=j + 1, padx=2, pady=2)
                    self._diag_lbls.append(lbl)
                    row_vars.append(None)
                else:
                    var = tk.StringVar(value=f'{off[i, j]:.3f}')
                    # Трассировка: при любом изменении поля пересчитываю диагональ
                    var.trace_add('write', lambda *_: self._preview_diag())
                    e   = tk.Entry(mf, textvariable=var, width=9,
                                   justify='center', font=('Courier', 9),
                                   relief='solid', bd=1)
                    e.grid(row=i + 1, column=j + 1, padx=2, pady=2)
                    row_vars.append(var)

            self._q_vars.append(row_vars)

        tk.Button(p, text='✔  Применить матрицу',
                  command=self._apply_matrix,
                  bg='#065F46', fg='white',
                  activebackground='#047857', activeforeground='white',
                  font=('Segoe UI', 9, 'bold'),
                  relief='flat', pady=5, cursor='hand2',
                  ).pack(padx=12, pady=(2, 4), fill='x')

    def _build_state_section(self, p, kw):
        """Секция: текущее состояние, время, счётчики."""
        tk.Label(p, text='Текущее состояние:',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(pady=(4, 2))

        self._state_lbl = tk.Label(p, text='Ясно',
                                   font=('Segoe UI', 16, 'bold'),
                                   width=17, pady=6, relief='ridge')
        self._state_lbl.pack(padx=20, pady=2)

        # Суммарное время и число переходов
        tf = tk.Frame(p, bg='#F9FAFB')
        tf.pack(padx=14, pady=(4, 2), fill='x')
        tf.columnconfigure(0, weight=1)
        tf.columnconfigure(1, weight=0)

        for row_idx, (label_text, attr) in enumerate([
            ('Суммарное время (дн):', '_time_lbl'),
            ('Переходов:',            '_trans_lbl'),
        ]):
            tk.Label(tf, text=label_text, font=('Segoe UI', 9),
                     anchor='w', bg='#F9FAFB').grid(row=row_idx, column=0, sticky='w')
            lbl = tk.Label(tf, text='0', font=('Segoe UI', 9, 'bold'),
                           anchor='e', bg='#F9FAFB')
            lbl.grid(row=row_idx, column=1, sticky='e')
            setattr(self, attr, lbl)

        # Время по состояниям
        tk.Label(p, text='Накопленное время (дн):',
                 font=('Segoe UI', 9, 'bold'), **kw).pack(pady=(6, 2))

        cf = tk.Frame(p, bg='#F9FAFB')
        cf.pack(padx=14, pady=2, fill='x')
        cf.columnconfigure(0, weight=1)
        cf.columnconfigure(1, weight=0)

        self._cnt_lbls = []
        for i in range(3):
            tk.Label(cf, text=STATE_NAMES[i] + ':',
                     font=('Segoe UI', 9, 'bold'),
                     fg=self._text_color(STATE_COLORS[i]),
                     anchor='w', bg='#F9FAFB', width=12,
                     ).grid(row=i, column=0, sticky='w', pady=1)
            lbl = tk.Label(cf, text='0.00', font=('Segoe UI', 9),
                           anchor='e', bg='#F9FAFB')
            lbl.grid(row=i, column=1, sticky='e', pady=1)
            self._cnt_lbls.append(lbl)

    def _build_buttons_section(self, p):
        """Секция: Старт / Стоп / Сброс."""
        bf = tk.Frame(p, bg='#F9FAFB')
        bf.pack(pady=6)

        self._btn_start = tk.Button(
            bf, text='▶  Старт', width=9,
            bg='#1D4ED8', fg='white',
            activebackground='#1E40AF', activeforeground='white',
            font=('Segoe UI', 10, 'bold'), relief='flat', pady=5, cursor='hand2',
            command=self._start)
        self._btn_start.grid(row=0, column=0, padx=5)

        self._btn_stop = tk.Button(
            bf, text='⏸  Стоп', width=9,
            bg='#B91C1C', fg='white',
            activebackground='#991B1B', activeforeground='white',
            font=('Segoe UI', 10, 'bold'), relief='flat', pady=5, cursor='hand2',
            state='disabled', command=self._stop)
        self._btn_stop.grid(row=0, column=1, padx=5)

        tk.Button(bf, text='↺  Сброс', width=9,
                  bg='#374151', fg='white',
                  activebackground='#1F2937', activeforeground='white',
                  font=('Segoe UI', 10, 'bold'), relief='flat', pady=5, cursor='hand2',
                  command=self._reset,
                  ).grid(row=0, column=2, padx=5)

    def _build_speed_section(self, p, kw):
        """Секция: ползунок задержки между переходами."""
        tk.Label(p, text='Задержка между шагами:',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(pady=(4, 0))

        sf = tk.Frame(p, bg='#F9FAFB')
        sf.pack(padx=10, fill='x')

        tk.Label(sf, text='50\nмс', font=('Segoe UI', 8),
                 fg='#6B7280', bg='#F9FAFB').pack(side='left')

        self._speed_var = tk.IntVar(value=500)
        ttk.Scale(sf, from_=50, to=2000, orient='horizontal',
                  variable=self._speed_var, length=220,
                  ).pack(side='left', fill='x', expand=True, padx=6)

        tk.Label(sf, text='2000\nмс', font=('Segoe UI', 8),
                 fg='#6B7280', bg='#F9FAFB').pack(side='left')

        self._speed_lbl = tk.Label(p, text='500 мс',
                                   font=('Segoe UI', 11, 'bold'),
                                   fg='#1D4ED8', **kw)
        self._speed_lbl.pack(pady=(0, 4))
        self._speed_var.trace_add('write', self._on_speed_change)

    def _build_plot_panel(self, p):
        """Три matplotlib-субграфика: поток / гистограмма / сходимость."""
        self._fig = Figure(figsize=(12, 8), dpi=90)
        self._fig.patch.set_facecolor('white')
        self._fig.subplots_adjust(hspace=0.44, wspace=0.30,
                                   left=0.07, right=0.97,
                                   top=0.94, bottom=0.08)

        self._ax_stream = self._fig.add_subplot(2, 2, (1, 2))  # верхний - на всю ширину
        self._ax_bar    = self._fig.add_subplot(2, 2, 3)        # нижний левый
        self._ax_conv   = self._fig.add_subplot(2, 2, 4)        # нижний правый

        self._canvas = FigureCanvasTkAgg(self._fig, master=p)
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

    # Вспомогательные методы

    @staticmethod
    def _sep(parent):
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=8, pady=4)

    @staticmethod
    def _text_color(hex_color, factor=0.55):
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}'

    # Обработчики событий

    def _preview_diag(self):
        """
        Пересчитываю диагональные лейблы Q в реальном времени - без нажатия Apply.
        Вызывается трассировкой при каждом изменении любого поля ввода.
        Если значение в поле некорректное (не число), просто не обновляю - не бросаю ошибок.
        """
        try:
            for i in range(3):
                row_sum = 0.0
                for j in range(3):
                    if i == j:
                        continue
                    raw = self._q_vars[i][j].get().strip().replace(',', '.')
                    # Если поле пустое или содержит только минус - пропускаю строку целиком
                    val = float(raw)
                    if val >= 0:
                        row_sum += val
                # Диагональный элемент q_ii = -(сумма строки без диагонали)
                self._diag_lbls[i].config(text=f'{-row_sum:.3f}')
        except (ValueError, AttributeError):
            # Некорректный ввод (пустое поле, буквы и т.п.) - просто ничего не делаю
            pass

    def _apply_matrix(self):
        """Считываю Q из полей ввода, передаю в модель. Возвращаю True при успехе."""
        try:
            mat = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    if i == j:
                        continue
                    raw = self._q_vars[i][j].get().strip().replace(',', '.')
                    val = float(raw)
                    if val < 0:
                        raise ValueError(
                            f'λ[{STATE_NAMES[i]}->{STATE_NAMES[j]}] = {val} '
                            f'- интенсивность не может быть отрицательной!')
                    mat[i, j] = val

            # Проверяю, что хотя бы одна интенсивность в каждой строке > 0.
            # Если вся строка нулевая, состояние поглощающее: цепь зайдёт туда
            # и никогда не выйдет - симуляция зависнет на одном состоянии.
            absorbing = [STATE_NAMES[i] for i in range(3)
                         if mat[i, :].sum() < 1e-12]
            if absorbing:
                messagebox.showwarning(
                    'Предупреждение',
                    'Все внедиагональные интенсивности в строке нулевые:\n  ' +
                    ', '.join(absorbing) +
                    '\n\nЭто поглощающее состояние - попав туда, цепь не выйдет.\n'
                    'Матрица принята, но результаты могут быть некорректны.')

            self.model.set_intensities(mat)
            self._refresh_diag_labels()
            return True
        except ValueError as e:
            messagebox.showerror('Ошибка ввода', str(e))
            return False

    def _refresh_diag_labels(self):
        """Обновляю лейблы диагонали Q из модели (вызывается после Apply)."""
        Q = self.model.get_Q_display()
        for idx, i in enumerate([0, 1, 2]):
            self._diag_lbls[idx].config(text=f'{Q[i, i]:.3f}')

    def _start(self):
        if not self._apply_matrix():
            return
        self.running = True
        self._btn_start.config(state='disabled')
        self._btn_stop.config(state='normal')
        self._tick()

    def _stop(self):
        self.running = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')

    def _reset(self):
        self._stop()
        self.model.reset()
        self._update_ui()
        self._redraw_plots()

    def _tick(self):
        """
        Один шаг симуляции. Планирует следующий вызов через after().
        Паттерн неблокирующей анимации в tkinter: вместо while True -
        рекурсивное планирование через event loop.
        """
        if not self.running:
            return

        self.model.step()
        self._update_ui()

        # Перерисовка matplotlib - дорогая операция; делаю реже при малой задержке
        n     = self.model.n_transitions
        speed = self._speed_var.get()
        skip  = max(1, 120 // speed)
        if n % skip == 0 or n <= 20:
            self._redraw_plots()

        self._after_id = self.after(speed, self._tick)

    def _on_speed_change(self, *_):
        self._speed_lbl.config(text=f'{self._speed_var.get()} мс')

    def _save_csv(self):
        if self.model.n_transitions == 0:
            messagebox.showwarning('Нет данных',
                                   'Запустите моделирование перед сохранением.')
            return
        paths = self.model.save_to_csv('output')
        messagebox.showinfo('Готово',
                            'Файлы успешно сохранены:\n\n' + '\n'.join(paths))

    # Обновление UI и графиков

    def _update_ui(self):
        s = self.model.current_state
        fg, bg = STATE_BADGE[s]
        self._state_lbl.config(text=STATE_NAMES[s], fg=fg, bg=bg)
        self._time_lbl.config(text=f'{self.model.total_time:.2f}')
        self._trans_lbl.config(text=str(self.model.n_transitions))
        for i in range(3):
            self._cnt_lbls[i].config(text=f'{self.model.time_in_state[i]:.2f}')

    def _redraw_plots(self):
        self._plot_stream()
        self._plot_bar()
        self._plot_convergence()
        self._canvas.draw_idle()

    def _plot_stream(self):
        """
        График 1: непрерывный поток состояний s(t).
        Каждый завершённый интервал - горизонтальная линия + цветная полоса.
        Ширина полосы = длительность пребывания (случайная, ~ Exp(lambda_i)).
        """
        ax = self._ax_stream
        ax.clear()
        ax.set_title('Непрерывный поток состояний', fontsize=10, fontweight='bold')
        ax.set_xlabel('Суммарное время (дн)', fontsize=9)
        ax.set_ylabel('Состояние', fontsize=9)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(STATE_NAMES, fontsize=9)
        ax.set_ylim(-0.5, 2.5)
        ax.yaxis.grid(True, alpha=0.25, linestyle='--')

        history = self.model.history  # [(t_in, state, duration), ...]
        if not history:
            return

        MAX_EVT = 50
        h = history[-MAX_EVT:]

        # Рисую завершённые интервалы пребывания
        prev_s = None
        for (t_in, state, dur) in h:
            t_out = t_in + dur
            ax.axvspan(t_in, t_out, color=STATE_COLORS[state], alpha=0.35, lw=0)
            ax.hlines(state, t_in, t_out, colors='#111827', linewidth=2.2)
            # Вертикальная линия при смене состояния
            if prev_s is not None and prev_s != state:
                lo, hi = min(prev_s, state), max(prev_s, state)
                ax.vlines(t_in, lo, hi, colors='#111827', linewidth=2.2)
            prev_s = state

        # Текущее состояние - пунктиром (ещё не завершено)
        curr  = self.model.current_state
        t_now = self.model.total_time
        window_w = t_now - h[0][0]
        t_ext    = t_now + max(0.5, window_w * 0.12)

        ax.axvspan(t_now, t_ext, color=STATE_COLORS[curr], alpha=0.15, lw=0)
        ax.hlines(curr, t_now, t_ext, colors='#555555', linewidth=1.5, linestyle='--')
        if prev_s is not None and prev_s != curr:
            lo, hi = min(prev_s, curr), max(prev_s, curr)
            ax.vlines(t_now, lo, hi, colors='#111827', linewidth=2.2)

        ax.set_xlim(h[0][0], t_ext + 0.1)

    def _plot_bar(self):
        """График 2: сравнение эмпирических и теоретических долей времени."""
        ax = self._ax_bar
        ax.clear()

        emp = self.model.get_empirical_fractions()
        sta = self.model.compute_stationary_distribution()

        x, w = np.arange(3), 0.35
        b1 = ax.bar(x - w/2, emp, w, color=BAR_EMP_COLOR, label='Эмпирич. (время)', zorder=3)
        b2 = ax.bar(x + w/2, sta, w, color=BAR_STA_COLOR, label='Теорет. (Q-стац)',  zorder=3)

        for bar in (*b1, *b2):
            val = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, val + 0.012,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=8, color='#111827')

        ax.set_xticks(x)
        ax.set_xticklabels(STATE_NAMES, fontsize=9)
        ax.set_ylabel('Доля времени', fontsize=9)
        ax.set_ylim(0, 1.10)
        ax.set_title('Распределение времени в состояниях', fontsize=10, fontweight='bold')
        ax.legend(fontsize=8, framealpha=0.8)
        ax.yaxis.grid(True, alpha=0.25, linestyle='--', zorder=0)
        ax.set_axisbelow(True)

    def _plot_convergence(self):
        """График 3: сходимость бегущих долей к стационарному распределению."""
        ax = self._ax_conv
        ax.clear()

        sta = self.model.compute_stationary_distribution()

        for i in range(3):
            fracs = self.model.running_fractions[i]
            if fracs:
                ax.plot(range(1, len(fracs) + 1), fracs,
                        color=CONV_COLORS[i], label=STATE_NAMES[i], linewidth=1.6)
            # Теоретическое значение - горизонтальная пунктирная линия
            ax.axhline(y=sta[i], color=CONV_COLORS[i],
                       linestyle='--', linewidth=1.0, alpha=0.65)

        ax.set_xlabel('Количество переходов', fontsize=9)
        ax.set_ylabel('Доля накопленного времени', fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.set_title('Сходимость к Q-стационарному', fontsize=10, fontweight='bold')
        ax.yaxis.grid(True, alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)

        if self.model.n_transitions > 0:
            ax.legend(fontsize=8, framealpha=0.8)


# Точка входа

if __name__ == '__main__':
    app = MarkovApp()
    app.mainloop()
