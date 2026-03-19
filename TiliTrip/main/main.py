import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import pygame
import sys

class TiliTripApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TiliTrip - Планировщик путешествий")
        self.root.geometry("800x650")

        # Инициализация звука
        pygame.mixer.init()
        self.play_sound("start.mp3")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.init_db()
        self.create_widgets()
        self.update_trip_list()

    def resource_path(self, relative_path):
        """ Получает абсолютный путь к ресурсам (нужно для корректной работы звуков в EXE) """
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def play_sound(self, filename):
        try:
            path = self.resource_path(filename)
            if os.path.exists(path):
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Ошибка воспроизведения звука {filename}: {e}")

    def on_closing(self):
        self.play_sound("shutdown.mp3")
        # Небольшая задержка, чтобы звук успел начаться перед закрытием
        self.root.after(1000, self.root.destroy)

    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db')
        self.cursor = self.conn.cursor()
        # Таблица поездок (с учетом города вылета)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trips 
                            (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT)''')
        # Таблица локаций
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations 
                            (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, 
                            FOREIGN KEY(trip_id) REFERENCES trips(id))''')
        self.conn.commit()

    def create_widgets(self):
        # --- Секция 1: Управление поездкой ---
        frame_add = ttk.LabelFrame(self.root, text="Параметры путешествия")
        frame_add.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_add, text="Название:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_trip_name = ttk.Entry(frame_add)
        self.entry_trip_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame_add, text="Дата:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_trip_date = ttk.Entry(frame_add)
        self.entry_trip_date.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame_add, text="Город вылета:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_dep_city = ttk.Entry(frame_add)
        self.entry_dep_city.grid(row=1, column=1, padx=5, pady=5)

        btn_add = ttk.Button(frame_add, text="Создать новую", command=self.add_trip)
        btn_add.grid(row=1, column=2, padx=5, pady=5)

        btn_edit = ttk.Button(frame_add, text="Сохранить изменения", command=self.edit_trip)
        btn_edit.grid(row=1, column=3, padx=5, pady=5)

        btn_del = ttk.Button(frame_add, text="Удалить выбранную", command=self.delete_trip)
        btn_del.grid(row=1, column=4, padx=5, pady=5)

        # --- Секция 2: Список поездок ---
        self.tree = ttk.Treeview(self.root, columns=("ID", "Название", "Дата", "Вылет"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Название", text="Поездка")
        self.tree.heading("Дата", text="Начало")
        self.tree.heading("Вылет", text="Город вылета")
        self.tree.column("ID", width=40)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_trip_select)

        # --- Секция 3: Детализация по дням ---
        self.frame_details = ttk.LabelFrame(self.root, text="Маршрут (выберите поездку в списке)")
        self.frame_details.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.frame_details, text="Место назначения:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_city = ttk.Entry(self.frame_details)
        self.entry_city.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.frame_details, text="День №:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_day = ttk.Entry(self.frame_details, width=10)
        self.entry_day.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(self.frame_details, text="+ Добавить в план", command=self.add_location).grid(row=0, column=4, padx=5)

        self.list_plan = tk.Listbox(self.root, height=8, font=("Arial", 10))
        self.list_plan.pack(fill="x", padx=10, pady=5)

    def add_trip(self):
        name = self.entry_trip_name.get()
        date = self.entry_trip_date.get()
        dep_city = self.entry_dep_city.get()
        
        if name and date:
            self.cursor.execute("INSERT INTO trips (name, start_date, departure_city) VALUES (?, ?, ?)", 
                                (name, date, dep_city))
            self.conn.commit()
            self.update_trip_list()
            self.play_sound("success.mp3")
            self.clear_trip_entries()
        else:
            messagebox.showwarning("Внимание", "Название и дата обязательны!")

    def edit_trip(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите поездку для редактирования")
            return
        
        trip_id = self.tree.item(selected[0])['values'][0]
        name = self.entry_trip_name.get()
        date = self.entry_trip_date.get()
        dep_city = self.entry_dep_city.get()

        self.cursor.execute("UPDATE trips SET name=?, start_date=?, departure_city=? WHERE id=?", 
                            (name, date, dep_city, trip_id))
        self.conn.commit()
        self.update_trip_list()
        messagebox.showinfo("Успех", "Данные поездки обновлены")

    def delete_trip(self):
        selected = self.tree.selection()
        if not selected: return
        
        if messagebox.askyesno("Подтверждение", "Удалить эту поездку и весь её маршрут?"):
            trip_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM trips WHERE id=?", (trip_id,))
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (trip_id,))
            self.conn.commit()
            self.update_trip_list()
            self.list_plan.delete(0, tk.END)
            self.clear_trip_entries()

    def update_trip_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.cursor.execute("SELECT * FROM trips")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def on_trip_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        vals = self.tree.item(selected[0])['values']
        # Заполнение полей для редактирования
        self.clear_trip_entries()
        self.entry_trip_name.insert(0, vals[1])
        self.entry_trip_date.insert(0, vals[2])
        self.entry_dep_city.insert(0, vals[3] if vals[3] else "")
        
        self.update_plan_list()

    def update_plan_list(self):
        self.list_plan.delete(0, tk.END)
        selected = self.tree.selection()
        if selected:
            trip_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("SELECT city, day_number FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
            for city, day in self.cursor.fetchall():
                self.list_plan.insert(tk.END, f"📅 День {day}: 📍 {city}")

    def add_location(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Сначала выберите поездку в таблице выше")
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
            messagebox.showwarning("Ошибка", "Введите название места и числовой номер дня")

    def clear_trip_entries(self):
        self.entry_trip_name.delete(0, tk.END)
        self.entry_trip_date.delete(0, tk.END)
        self.entry_dep_city.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = TiliTripApp(root)
    root.mainloop()
