import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib
matplotlib.use('TkAgg')  
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Импортирую логику из соседнего файла
from markov_logic import MarkovWeatherModel


# Цветовая схема и константы

STATE_COLORS = ['#FFD700', '#87CEEB', '#778899']

CONV_COLORS  = ['#B8860B', '#2171B5', '#525252']

BAR_EMP_COLOR = '#64B5F6'   # эмпирика - синеватый
BAR_STA_COLOR = '#EF9A9A'   # теория   - розоватый

STATE_BADGE_STYLE = [
    ('#7B5800', '#FFF3CD'),  
    ('#0A3D6B', '#DBEAFE'),  
    ('#2C2C2C', '#D1D5DB'),  
]

STATE_NAMES = ['Ясно', 'Облачно', 'Пасмурно']


# Главное окно приложения

class MarkovApp(tk.Tk):
    """Главное окно - вся интеграция GUI и модели."""

    def __init__(self):
        super().__init__()
        self.title('Марковская модель погоды (ДЦМ)')

        self._maximize_window()

        # Создаю объект модели (из markov_logic.py)
        self.model = MarkovWeatherModel()

        # Флаг работы симуляции и id запланированного after()-вызова
        self.running   = False
        self._after_id = None

        # Строю весь интерфейс
        self._build_layout()

        # Начальное отображение (нулевые счётчики + пустые графики)
        self._update_ui()
        self._redraw_plots()

    def _maximize_window(self):
        """Раскрываю окно на весь экран"""
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
        """Двухколоночная компоновка: левая панель - управление, правая - графики."""
        self.columnconfigure(0, weight=0, minsize=375)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Левая панель (фиксированная ширина)
        left = tk.Frame(self, bd=1, relief='groove', bg='#F9FAFB')
        left.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)

        # Правая панель (растягивается)
        right = tk.Frame(self, bg='white')
        right.grid(row=0, column=1, sticky='nsew', padx=(4, 8), pady=8)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_control_panel(left)
        self._build_plot_panel(right)

    # -Левая панель: управление

    def _build_control_panel(self, p):
        """Строю все элементы управления на левой панели."""
        kw = dict(bg='#F9FAFB')

        # Заголовок
        tk.Label(p, text='Марковская модель погоды',
                 font=('Segoe UI', 13, 'bold'), **kw).pack(padx=10, pady=(10, 1))
        tk.Label(p, text='Дискретная цепь Маркова (ДЦМ)  |  1 шаг = 1 день',
                 font=('Segoe UI', 8, 'italic'), fg='#6B7280', **kw).pack()

        self._sep(p)
        self._build_matrix_section(p, kw)
        self._sep(p)
        self._build_state_section(p, kw)
        self._sep(p)
        self._build_buttons_section(p)
        self._sep(p)
        self._build_speed_section(p, kw)
        self._sep(p)

        # Кнопка сохранения CSV
        tk.Button(p, text='💾   Сохранить статистику в CSV',
                  command=self._save_csv,
                  bg='#D97706', fg='white',
                  activebackground='#B45309', activeforeground='white',
                  font=('Segoe UI', 10, 'bold'),
                  pady=7, relief='flat', cursor='hand2'
                  ).pack(fill='x', padx=12, pady=(4, 2))

        tk.Label(p, text='Файлы сохраняются в папку ./output/',
                 font=('Segoe UI', 8), fg='#9CA3AF', **kw).pack(pady=(0, 6))

    def _build_matrix_section(self, p, kw):
        """Таблица для ввода матрицы переходных вероятностей P."""
        tk.Label(p, text='Матрица переходов P  (вероятности):',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(padx=10, pady=(4, 0))
        tk.Label(p,
                 text='P[i][j] >= 0 - вероятность перейти из i в j за 1 день\n'
                      'Строки нормируются автоматически (сумма = 1)',
                 font=('Segoe UI', 8), fg='#6B7280', justify='left', **kw).pack(padx=12)

        # Сетка 3x3 - все ячейки редактируемые (диагональ тоже)
        mf = tk.Frame(p, bg='#F9FAFB')
        mf.pack(pady=4)

        # Шапка столбцов
        tk.Label(mf, text='', width=9, bg='#F9FAFB').grid(row=0, column=0)
        for j, name in enumerate(STATE_NAMES):
            tk.Label(mf, text=name, width=9, font=('Segoe UI', 9, 'bold'),
                     fg=self._text_color(STATE_COLORS[j]), bg='#F9FAFB'
                     ).grid(row=0, column=j + 1, padx=2)

        # Ячейки матрицы - все 9 редактируемые
        self._p_vars = []   # StringVar[3][3]

        # Значения по умолчанию: P = I + Q из слайдов
        defaults = [
            ['0.600', '0.300', '0.100'],
            ['0.400', '0.200', '0.400'],
            ['0.100', '0.400', '0.500'],
        ]

        for i in range(3):
            row_vars = []

            # Метка строки
            tk.Label(mf, text=STATE_NAMES[i], width=9,
                     font=('Segoe UI', 9, 'bold'),
                     fg=self._text_color(STATE_COLORS[i]),
                     bg='#F9FAFB').grid(row=i + 1, column=0)

            for j in range(3):
                var = tk.StringVar(value=defaults[i][j])
                e = tk.Entry(mf, textvariable=var, width=9,
                             justify='center', font=('Courier', 9),
                             relief='solid', bd=1)
                e.grid(row=i + 1, column=j + 1, padx=2, pady=2)
                row_vars.append(var)

            self._p_vars.append(row_vars)

        # Кнопка применить (нормализует строки и обновляет модель)
        tk.Button(p, text='✔  Применить матрицу',
                  command=self._apply_matrix,
                  bg='#065F46', fg='white',
                  activebackground='#047857', activeforeground='white',
                  font=('Segoe UI', 9, 'bold'),
                  relief='flat', pady=5, cursor='hand2'
                  ).pack(padx=12, pady=(2, 4), fill='x')

    def _build_state_section(self, p, kw):
       # Текущее состояние, день, счётчики по состояниям.
        tk.Label(p, text='Текущее состояние:',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(pady=(4, 2))

        # Крупный лейбл с текущим состоянием
        self._state_lbl = tk.Label(p, text='Ясно',
                                   font=('Segoe UI', 16, 'bold'),
                                   width=17, pady=6, relief='ridge')
        self._state_lbl.pack(padx=20, pady=2)

        # Счётчики: день и количество переходов
        tf = tk.Frame(p, bg='#F9FAFB')
        tf.pack(padx=14, pady=(4, 2), fill='x')
        tf.columnconfigure(0, weight=1)
        tf.columnconfigure(1, weight=0)

        for row_idx, (label_text, attr) in enumerate([
            ('Текущий день:', '_day_lbl'),
        ]):
            tk.Label(tf, text=label_text, font=('Segoe UI', 9),
                     anchor='w', bg='#F9FAFB').grid(row=row_idx, column=0, sticky='w')
            lbl = tk.Label(tf, text='0', font=('Segoe UI', 11, 'bold'),
                           anchor='e', bg='#F9FAFB')
            lbl.grid(row=row_idx, column=1, sticky='e')
            setattr(self, attr, lbl)

        # Счётчики дней по состояниям
        tk.Label(p, text='Дней по состояниям:',
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
                     anchor='w', bg='#F9FAFB', width=12
                     ).grid(row=i, column=0, sticky='w', pady=1)
            lbl = tk.Label(cf, text='0 дн.', font=('Segoe UI', 9),
                           anchor='e', bg='#F9FAFB')
            lbl.grid(row=i, column=1, sticky='e', pady=1)
            self._cnt_lbls.append(lbl)

    def _build_buttons_section(self, p):
       # Кнопки Старт / Стоп / Сброс.
        bf = tk.Frame(p, bg='#F9FAFB')
        bf.pack(pady=6)

        # Старт
        self._btn_start = tk.Button(
            bf, text='▶  Старт', width=9,
            bg='#1D4ED8', fg='white',
            activebackground='#1E40AF', activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat', pady=5, cursor='hand2',
            command=self._start)
        self._btn_start.grid(row=0, column=0, padx=5)

        # Стоп
        self._btn_stop = tk.Button(
            bf, text='⏸  Стоп', width=9,
            bg='#B91C1C', fg='white',
            activebackground='#991B1B', activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat', pady=5, cursor='hand2',
            state='disabled',
            command=self._stop)
        self._btn_stop.grid(row=0, column=1, padx=5)

        # Сброс
        tk.Button(
            bf, text='↺  Сброс', width=9,
            bg='#374151', fg='white',
            activebackground='#1F2937', activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat', pady=5, cursor='hand2',
            command=self._reset
        ).grid(row=0, column=2, padx=5)

    def _build_speed_section(self, p, kw):
       # Ползунок скорости (задержка между шагами в мс).
        tk.Label(p, text='Задержка между шагами:',
                 font=('Segoe UI', 10, 'bold'), **kw).pack(pady=(4, 0))

        sf = tk.Frame(p, bg='#F9FAFB')
        sf.pack(padx=10, fill='x')

        tk.Label(sf, text='50\nмс', font=('Segoe UI', 8),
                 fg='#6B7280', bg='#F9FAFB').pack(side='left')

        self._speed_var = tk.IntVar(value=500)
        ttk.Scale(sf, from_=50, to=2000, orient='horizontal',
                  variable=self._speed_var, length=220
                  ).pack(side='left', fill='x', expand=True, padx=6)

        tk.Label(sf, text='2000\nмс', font=('Segoe UI', 8),
                 fg='#6B7280', bg='#F9FAFB').pack(side='left')

        self._speed_lbl = tk.Label(p, text='500 мс',
                                   font=('Segoe UI', 11, 'bold'),
                                   fg='#1D4ED8', **kw)
        self._speed_lbl.pack(pady=(0, 4))
        # Слежу за изменениями ползунка и обновляю подпись
        self._speed_var.trace_add('write', self._on_speed_change)

    #  Правая панель: графики 

    def _build_plot_panel(self, p):
        """Встраиваю matplotlib-фигуру с тремя субграфиками."""
        self._fig = Figure(figsize=(12, 8), dpi=90)
        self._fig.patch.set_facecolor('white')
        self._fig.subplots_adjust(
            hspace=0.44, wspace=0.30,
            left=0.07, right=0.97,
            top=0.94, bottom=0.08
        )

        # Верхний - поток состояний (оба столбца)
        self._ax_stream = self._fig.add_subplot(2, 2, (1, 2))

        # Нижний левый - столбчатая диаграмма
        self._ax_bar = self._fig.add_subplot(2, 2, 3)

        # Нижний правый - сходимость к стационарному
        self._ax_conv = self._fig.add_subplot(2, 2, 4)

        # Встраиваю matplotlib canvas в tkinter
        self._canvas = FigureCanvasTkAgg(self._fig, master=p)
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

    # =========================
    # Вспомогательные методы

    @staticmethod
    def _sep(parent):
        """Горизонтальный разделитель."""
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=8, pady=4)

    @staticmethod
    def _text_color(hex_color, factor=0.55):
        """Затемняю hex-цвет для использования в тексте поверх светлого фона."""
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}'

    # ==========================
    # Обработчики событий

    def _apply_matrix(self):
        """Считываю матрицу P из полей ввода и передаю в модель."""
        try:
            mat = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    raw = self._p_vars[i][j].get().strip().replace(',', '.')
                    val = float(raw)
                    if val < 0:
                        raise ValueError(
                            f'P[{STATE_NAMES[i]}->{STATE_NAMES[j]}]'
                            f' = {val} - вероятность не может быть отрицательной!'
                        )
                    mat[i, j] = val
            self.model.set_transition_matrix(mat)
            # Показываю нормированные значения обратно в полях ввода
            P = self.model.get_P_display()
            for i in range(3):
                for j in range(3):
                    self._p_vars[i][j].set(f'{P[i, j]:.3f}')
            return True
        except ValueError as e:
            messagebox.showerror('Ошибка ввода', str(e))
            return False

    def _start(self):
        """Запускаю моделирование."""
        if not self._apply_matrix():
            return
        self.running = True
        self._btn_start.config(state='disabled')
        self._btn_stop.config(state='normal')
        self._tick()

    def _stop(self):
        """Останавливаю моделирование."""
        self.running = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')

    def _reset(self):
        """Сбрасываю модель в начальное состояние."""
        self._stop()
        self.model.reset()
        self._update_ui()
        self._redraw_plots()

    def _tick(self):
        """Один шаг симуляции. После выполнения планирует следующий вызов через after()."""
        if not self.running:
            return

        # Выполняю один день ДЦМ
        self.model.step()

        # Обновляю лейблы (быстрая операция - каждый шаг)
        self._update_ui()

        # Перерисовываю графики реже: matplotlib - дорогая операция.
        # Чем быстрее скорость, тем больше шагов пропускаем между кадрами.
        n     = self.model.day
        speed = self._speed_var.get()
        # Обновляю примерно каждые 120 мс реального времени
        skip_frames = max(1, 120 // speed)
        if n % skip_frames == 0 or n <= 20:
            self._redraw_plots()

        # Планирую следующий шаг через speed мс
        self._after_id = self.after(speed, self._tick)

    def _on_speed_change(self, *_):
        """Обновляю текстовую подпись ползунка скорости."""
        self._speed_lbl.config(text=f'{self._speed_var.get()} мс')

    def _save_csv(self):
        """Сохраняю статистику в CSV и показываю диалог с результатом."""
        if self.model.day == 0:
            messagebox.showwarning(
                'Нет данных',
                'Сначала запустите моделирование хотя бы на несколько шагов.'
            )
            return
        paths = self.model.save_to_csv('output')
        messagebox.showinfo(
            'Готово',
            'Файлы успешно сохранены:\n\n' + '\n'.join(paths)
        )

    # ===================
    # Обновление UI

    def _update_ui(self):
        """Обновляю лейблы состояния, дня и счётчиков."""
        s = self.model.current_state
        fg, bg = STATE_BADGE_STYLE[s]
        self._state_lbl.config(text=STATE_NAMES[s], fg=fg, bg=bg)
        self._day_lbl.config(text=str(self.model.day))
        for i in range(3):
            self._cnt_lbls[i].config(text=f'{self.model.state_counts[i]} дн.')

    # ====================
    # Графики matplotlib

    def _redraw_plots(self):
        """Перерисовываю все три графика и обновляю canvas."""
        self._plot_stream()
        self._plot_bar()
        self._plot_convergence()
        # draw_idle() безопаснее draw() внутри event loop - не вызывает рекурсию
        self._canvas.draw_idle()

    def _plot_stream(self):
        """
        График 1 (верхний): Непрерывный поток состояний.

        Рисую шаговую функцию: для каждого дня - горизонтальная полоса
        шириной 1 (один день) с цветной заливкой и линией уровня состояния.
        Вертикальными линиями показываю переходы между состояниями.
        Пунктирным отрезком показываю текущее состояние (начало следующего дня).
        """
        ax = self._ax_stream
        ax.clear()
        ax.set_title('Непрерывный поток состояний', fontsize=10, fontweight='bold')
        ax.set_xlabel('День', fontsize=9)
        ax.set_ylabel('Состояние', fontsize=9)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(STATE_NAMES, fontsize=9)
        ax.set_ylim(-0.5, 2.5)
        ax.yaxis.grid(True, alpha=0.25, linestyle='--')

        history = self.model.state_history  # [(day, state), ...]
        if not history:
            return

        # Показываю последние MAX_DAYS дней
        MAX_DAYS = 50
        h = history[-MAX_DAYS:]

        # Для каждого дня рисую прямоугольник шириной 1 день
        # День d занимает интервал [d-1, d] на оси x
        prev_s = None
        for (day, state) in h:
            t_in  = day - 1   # начало интервала дня d
            t_out = day       # конец  интервала дня d
            # Цветная полоса фона состояния
            ax.axvspan(t_in, t_out, color=STATE_COLORS[state], alpha=0.35, lw=0)
            # Горизонтальная линия уровня состояния внутри дня
            ax.hlines(state, t_in, t_out, colors='#111827', linewidth=2.2)
            # Вертикальная линия перехода (если состояние сменилось относительно предыдущего дня)
            if prev_s is not None and prev_s != state:
                lo, hi = min(prev_s, state), max(prev_s, state)
                ax.vlines(t_in, lo, hi, colors='#111827', linewidth=2.2)
            prev_s = state

        # Текущее состояние - пунктир на один следующий день
        curr  = self.model.current_state
        t_now = self.model.day          # конец последнего завершённого дня
        t_ext = t_now + 1               # показываю один день вперёд

        ax.axvspan(t_now, t_ext, color=STATE_COLORS[curr], alpha=0.15, lw=0)
        ax.hlines(curr, t_now, t_ext, colors='#555555',
                  linewidth=1.5, linestyle='--')

        # Вертикальная линия входа в текущее состояние
        if prev_s is not None and prev_s != curr:
            lo, hi = min(prev_s, curr), max(prev_s, curr)
            ax.vlines(t_now, lo, hi, colors='#111827', linewidth=2.2)

        # Настраиваю диапазон оси x: от начала первого показанного дня до конца пунктира
        first_day = h[0][0]
        ax.set_xlim(first_day - 1, t_ext + 0.15)

    def _plot_bar(self):
        """
        График 2 (нижний левый): Сравнение эмпирической и теоретической долей дней.

        Два столбца рядом для каждого состояния:
            - синий  = state_counts[i] / day  (сколько дней провели в состоянии i)
            - розовый = pi[i] из solve(pi*P=pi, sum=1)
        """
        ax = self._ax_bar
        ax.clear()

        emp = self.model.get_empirical_fractions()
        sta = self.model.compute_stationary_distribution()

        x = np.arange(3)
        w = 0.35

        b1 = ax.bar(x - w / 2, emp, w, color=BAR_EMP_COLOR, label='Эмпирич. (время)', zorder=3)
        b2 = ax.bar(x + w / 2, sta, w, color=BAR_STA_COLOR, label='Теорет. (Q-стац)',  zorder=3)

        # Подписи значений над столбцами
        for bar in (*b1, *b2):
            val = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2,
                    val + 0.012, f'{val:.2f}',
                    ha='center', va='bottom', fontsize=8, color='#111827')

        ax.set_xticks(x)
        ax.set_xticklabels(STATE_NAMES, fontsize=9)
        ax.set_ylabel('Доля дней', fontsize=9)
        ax.set_ylim(0, 1.10)
        ax.set_title('Распределение времени в состояниях',
                     fontsize=10, fontweight='bold')
        ax.legend(fontsize=8, framealpha=0.8)
        ax.yaxis.grid(True, alpha=0.25, linestyle='--', zorder=0)
        ax.set_axisbelow(True)

    def _plot_convergence(self):
        """
        График 3 (нижний правый): Сходимость бегущих долей к стационарному.

        Для каждого состояния рисую кривую running_fractions[i] vs день.
        Горизонтальными пунктирами показываю теоретические значения pi[i].
        По мере роста числа дней кривые должны сходиться к пунктирам.
        """
        ax = self._ax_conv
        ax.clear()

        sta = self.model.compute_stationary_distribution()

        for i in range(3):
            fracs = self.model.running_fractions[i]
            if fracs:
                xs = range(1, len(fracs) + 1)
                ax.plot(xs, fracs, color=CONV_COLORS[i],
                        label=STATE_NAMES[i], linewidth=1.6)
            # Теоретическая горизонтальная пунктирная линия
            ax.axhline(y=sta[i], color=CONV_COLORS[i],
                       linestyle='--', linewidth=1.0, alpha=0.65)

        ax.set_xlabel('Количество переходов', fontsize=9)
        ax.set_ylabel('Доля накопленного времени', fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.set_title('Сходимость к Q-стационарному', fontsize=10, fontweight='bold')
        ax.yaxis.grid(True, alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)

        if self.model.day > 0:
            ax.legend(fontsize=8, framealpha=0.8)


# =========================
# Точка входа

if __name__ == '__main__':
    app = MarkovApp()
    app.mainloop()
