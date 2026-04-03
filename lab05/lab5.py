import tkinter as tk
import random

# Окошечко
root = tk.Tk()
root.title("ЖЕСТЬ магия")
root.geometry("400x500")
root.resizable(False, False) 
root.configure(bg="#2b2b2b") 

# Функция для переключения вкладок
def show_frame(frame):
    frame.tkraise()

# Верхняя панель для кнопок переключения
nav_frame = tk.Frame(root, bg="#1e1e1e")
nav_frame.pack(side="top", fill="x")

# Контейнер, где будут лежать сами вкладки (одна поверх другой)
container = tk.Frame(root, bg="#2b2b2b")
container.pack(fill="both", expand=True)
container.grid_rowconfigure(0, weight=1)
container.grid_columnconfigure(0, weight=1)

# Создаем два фрейма
frame_yn = tk.Frame(container, bg="#2b2b2b")
frame_8b = tk.Frame(container, bg="#2b2b2b")

# Кладем их в одну ячейку сетки, чтобы они перекрывали друг друга
for f in (frame_yn, frame_8b):
    f.grid(row=0, column=0, sticky="nsew")

# Кнопки навигации
btn_nav_yn = tk.Button(nav_frame, text="Да / Нет", font=("Arial", 12, "bold"), 
                       command=lambda: show_frame(frame_yn), bg="#444", fg="white", relief="flat")
btn_nav_yn.pack(side="left", expand=True, fill="x", padx=1, pady=1)

btn_nav_8b = tk.Button(nav_frame, text="8-Шар", font=("Arial", 12, "bold"), 
                       command=lambda: show_frame(frame_8b), bg="#444", fg="white", relief="flat")
btn_nav_8b.pack(side="left", expand=True, fill="x", padx=1, pady=1)


# ЛАБА 1: "Да/Нет"
lbl_yn = tk.Label(frame_yn, text="?", font=("Arial", 80, "bold"), bg="#2b2b2b", fg="#00ffcc")
lbl_yn.pack(pady=100)

def roll_yes_no():
    # 1 Получаем значение от базового датчика
    # random.random() генерирует псевдослучайное число alpha
    alpha = random.random()
    
    # 2 Моделируем наступление события A
    # Вероятность наступления p = 0.5
    p = 0.5
    
    # 3 Если alpha попадает в отрезок [0; p), событие наступило
    if alpha < p:
        lbl_yn.config(text="Ага", fg="#00ff00") 
    else:
        # Если alpha >= p, наступило противоположное событие
        lbl_yn.config(text="Не ага", fg="#ff3333") 

# Кнопка
btn_yn = tk.Button(frame_yn, text="Ну и шо?", font=("Arial", 20, "bold"), 
                   command=roll_yes_no, bg="#555", fg="white", relief="flat", padx=20, pady=10)
btn_yn.pack()


# ЛАБА 2: "8-Шар"
# Шар типо
canvas = tk.Canvas(frame_8b, width=300, height=300, bg="#2b2b2b", highlightthickness=0)
canvas.pack(pady=40)

canvas.create_oval(10, 10, 290, 290, fill="#111111", outline="#000")
canvas.create_oval(70, 70, 230, 230, fill="#eeeeee", outline="#ccc")

# Текст внутри шара (по умолчанию "Жми!")
text_8b = canvas.create_text(150, 150, text="Жми\nна шар!", font=("Arial", 14, "bold"), 
                             justify="center", fill="#111", width=140)

# Полная группа попарно несовместных событий
answers = [
    "Да", "Нет", "Скорее всего", "Сомнительно", 
    "Без сомнений", "Спроси позже", "Определенно да", "Маловероятно"
]

def roll_magic_ball(event):
    # 1 Обращаемся к базовому датчику
    alpha = random.random()
    
    # 2 Так как события равновероятны, вычисляем P_k для каждого
    # Ответов  8 => p_k = 1/m = 0.125
    m = len(answers)
    p_k = 1.0 / m
    
    # 3 Алгоритм поиска интервала, куда попало число alpha
    # Разбиваем отрезок [0, 1] на m интервалов длиной p_k.
    cumulative_probability = 0.0 # Верхняя граница текущего интервала
    
    for i in range(m):
        # Сдвигаем границу вправо на p_k
        cumulative_probability += p_k
        
        # Проверяем, попало ли сгенерированное alpha в текущий интервал
        if alpha < cumulative_probability:
            # Если попало — событие под номером i свершилось. Выводим текст и прерываем цикл
            canvas.itemconfig(text_8b, text=answers[i])
            break

canvas.bind("<Button-1>", roll_magic_ball)

show_frame(frame_yn)

root.mainloop()