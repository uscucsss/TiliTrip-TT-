import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import pygame
import requests
import threading
import time
import webbrowser
import urllib.parse
from datetime import datetime

# --- Конфигурация темы ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg": "#E3F2FD",
    "card": "#FFFFFF",
    "accent": "#2196F3",
    "danger": "#EF5350",
    "header_blue": "#E1F5FE",
    "header_text": "#01579B",
    "done_bg": "#C8E6C9",  # Пастельный зеленый
    "process_bg": "#BBDEFB"  # Пастельный голубой
}

STATUS_OPTIONS = ["Планируется", "В процессе", "Завершено"]

class TiliTripApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TiliTrip - Планировщик путешествий")
        self.geometry("1200x950")
        self.configure(fg_color=COLORS["bg"])

        try:
            pygame.mixer.init()
            self.play_sound("start.mp3")
        except:
            pass

        self.init_db()
        self.setup_styles()
        self.create_widgets()
        self.update_trip_list()
        self.set_today_date()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["card"], foreground="#333333", rowheight=40,
                        fieldbackground=COLORS["card"], borderwidth=0, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=COLORS["header_blue"], foreground=COLORS["header_text"],
                        relief="flat", padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', "white")])

    def init_db(self):
        # check_same_thread=False важен для работы сетевых запросов в фоновых потоках
        self.conn = sqlite3.connect('tilitrip.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT, status TEXT)')
        # Добавлены колонки lat и lon для кэширования координат
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, 
                is_done INTEGER DEFAULT 0, lat TEXT, lon TEXT,
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE)''')
        self.conn.commit()

    def create_widgets(self):
        # Заголовок
        self.header_label = ctk.CTkLabel(self, text="TiliTrip", font=("Segoe UI", 48, "bold"),
                                         text_color=COLORS["accent"])
        self.header_label.pack(pady=(10, 10))

        # Прокручиваемая область
        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_canvas.pack(padx=20, pady=0, fill="both", expand=True)

        # Поиск
        self.search_entry = ctk.CTkEntry(self.scroll_canvas, placeholder_text="🔍 Поиск поездки...", width=250)
        self.search_entry.pack(pady=(0, 10), anchor="e", padx=20)
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_trip_list(self.search_entry.get()))

        # Блок создания поездки
        self.frame_add = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_add.pack(fill="x", pady=10, padx=20)

        self.entry_trip_name = ctk.CTkEntry(self.frame_add, placeholder_text="Название")
        self.entry_trip_name.grid(row=0, column=0, padx=15, pady=25)
        self.entry_dep_city = ctk.CTkEntry(self.frame_add, placeholder_text="Город вылета")
        self.entry_dep_city.grid(row=0, column=1, padx=10, pady=25)

        self.date_container = ctk.CTkFrame(self.frame_add, fg_color="transparent")
        self.date_container.grid(row=0, column=2, padx=10)
        self.entry_trip_date = ctk.CTkEntry(self.date_container, width=110)
        self.entry_trip_date.pack(side="left")
        ctk.CTkButton(self.date_container, text="📅", width=35, fg_color="transparent",
                      command=self.set_today_date).pack(side="left")

        self.status_menu = ctk.CTkOptionMenu(self.frame_add, values=STATUS_OPTIONS, width=150)
        self.status_menu.grid(row=0, column=3, padx=10)
        self.status_menu.set("Планируется")

        ctk.CTkButton(self.frame_add, text="СОЗДАТЬ", command=self.add_trip, width=100).grid(row=0, column=4, padx=15)

        # Таблица поездок
        self.tree_container = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.tree_container.pack(fill="x", pady=10, padx=20)

        self.tree = ttk.Treeview(self.tree_container,
                                 columns=("ID", "Название", "Дата", "Вылет", "Статус"), show="headings", height=6)

        self.tree.tag_configure('trip_done', background=COLORS["done_bg"])
        self.tree.tag_configure('trip_process', background=COLORS["process_bg"])

        for col in ("ID", "Название", "Дата", "Вылет", "Статус"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)
        self.tree.column("ID", width=50)
        self.tree.pack(fill="x", padx=15, pady=15)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_trip_select())

        # Кнопки управления поездкой
        self.trip_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.trip_btns_frame.pack(fill="x", padx=20)
        ctk.CTkButton(self.trip_btns_frame, text="УДАЛИТЬ ПОЕЗДКУ", fg_color=COLORS["danger"],
                      command=self.delete_trip).pack(side="right", padx=10)
        ctk.CTkButton(self.trip_btns_frame, text="РЕДАКТИРОВАТЬ", command=self.open_edit_window).pack(side="right")

        # Разделитель
        ctk.CTkFrame(self.scroll_canvas, height=2, fg_color=COLORS["accent"]).pack(fill="x", pady=20, padx=20)

        # Блок добавления в план
        self.frame_details = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_details.pack(fill="x", pady=10, padx=20)
        self.entry_city = ctk.CTkEntry(self.frame_details, placeholder_text="Куда идем?")
        self.entry_city.grid(row=0, column=0, padx=20, pady=25)
        self.entry_day = ctk.CTkEntry(self.frame_details, placeholder_text="День", width=80)
        self.entry_day.grid(row=0, column=1, padx=10, pady=25)
        ctk.CTkButton(self.frame_details, text="+ В ПЛАН", command=self.add_location).grid(row=0, column=2, padx=10)

        # Таблица плана
        self.plan_container = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.plan_container.pack(fill="x", pady=10, padx=20)

        ctk.CTkLabel(self.plan_container, text="📋 План маршрута (двойной клик — Готово)", font=("Segoe UI", 13, "bold"),
                     text_color=COLORS["header_text"]).pack(pady=10, padx=20, anchor="w")

        self.plan_view = ttk.Treeview(self.plan_container, columns=("LocID", "Done", "Day", "City"), show="headings",
                                      height=8)
        self.plan_view.tag_configure('item_done', background=COLORS["done_bg"])
        self.plan_view.heading("Done", text="Статус")
        self.plan_view.heading("Day", text="День")
        self.plan_view.heading("City", text="Место назначения")
        self.plan_view.column("LocID", width=0, stretch=False)
        self.plan_view.column("Done", width=100, anchor="center")
        self.plan_view.column("Day", width=80, anchor="center")
        self.plan_view.column("City", anchor="w", width=500)
        self.plan_view.pack(fill="x", padx=20, pady=10)
        self.plan_view.bind("<Double-1>", lambda e: self.toggle_location_done())

        # Блок кнопок Маршрута и Карты
        self.route_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.route_btns_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(self.route_btns_frame, text="📍 РАССЧИТАТЬ ПУТЬ", fg_color="#4CAF50", hover_color="#45a049",
                      command=self.calculate_route).pack(side="left", padx=5)
        
        ctk.CTkButton(self.route_btns_frame, text="🗺️ ОТКРЫТЬ КАРТУ", fg_color="#FF9800", hover_color="#F57C00",
                      command=self.open_map_action).pack(side="left", padx=5)
        
        self.result_label = ctk.CTkLabel(self.scroll_canvas, text="", font=("Segoe UI", 16, "bold"), text_color=COLORS["accent"])
        self.result_label.pack(pady=10)

        # Кнопки управления планом (нижние)
        self.plan_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.plan_btns_frame.pack(fill="x", padx=20, pady=(10, 20))
        ctk.CTkButton(self.plan_btns_frame, text="ОЧИСТИТЬ ВЕСЬ ПЛАН", fg_color="transparent", border_width=1,
                      border_color=COLORS["danger"], text_color=COLORS["danger"], command=self.clear_entire_plan).pack(side="left")

    # --- ЛОГИКА ГЕОКОДИРОВАНИЯ И МАРШРУТОВ ---

    def get_coordinates(self, city, loc_id):
        """Получает координаты из БД или через Nominatim API."""
        self.cursor.execute("SELECT lat, lon FROM locations WHERE id=?", (loc_id,))
        row = self.cursor.fetchone()
        if row and row[0] and row[1]:
            return row[0], row[1]
        
        try:
            url = f"https://nominatim.openstreetmap.org{urllib.parse.quote(city)}&format=json&limit=1"
            res = requests.get(url, headers={'User-Agent': 'TiliTripApp/1.2'}).json()
            if res:
                lat, lon = res[0]['lat'], res[0]['lon']
                self.cursor.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (lat, lon, loc_id))
                self.conn.commit()
                time.sleep(1) # Лимит Nominatim
                return lat, lon
        except Exception as e:
            print(f"Ошибка геокодирования: {e}")
        return None, None

    def calculate_route(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Сначала выберите поездку")
            return
        trip_id = self.tree.item(selected[0])['values'][0]
        self.result_label.configure(text="⏳ Идет расчет... пожалуйста, подождите")
        threading.Thread(target=self._route_thread, args=(trip_id,), daemon=True).start()

    def _route_thread(self, trip_id):
        try:
            self.cursor.execute("SELECT id, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
            locations = self.cursor.fetchall()

            if len(locations) < 2:
                self.after(0, lambda: self.result_label.configure(text="Добавьте хотя бы 2 точки в план"))
                return

            points = []
            for loc_id, city in locations:
                lat, lon = self.get_coordinates(city, loc_id)
                if lat: points.append(f"{lat},{lon}")
                else:
                    self.after(0, lambda c=city: messagebox.showerror("Ошибка", f"Город {c} не найден"))
                    return

            total_dist = 0
            total_time = 0
            api_key = "e0db81e2-ded2-4ba9-9f0f-dc8eb9fac721"

            for i in range(len(points)-1):
                gh_url = "https://graphhopper.com"
                params = [('point', points[i]), ('point', points[i+1]), ('profile', 'car'), ('key', api_key)]
                res = requests.get(gh_url, params=params).json()
                if 'paths' in res:
                    total_dist += res['paths'][0]['distance']
                    total_time += res['paths'][0]['time']
                else:
                    self.after(0, lambda: messagebox.showerror("Ошибка API", "Не удалось рассчитать маршрут"))
                    return

            km = total_dist / 1000
            h, m = divmod(int(total_time / 1000 / 60), 60)
            self.after(0, lambda: self.result_label.configure(text=f"🏁 Дистанция: {km:.1f} км | Время: {h}ч. {m}мин."))
            self.after(0, lambda: self.play_sound("success.mp3"))

        except Exception as e:
            self.after(0, lambda ex=e: messagebox.showerror("Ошибка", f"Ошибка: {ex}"))

    def open_map_action(self):
        selected = self.tree.selection()
        if not selected: return
        trip_id = self.tree.item(selected[0])['values'][0]
        threading.Thread(target=self._map_thread, args=(trip_id,), daemon=True).start()

    def _map_thread(self, trip_id):
        self.cursor.execute("SELECT id, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        locations = self.cursor.fetchall()
        
        points_query = []
        for loc_id, city in locations:
            lat, lon = self.get_coordinates(city, loc_id)
            if lat: points_query.append(f"point={lat}%2C{lon}")

        if points_query:
            url = f"https://graphhopper.com?{'&'.join(points_query)}&profile=car&locale=ru"
            webbrowser.open(url)

    # --- СТАНДАРТНЫЕ МЕТОДЫ УПРАВЛЕНИЯ ---

    def add_trip(self):
        name = self.entry_trip_name.get()
        dep = self.entry_dep_city.get()
        date = self.entry_trip_date.get()
        status = self.status_menu.get()
        if name:
            self.cursor.execute("INSERT INTO trips (name, start_date, departure_city, status) VALUES (?,?,?,?)",
                               (name, date, dep, status))
            self.conn.commit()
            self.update_trip_list()
            self.entry_trip_name.delete(0, 'end')

    def update_trip_list(self, search_query=""):
        for i in self.tree.get_children(): self.tree.delete(i)
        if search_query:
            self.cursor.execute("SELECT * FROM trips WHERE name LIKE ?", (f'%{search_query}%',))
        else:
            self.cursor.execute("SELECT * FROM trips")
        
        for row in self.cursor.fetchall():
            tag = ''
            if row[4] == "Завершено": tag = 'trip_done'
            elif row[4] == "В процессе": tag = 'trip_process'
            self.tree.insert("", "end", values=row, tags=(tag,))

    def on_trip_select(self):
        selected = self.tree.selection()
        if not selected: return
        trip_id = self.tree.item(selected[0])['values'][0]
        self.update_plan_view(trip_id)

    def update_plan_view(self, trip_id):
        for i in self.plan_view.get_children(): self.plan_view.delete(i)
        self.cursor.execute("SELECT id, is_done, day_number, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        for row in self.cursor.fetchall():
            status = "✅ Готово" if row[1] else "⏳ План"
            tag = 'item_done' if row[1] else ''
            self.plan_view.insert("", "end", values=(row[0], status, row[2], row[3]), tags=(tag,))

    def add_location(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите поездку в таблице выше")
            return
        trip_id = self.tree.item(selected[0])['values'][0]
        city = self.entry_city.get()
        day = self.entry_day.get()
        if city and day:
            self.cursor.execute("INSERT INTO locations (trip_id, city, day_number) VALUES (?,?,?)", (trip_id, city, day))
            self.conn.commit()
            self.update_plan_view(trip_id)
            self.entry_city.delete(0, 'end')

    def toggle_location_done(self):
        selected = self.plan_view.selection()
        if not selected: return
        loc_id = self.plan_view.item(selected[0])['values'][0]
        self.cursor.execute("UPDATE locations SET is_done = NOT is_done WHERE id=?", (loc_id,))
        self.conn.commit()
        # Обновляем вид
        trip_id = self.tree.item(self.tree.selection()[0])['values'][0]
        self.update_plan_view(trip_id)

    def delete_trip(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Удаление", "Удалить эту поездку и весь её план?"):
            trip_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM trips WHERE id=?", (trip_id,))
            self.conn.commit()
            self.update_trip_list()
            for i in self.plan_view.get_children(): self.plan_view.delete(i)

    def clear_entire_plan(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Очистка", "Удалить все точки из плана этой поездки?"):
            trip_id = self.tree.item(selected[0])['values'][0]
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (trip_id,))
            self.conn.commit()
            self.update_plan_view(trip_id)

    def open_edit_window(self):
        messagebox.showinfo("Редактирование", "Функция редактирования в разработке")

    def set_today_date(self):
        self.entry_trip_date.delete(0, "end")
        self.entry_trip_date.insert(0, datetime.now().strftime("%d.%m.%Y"))

    def play_sound(self, filename):
        try:
            if os.path.exists(filename):
                pygame.mixer.Sound(filename).play()
        except: pass

if __name__ == "__main__":
    app = TiliTripApp()
    app.mainloop()
