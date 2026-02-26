import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

#Параметры задачи
L = 0.03          # Длина пластины (м)
T0 = 20.0        # Начальная температура
T_left = 300.0   # Граничное условие слева (x=0)
T_right = 50.0   # Граничное условие справа (x=L)
rho = 7800.0     # Плотность (кг/м3)
c = 460.0        # Удельная теплоемкость (Дж/кг*К)
lam = 50.0       # Теплопроводность (Вт/м*К)
t_end = 2.0      # Конечное время моделирования (с)

# Алгоритм Томаса
def solve_tridiagonal(a, b, c, d):
    n = len(d)
    ac, bc, cc, dc = a.copy(), b.copy(), c.copy(), d.copy()
    for i in range(1, n):
        mc = ac[i-1] / bc[i-1]
        bc[i] -= mc * cc[i-1]
        dc[i] -= mc * dc[i-1]
    res = bc
    res[-1] = dc[-1] / bc[-1]
    for i in range(n-2, -1, -1):
        res[i] = (dc[i] - cc[i] * res[i+1]) / bc[i]
    return res

# Функция рассчёта
def simulate(dt, dx):
    nx = int(L / dx) + 1
    nt = int(t_end / dt)
    T = np.full(nx, T0)
    T[0], T[-1] = T_left, T_right
    
    # Ai*T[i+1] - Bi*T[i] + Ci*T[i-1] = Fi
    # Преобразуем: -Ci*T[i-1] + Bi*T[i] - Ai*T[i+1] = -Fi
    A_val = lam / (dx**2)
    C_val = lam / (dx**2)
    B_val = (2 * lam / (dx**2)) + (rho * c / dt)
    
    # Формируем диагонали (для внутренних точек i=1 - nx-2)
    main_diag = np.full(nx - 2, B_val)
    off_diag = np.full(nx - 3, -A_val) # Верхняя и нижняя одинаковы (Ai=Ci)
    coeff_const = (rho * c / dt)

    for _ in range(nt):
        # Правая часть Fi = -(rho*c/dt) * T_old
        rhs = coeff_const * T[1:-1]

        # Коррекция краев для СЛАУ
        rhs[0] += C_val * T[0]
        rhs[-1] += A_val * T[-1]

        # Решаем систему для внутренних точек
        T[1:-1] = solve_tridiagonal(off_diag, main_diag, off_diag, rhs)
    
    # Возвращаем температуру в центре
    return T[nx // 2], np.linspace(0, L, nx), T

# Интерфейс...
root = tk.Tk()
root.title("Теплопроводность - Испытания")
root.geometry("1100x700")

top_frame = tk.Frame(root)
top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

# Таблица результатов
cols = ("Шаг t \ Шаг x", "0.1", "0.01", "0.001", "0.0001")
tree = ttk.Treeview(top_frame, columns=cols, show='headings', height=5)
for col in cols:
    tree.heading(col, text=col)
    tree.column(col, width=150, anchor="center")
tree.pack(side=tk.LEFT)

fig, ax = plt.subplots(figsize=(6, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

status_label = tk.Label(root, text="Нажмите 'Запустить', чтобы начать", fg="blue")
status_label.pack()

def calculation_thread():
    """Функция для работы в фоновом потоке"""
    dt_steps = [0.1, 0.01, 0.001, 0.0001]
    dx_steps = [0.1, 0.01, 0.001, 0.0001]
    
    btn_run.config(state=tk.DISABLED) # Отключаем кнопку на время расчета
    
    for dt in dt_steps:
        row_values = [dt]
        for dx in dx_steps:
            root.after(0, lambda d=dt, x=dx: status_label.config(text=f"Считаю: dt={d}, dx={x}..."))
            try:
                temp_mid, x_vals, t_vals = simulate(dt, dx)
                row_values.append(f"{temp_mid:.4f}")
                
                # Обновляем график для текущего dx при dt=0.001 (самый наглядный)
                if dt == 0.001:
                    def update_plot(xv=x_vals, tv=t_vals, dxx=dx):
                        ax.plot(xv, tv, label=f"dx={dxx}")
                        ax.legend()
                        canvas.draw()
                    root.after(0, update_plot)
                    
            except Exception as e:
                row_values.append("Ошибка")
        
        # Добавляем строку в таблицу через очередь основного потока
        root.after(0, lambda rv=row_values: tree.insert("", tk.END, values=rv))

    root.after(0, lambda: status_label.config(text="Расчет завершен!", fg="green"))
    root.after(0, lambda: btn_run.config(state=tk.NORMAL))

def start_task():
    # Очистка перед новым запуском
    for i in tree.get_children(): tree.delete(i)
    ax.clear()
    ax.set_title("Распределение температуры (t=2с)")
    ax.grid(True)
    # Запуск потока
    threading.Thread(target=calculation_thread, daemon=True).start()

btn_run = tk.Button(top_frame, text="Запустить расчет", command=start_task, bg="green", fg="white")
btn_run.pack(side=tk.LEFT, padx=20)

root.mainloop()
