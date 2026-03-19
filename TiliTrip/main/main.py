import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
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
    "done_bg": "#C8E6C9",
    "process_bg": "#BBDEFB"
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
        except: pass

        self.init_db()
        self.setup_styles()
        self.create_widgets()
        self.update_trip_list()

    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute('CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT, status TEXT)')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations 
            (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, 
             is_done INTEGER DEFAULT 0, lat TEXT, lon TEXT, 
             FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE)''')
        self.conn.commit()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["card"], foreground="#333333", rowheight=40, fieldbackground=COLORS["card"], borderwidth=0, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=COLORS["header_blue"], foreground=COLORS["header_text"], relief="flat", padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', "white")])

    def create_widgets(self):
        # Заголовок
        self.header_label = ctk.CTkLabel(self, text="TiliTrip", font=("Segoe UI", 48, "bold"), text_color=COLORS["accent"])
        self.header_label.pack(pady=(10, 5))

        # Прокрутка
        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_canvas.pack(padx=20, pady=0, fill="both", expand=True)

        # Поиск
        self.search_entry = ctk.CTkEntry(self.scroll_canvas, placeholder_text="🔍 Поиск поездки...", width=250)
        self.search_entry.pack(pady=(0, 10), anchor="e", padx=20)
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_trip_list(self.search_entry.get()))

        # Блок создания (с классическим календарем)
        self.frame_add = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_add.pack(fill="x", pady=10, padx=20)

        self.entry_trip_name = ctk.CTkEntry(self.frame_add, placeholder_text="Название", width=150)
        self.entry_trip_name.grid(row=0, column=0, padx=10, pady=25)
        
        self.entry_dep_city = ctk.CTkEntry(self.frame_add, placeholder_text="Город вылета", width=150)
        self.entry_dep_city.grid(row=0, column=1, padx=10, pady=25)

        self.date_picker = DateEntry(self.frame_add, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        self.date_picker.grid(row=0, column=2, padx=10, pady=25)

        self.status_menu = ctk.CTkOptionMenu(self.frame_add, values=STATUS_OPTIONS, width=140)
        self.status_menu.grid(row=0, column=3, padx=10)
        self.status_menu.set("Планируется")

        ctk.CTkButton(self.frame_add, text="СОЗДАТЬ", command=self.add_trip, width=100).grid(row=0, column=4, padx=15)

        # Кнопки расчета и карты (ПЕРЕНЕСЕНЫ НАВЕРХ)
        self.action_btn_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(self.action_btn_frame, text="📍 РАССЧИТАТЬ ПУТЬ", fg_color="#4CAF50", hover_color="#45a049", command=self.calculate_route).pack(side="left", padx=5)
        ctk.CTkButton(self.action_btn_frame, text="🗺️ КАРТА МАРШРУТА", fg_color="#FF9800", hover_color="#F57C00", command=self.open_map_action).pack(side="left", padx=5)
        
        self.result_label = ctk.CTkLabel(self.action_btn_frame, text="", font=("Segoe UI", 14, "bold"), text_color=COLORS["accent"])
        self.result_label.pack(side="left", padx=20)

        # Таблица поездок
        self.tree = ttk.Treeview(self.scroll_canvas, columns=("ID", "Название", "Дата", "Вылет", "Статус"), show="headings", height=6)
        for col in ("ID", "Название", "Дата", "Вылет", "Статус"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)
        self.tree.column("ID", width=50)
        self.tree.pack(fill="x", padx=20, pady=10)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_trip_select())

        # Кнопки под таблицей поездок
        self.trip_ctrl_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.trip_ctrl_frame.pack(fill="x", padx=20)
        ctk.CTkButton(self.trip_ctrl_frame, text="УДАЛИТЬ ПОЕЗДКУ", fg_color=COLORS["danger"], command=self.delete_trip).pack(side="right", padx=5)

        # Разделитель и блок Плана
        ctk.CTkFrame(self.scroll_canvas, height=2, fg_color=COLORS["accent"]).pack(fill="x", pady=20, padx=20)
        
        self.frame_loc_add = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_loc_add.pack(fill="x", pady=10, padx=20)
        self.entry_city = ctk.CTkEntry(self.frame_loc_add, placeholder_text="Куда идем? (Город)")
        self.entry_city.grid(row=0, column=0, padx=20, pady=20)
        self.entry_day = ctk.CTkEntry(self.frame_loc_add, placeholder_text="День", width=80)
        self.entry_day.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.frame_loc_add, text="+ В ПЛАН", command=self.add_location).grid(row=0, column=2, padx=10)

        # Таблица плана
        self.plan_view = ttk.Treeview(self.scroll_canvas, columns=("LocID", "Status", "Day", "City"), show="headings", height=8)
        self.plan_view.heading("Day", text="День"); self.plan_view.heading("City", text="Место назначения"); self.plan_view.heading("Status", text="Статус")
        self.plan_view.column("LocID", width=0, stretch=False); self.plan_view.column("Status", width=100); self.plan_view.column("Day", width=80)
        self.plan_view.pack(fill="x", padx=20, pady=10)
        self.plan_view.bind("<Double-1>", lambda e: self.toggle_location_done())

        # Кнопки под таблицей плана
        self.plan_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.plan_btns_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(self.plan_btns_frame, text="УДАЛИТЬ ПУНКТ", fg_color=COLORS["danger"], command=self.delete_location).pack(side="left", padx=5)
        ctk.CTkButton(self.plan_btns_frame, text="ОЧИСТИТЬ ВЕСЬ ПЛАН", fg_color="transparent", border_width=1, border_color=COLORS["danger"], text_color=COLORS["danger"], command=self.clear_entire_plan).pack(side="right")

    # --- ЛОГИКА ГЕОКОДИРОВАНИЯ И API ---

    def get_coords(self, city, loc_id=None):
        """Усиленный поиск через Nominatim с очисткой данных."""
        if loc_id:
            self.cursor.execute("SELECT lat, lon FROM locations WHERE id=?", (loc_id,))
            res = self.cursor.fetchone()
            if res and res[0] and res[1]: return res[0], res[1]

        try:
            city_clean = city.strip()
            # Усиленный User-Agent для обхода блокировок
            headers = {'User-Agent': 'TiliTripApp_Final_Stable_v3.2'}
            url = f"https://nominatim.openstreetmap.org{urllib.parse.quote(city_clean)}&format=json&limit=1"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            if data:
                lat, lon = data[0]['lat'], data[0]['lon']
                if loc_id:
                    self.cursor.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (lat, lon, loc_id))
                    self.conn.commit()
                time.sleep(1.2) # Обязательная пауза Nominatim
                return lat, lon
        except Exception as e:
            print(f"Ошибка гео: {e}")
        return None, None

    def calculate_route(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Ошибка", "Выберите поездку")
        trip_data = self.tree.item(sel)['values']
        self.result_label.configure(text="⏳ Ищу города и считаю путь...")
        threading.Thread(target=self._route_thread, args=(trip_data,), daemon=True).start()

    def _route_thread(self, trip_data):
        try:
            trip_id, _, _, dep_city, _ = trip_data
            self.cursor.execute("SELECT id, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
            locs = self.cursor.fetchall()
            
            full_route_pts = []
            
            # 1. Город вылета
            l_start, lon_start = self.get_coords(dep_city)
            if l_start: full_route_pts.append(f"{l_start},{lon_start}")
            else: return self.after(0, lambda: messagebox.showerror("Ошибка", f"Не найден город вылета: {dep_city}"))

            # 2. Пункты плана
            for l_id, l_city in locs:
                lt, ln = self.get_coords(l_city, l_id)
                if lt: full_route_pts.append(f"{lt},{ln}")
                else: return self.after(0, lambda c=l_city: messagebox.showerror("Ошибка", f"Не найден пункт: {c}"))

            if len(full_route_pts) < 2:
                return self.after(0, lambda: self.result_label.configure(text="Добавьте города в план"))

            d_m, t_ms = 0, 0
            api_key = "e0db81e2-ded2-4ba9-9f0f-dc8eb9fac721"
            
            for i in range(len(full_route_pts)-1):
                url = f"https://graphhopper.com{full_route_pts[i]}&point={full_route_pts[i+1]}&profile=car&key={api_key}"
                r = requests.get(url).json()
                if 'paths' in r:
                    d_m += r['paths'][0]['distance']
                    t_ms += r['paths'][0]['time']
                else: raise Exception(r.get('message', 'API Error'))

            res = f"🏁 {d_m/1000:.1f} км | {int(t_ms/1000/3600)}ч {int((t_ms/1000%3600)/60)}м"
            self.after(0, lambda: self.result_label.configure(text=res))
            self.after(0, lambda: self.play_sound("success.mp3"))
        except Exception as e:
            self.after(0, lambda ex=e: messagebox.showerror("Ошибка", f"Ошибка расчета: {ex}"))
            self.after(0, lambda: self.result_label.configure(text=""))

    def open_map_action(self):
        sel = self.tree.selection()
        if not sel: return
        t_id, _, _, dep, _ = self.tree.item(sel)['values']
        threading.Thread(target=self._map_thread, args=(t_id, dep), daemon=True).start()

    def _map_thread(self, trip_id, dep_city):
        pts = []
        l0, ln0 = self.get_coords(dep_city)
        if l0: pts.append(f"point={l0}%2C{ln0}")
        self.cursor.execute("SELECT id, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        for lid, city in self.cursor.fetchall():
            lt, ln = self.get_coords(city, lid)
            if lt: pts.append(f"point={lt}%2C{ln}")
        if pts: webbrowser.open(f"https://graphhopper.com?{'&'.join(pts)}&profile=car&locale=ru")

    # --- УПРАВЛЕНИЕ ДАННЫМИ ---

    def add_trip(self):
        n, dep, d, s = self.entry_trip_name.get(), self.entry_dep_city.get(), self.date_picker.get(), self.status_menu.get()
        if n and dep:
            self.cursor.execute("INSERT INTO trips VALUES (NULL,?,?,?,?)", (n, d, dep, s))
            self.conn.commit(); self.update_trip_list()

    def update_trip_list(self, query=""):
        for i in self.tree.get_children(): self.tree.delete(i)
        sql = "SELECT * FROM trips WHERE name LIKE ?" if query else "SELECT * FROM trips"
        self.cursor.execute(sql, (f'%{query}%',) if query else ())
        for r in self.cursor.fetchall(): self.tree.insert("", "end", values=r)

    def on_trip_select(self):
        sel = self.tree.selection()
        if sel: self.update_plan_view(self.tree.item(sel)['values'][0])

    def update_plan_view(self, trip_id):
        for i in self.plan_view.get_children(): self.plan_view.delete(i)
        self.cursor.execute("SELECT id, is_done, day_number, city FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        for r in self.cursor.fetchall():
            self.plan_view.insert("", "end", values=(r[0], "✅" if r[1] else "⏳", r[2], r[3]))

    def add_location(self):
        sel = self.tree.selection()
        if not sel: return
        t_id, c, d = self.tree.item(sel)['values'][0], self.entry_city.get(), self.entry_day.get()
        if c and d:
            self.cursor.execute("INSERT INTO locations (trip_id, city, day_number) VALUES (?,?,?)", (t_id, c, d))
            self.conn.commit(); self.update_plan_view(t_id)

    def delete_location(self):
        sel = self.plan_view.selection()
        if sel:
            self.cursor.execute("DELETE FROM locations WHERE id=?", (self.plan_view.item(sel)['values'][0],))
            self.conn.commit(); self.on_trip_select()

    def toggle_location_done(self):
        sel = self.plan_view.selection()
        if sel:
            self.cursor.execute("UPDATE locations SET is_done = NOT is_done WHERE id=?", (self.plan_view.item(sel)['values'][0],))
            self.conn.commit(); self.on_trip_select()

    def delete_trip(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Удаление", "Удалить поездку?"):
            self.cursor.execute("DELETE FROM trips WHERE id=?", (self.tree.item(sel)['values'][0],))
            self.conn.commit(); self.update_trip_list()

    def clear_entire_plan(self):
        sel = self.tree.selection()
        if sel:
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (self.tree.item(sel)['values'][0],))
            self.conn.commit(); self.on_trip_select()

    def play_sound(self, f):
        try:
            if os.path.exists(f): pygame.mixer.Sound(f).play()
        except: pass

if __name__ == "__main__":
    app = TiliTripApp(); app.mainloop()
