import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import pygame
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
        # Настройка выделения (чтобы цвета строк были видны)
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', "white")])

    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT, status TEXT)')
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, is_done INTEGER DEFAULT 0, FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE)')
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

        self.tree = ttk.Treeview(self.tree_frame if hasattr(self, 'tree_frame') else self.tree_container,
                                 columns=("ID", "Название", "Дата", "Вылет", "Статус"), show="headings", height=6)

        # Настройка цветов тегов для ГЛАВНОЙ ТАБЛИЦЫ
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

        # Настройка цветов тегов для ТАБЛИЦЫ ПЛАНА
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

        # Кнопки управления планом
        self.plan_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.plan_btns_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(self.plan_btns_frame, text="ОЧИСТИТЬ ВЕСЬ ПЛАН", fg_color="transparent", border_width=1,
                      border_color=COLORS["danger"], text_color=COLORS["danger"], command=self.clear_entire_plan).pack(
            side="right", padx=10)
        ctk.CTkButton(self.plan_btns_frame, text="УДАЛИТЬ ПУНКТ", fg_color=COLORS["danger"],
                      command=self.delete_location).pack(side="right")

    # --- ЛОГИКА ---
    def update_trip_list(self, filter_text=""):
        for i in self.tree.get_children(): self.tree.delete(i)
        query = "SELECT id, name, start_date, departure_city, status FROM trips WHERE name LIKE ?"
        self.cursor.execute(query, (f'%{filter_text}%',))
        for row in self.cursor.fetchall():
            # Присваиваем тег в зависимости от статуса
            tag = ''
            if row[4] == "Завершено":
                tag = 'trip_done'
            elif row[4] == "В процессе":
                tag = 'trip_process'
            self.tree.insert("", "end", values=row, tags=(tag,))

    def on_trip_select(self):
        self.update_plan_list()

    def update_plan_list(self):
        for i in self.plan_view.get_children(): self.plan_view.delete(i)
        sel = self.tree.selection()
        if not sel: return
        t_id = self.tree.item(sel)['values'][0]
        self.cursor.execute("SELECT id, is_done, day_number, city FROM locations WHERE trip_id=? ORDER BY day_number",
                            (t_id,))
        for row in self.cursor.fetchall():
            mark = "✅ Готово" if row[1] == 1 else "⏳ План"
            tag = 'item_done' if row[1] == 1 else ''
            self.plan_view.insert("", "end", values=(row[0], mark, row[2], row[3]), tags=(tag,))

    def add_trip(self):
        n, d, dep, s = self.entry_trip_name.get(), self.entry_trip_date.get(), self.entry_dep_city.get(), self.status_menu.get()
        if n and d:
            self.cursor.execute("INSERT INTO trips (name, start_date, departure_city, status) VALUES (?, ?, ?, ?)",
                                (n, d, dep, s))
            self.conn.commit();
            self.update_trip_list();
            self.entry_trip_name.delete(0, 'end')

    def delete_trip(self):
        sel = self.tree.selection()
        if not sel: return
        t_id = self.tree.item(sel)['values'][0]
        if messagebox.askyesno("Удаление", "Удалить поездку целиком?"):
            self.cursor.execute("DELETE FROM trips WHERE id=?", (t_id,))
            self.conn.commit();
            self.update_trip_list();
            self.update_plan_list()

    def add_location(self):
        sel = self.tree.selection()
        if not sel: return
        t_id = self.tree.item(sel)['values'][0]
        c, d = self.entry_city.get(), self.entry_day.get()
        if c and d.isdigit():
            self.cursor.execute("INSERT INTO locations (trip_id, city, day_number) VALUES (?, ?, ?)", (t_id, c, int(d)))
            self.conn.commit();
            self.update_plan_list();
            self.entry_city.delete(0, 'end')

    def delete_location(self):
        sel = self.plan_view.selection()
        if not sel: return
        l_id = self.plan_view.item(sel)['values'][0]
        self.cursor.execute("DELETE FROM locations WHERE id=?", (l_id,))
        self.conn.commit();
        self.update_plan_list()

    def clear_entire_plan(self):
        sel = self.tree.selection()
        if not sel: return
        t_id = self.tree.item(sel)['values'][0]
        if messagebox.askyesno("Очистка", "Удалить все пункты маршрута?"):
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (t_id,))
            self.conn.commit();
            self.update_plan_list()

    def toggle_location_done(self):
        sel = self.plan_view.selection()
        if not sel: return
        l_id, current_mark = self.plan_view.item(sel)['values'][0], self.plan_view.item(sel)['values'][1]
        new_status = 1 if current_mark == "⏳ План" else 0
        self.cursor.execute("UPDATE locations SET is_done=? WHERE id=?", (new_status, l_id))
        self.conn.commit();
        self.update_plan_list()

    def set_today_date(self):
        self.entry_trip_date.delete(0, 'end')
        self.entry_trip_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

    def open_edit_window(self):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel)['values']
        edit_win = ctk.CTkToplevel(self)
        edit_win.geometry("350x450");
        edit_win.attributes("-topmost", True)
        en_name = ctk.CTkEntry(edit_win);
        en_name.insert(0, v[1]);
        en_name.pack(pady=10)
        en_date = ctk.CTkEntry(edit_win);
        en_date.insert(0, v[2]);
        en_date.pack(pady=10)
        en_dep = ctk.CTkEntry(edit_win);
        en_dep.insert(0, v[3] if v[3] else "");
        en_dep.pack(pady=10)
        en_stat = ctk.CTkOptionMenu(edit_win, values=STATUS_OPTIONS);
        en_stat.set(v[4]);
        en_stat.pack(pady=10)

        def save():
            self.cursor.execute("UPDATE trips SET name=?, start_date=?, departure_city=?, status=? WHERE id=?",
                                (en_name.get(), en_date.get(), en_dep.get(), en_stat.get(), v[0]))
            self.conn.commit();
            self.update_trip_list();
            edit_win.destroy()

        ctk.CTkButton(edit_win, text="Сохранить", command=save).pack(pady=20)

    def play_sound(self, filename):
        if os.path.exists(filename): pygame.mixer.music.load(filename); pygame.mixer.music.play()

    def on_closing(self):
        try:
            self.play_sound("shutdown.mp3")
        except:
            pass
        self.after(1000, self.destroy)


if __name__ == "__main__":
    app = TiliTripApp();
    app.mainloop()
