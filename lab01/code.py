import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

G = 9.81

class Modelka:
    def __init__(self, root):
        self.root = root
        self.root.title("Моделирование полета тела в атмосфере")
        self.root.geometry("1200x800")

        #список для хранения результатов всех запусков
        self.results_data = []

        #левая панель
        self.ctrl_panel = ttk.Frame(root, padding="10")
        self.ctrl_panel.pack(side=tk.LEFT, fill=tk.Y)

        def create_input(label_text, default_val):
            frame = ttk.Frame(self.ctrl_panel)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
            entry = ttk.Entry(frame)
            entry.insert(0, str(default_val))
            entry.pack(side=tk.RIGHT, expand=True)
            return entry

        self.entry_v0 = create_input("Нач. скорость (м/с):", 50)
        self.entry_angle = create_input("Угол (градусы):", 45)
        self.entry_m = create_input("Масса (кг):", 1.0)
        self.entry_S = create_input("Площадь сечения (м²):", 0.01)
        self.entry_C = create_input("Коэф. лоб. сопр. C:", 0.15)
        self.entry_rho = create_input("Плотность воздуха ρ:", 1.29)
        self.entry_step = create_input("Шаг моделирования (с):", 0.01)

        ttk.Separator(self.ctrl_panel, orient='horizontal').pack(fill=tk.X, pady=10)

        self.btn_run = ttk.Button(self.ctrl_panel, text="Запустить симуляцию", command=self.run_single)
        self.btn_run.pack(fill=tk.X, pady=2)

        self.btn_run_all = ttk.Button(self.ctrl_panel, text="Запустить все симуляции", command=self.run_all_steps)
        self.btn_run_all.pack(fill=tk.X, pady=2)

        self.btn_clear = ttk.Button(self.ctrl_panel, text="Очистить всё", command=self.clear_all)
        self.btn_clear.pack(fill=tk.X, pady=2)

        #правая панель
        self.view_panel = ttk.Frame(root, padding="10")
        self.view_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # График
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title("Траектории полета тела")
        self.ax.set_xlabel("Дистанция (м)")
        self.ax.set_ylabel("Высота (м)")
        self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.view_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Таблица
        columns = ("step", "range", "height", "velocity")
        self.tree = ttk.Treeview(self.view_panel, columns=columns, show='headings', height=6)
        self.tree.heading("step", text="Шаг (с)")
        self.tree.heading("range", text="Дальность (м)")
        self.tree.heading("height", text="Максимальая высота (м)")
        self.tree.heading("velocity", text="Конечная скорость (м/с)")
        self.tree.pack(fill=tk.X, pady=5)

    def solve_rk4(self, h, v0, angle, m, S, C, rho):
        """Решение системы методом Рунге-Кутты 4-го порядка"""
        k = (C * S * rho) / (2 * m) #коэффициент сопротивления
        alpha_rad = np.radians(angle) #перевод градусов в радианы

        #состояние: [x, y, vx, vy]
        state = np.array([0.0, 0.0, v0 * np.cos(alpha_rad), v0 * np.sin(alpha_rad)])

        def derivatives(s):
            vx, vy = s[2], s[3] #достаем текущие скорости
            v = np.sqrt(vx ** 2 + vy ** 2) #считаем общую скорость
            ax = -k * vx * v #ускорение по X
            ay = -G - k * vy * v #ускорение по Y
            return np.array([vx, vy, ax, ay]) #возвращаем скорость изменения состояния

        trajectory_x = [state[0]]
        trajectory_y = [state[1]]
        max_height = 0.0

        #моделируем до падения
        while state[1] >= 0:
            k1 = derivatives(state)
            k2 = derivatives(state + h / 2 * k1)
            k3 = derivatives(state + h / 2 * k2)
            k4 = derivatives(state + h * k3)

            state = state + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

            if state[1] < 0: break  #таки падение

            trajectory_x.append(state[0])
            trajectory_y.append(state[1])
            if state[1] > max_height:
                max_height = state[1]

        final_velocity = np.sqrt(state[2] ** 2 + state[3] ** 2)
        return trajectory_x, trajectory_y, max_height, state[0], final_velocity

    def run_simulation(self, h):
        try:
            v0 = float(self.entry_v0.get())
            angle = float(self.entry_angle.get())
            m = float(self.entry_m.get())
            S = float(self.entry_S.get())
            C = float(self.entry_C.get())
            rho = float(self.entry_rho.get())
        except ValueError:
            messagebox.showerror("Не-а)))))))", "Введите корректные числовые значения")
            return

        tx, ty, mh, dist, fv = self.solve_rk4(h, v0, angle, m, S, C, rho)

        #вывод на график
        self.ax.plot(tx, ty, label=f"h={h}")
        self.ax.legend()
        self.canvas.draw()

        #вывод в таблицу
        row = (h, f"{dist:.4f}", f"{mh:.4f}", f"{fv:.4f}")
        self.tree.insert("", tk.END, values=row)

    def run_single(self):
        h = float(self.entry_step.get())
        self.run_simulation(h)

    def run_all_steps(self):
        steps = [1, 0.1, 0.01, 0.001, 0.0001]
        for h in steps:
            self.run_simulation(h)

    def clear_all(self):
        self.ax.clear()
        self.ax.set_title("Траектории полета")
        self.ax.set_xlabel("Дистанция (м)")
        self.ax.set_ylabel("Высота (м)")
        self.ax.grid(True)
        self.canvas.draw()
        for item in self.tree.get_children():
            self.tree.delete(item)


#создание и запуск приложения
root = tk.Tk()
app = Modelka(root)
root.mainloop() #бесконечный цикл
