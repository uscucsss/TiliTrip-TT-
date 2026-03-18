import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import pygame #pip install pygame-ce

class TiliTripApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TiliTrip - Планировщик путешествий")
        self.root.geometry("600x500")

        pygame.mixer.init()
        self.play_sound("start.mp3")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.init_db()
        self.create_widgets()
        self.update_trip_list()
    def play_sound(self, filename):
        #Проигрывает звук
        try:
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Ошибка воспроизведения звука {filename}: {e}")

    def on_closing(self):
            #Логика при закрытия программы
            self.play_sound("shutdown.mp3")
            self.root.after(1000,self.root.destroy)

    
    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, FOREIGN KEY(trip_id) REFERENCES trips(id))''')
        self.conn.commit()

    def create_widgets(self):
        # Секция 1 создание поездки
        frame_add = ttk.LabelFrame(self.root, text="Новое путешествие")
        frame_add.pack(fill="x", padx=10, pady=5)
        ttk.Label(frame_add, text="Название:").grid(column=0, row=0, padx=5, pady=5)
        self.entry_trip_name = ttk.Entry(frame_add)
        self.entry_trip_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_add, text="Дата (ГГГГ-ММ-ДД):").grid(row=0, column=2, padx=5, pady=5)
        self.entry_trip_date = ttk.Entry(frame_add)
        self.entry_trip_date.grid(row=0, column=3, padx=5, pady=5)

        btn_add_trip = ttk.Button(frame_add, text="Создать", command=self.add_trip)
        btn_add_trip.grid(row=0, column=4, padx=5, pady=5)

        # --- Секция 2: Список поездок и детализация ---
        self.tree = ttk.Treeview(self.root, columns=("ID", "Название", "Дата"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Название", text="Поездка")
        self.tree.heading("Дата", text="Начало")
        self.tree.column("ID", width=30)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_trip_select)

        # --- Секция 3: Добавление мест по дням ---
        self.frame_details = ttk.LabelFrame(self.root, text="План по дням (выберите поездку выше)")
        self.frame_details.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.frame_details, text="Город/Место:").grid(row=0, column=0, padx=5, pady=2)
        self.entry_city = ttk.Entry(self.frame_details)
        self.entry_city.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(self.frame_details, text="День №:").grid(row=0, column=2, padx=5, pady=2)
        self.entry_day = ttk.Entry(self.frame_details, width=5)
        self.entry_day.grid(row=0, column=3, padx=5, pady=2)

        btn_add_loc = ttk.Button(self.frame_details, text="+ Добавить в план", command=self.add_location)
        btn_add_loc.grid(row=0, column=4, padx=5, pady=2)

        self.list_plan = tk.Listbox(self.root, height=6)
        self.list_plan.pack(fill="x", padx=10, pady=5)

    def add_trip(self):
        name = self.entry_trip_name.get()
        date = self.entry_trip_date.get()
        if name and date:
            self.cursor.execute("INSERT INTO trips (name, start_date) VALUES (?, ?)", (name, date))
            self.conn.commit()

            self.play_sound("success.mp3")
            
            self.update_trip_list()
            self.entry_trip_name.delete(0, tk.END)
            self.entry_trip_date.delete(0, tk.END)
        else:
            messagebox.showwarning("Ошибка", "Заполните название и дату")

    def update_trip_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.cursor.execute("SELECT * FROM trips")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def on_trip_select(self, event):
        self.update_plan_list()

    def update_plan_list(self):
        self.list_plan.delete(0, tk.END)
        selected = self.tree.selection()
        if not selected: return

        trip_id = self.tree.item(selected[0])['values'][0]
        self.cursor.execute("SELECT city, day_number FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        for city, day in self.cursor.fetchall():
            self.list_plan.insert(tk.END, f"День {day}: {city}")

    def add_location(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Сначала выберите поездку в списке")
            return

        trip_id = self.tree.item(selected[0])['values'][0]
        city = self.entry_city.get()
        day = self.entry_day.get()

        if city and day.isdigit():
            self.cursor.execute("INSERT INTO locations (trip_id, city, day_number) VALUES (?, ?, ?)",
                                (trip_id, city, int(day)))
            self.conn.commit()
            self.update_plan_list()
            self.entry_city.delete(0, tk.END)
            self.entry_day.delete(0, tk.END)
        else:
            messagebox.showwarning("Ошибка", "Введите название места и номер дня")


if __name__ == "__main__":
    root = tk.Tk()
    app = TiliTripApp(root)
    root.mainloop()
