import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
import os
import pygame

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
    "money": "#2E7D32",  # Зеленый для бюджета
    "process_bg": "#BBDEFB",  # Пастельный голубой
    "done_bg": "#C8E6C9"  # Пастельный зеленый
}

STATUS_OPTIONS = ["Планируется", "В процессе", "Завершено"]


class TiliTripApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TiliTrip - Мои Поездки и Бюджет")
        self.geometry("1200x900")
        self.configure(fg_color=COLORS["bg"])

        try:
            pygame.mixer.init()
        except:
            pass

        self.init_db()
        self.setup_styles()
        self.create_widgets()
        self.update_trip_list()

    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT, status TEXT)')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations 
            (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, 
             cost REAL DEFAULT 0, is_done INTEGER DEFAULT 0, 
             FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE)''')
        self.conn.commit()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["card"], foreground="#333333", rowheight=40,
                        fieldbackground=COLORS["card"], borderwidth=0, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=COLORS["header_blue"], foreground=COLORS["header_text"],
                        relief="flat", padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', "white")])

        # Настройка цветов для тегов
        style.map("Treeview", background=[('selected', COLORS["accent"])])

    def create_widgets(self):
        # Заголовок
        self.header_label = ctk.CTkLabel(self, text="TiliTrip", font=("Segoe UI", 42, "bold"),
                                         text_color=COLORS["accent"])
        self.header_label.pack(pady=(15, 5))

        # Основной контейнер с двумя колонками
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Левая колонка (поездки)
        self.left_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Правая колонка (план)
        self.right_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_column.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # --- ЛЕВАЯ КОЛОНКА ---
        # Поиск
        self.search_entry = ctk.CTkEntry(self.left_column, placeholder_text="🔍 Поиск поездки...", width=250)
        self.search_entry.pack(pady=(0, 10), anchor="e")
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_trip_list(self.search_entry.get()))

        # Блок создания поездки
        self.frame_add = ctk.CTkFrame(self.left_column, corner_radius=20, fg_color=COLORS["card"])
        self.frame_add.pack(fill="x", pady=(0, 10))

        add_inner = ctk.CTkFrame(self.frame_add, fg_color="transparent")
        add_inner.pack(fill="x", padx=15, pady=20)

        self.entry_trip_name = ctk.CTkEntry(add_inner, placeholder_text="Название", width=140)
        self.entry_trip_name.grid(row=0, column=0, padx=(0, 5))

        self.entry_dep_city = ctk.CTkEntry(add_inner, placeholder_text="Город вылета", width=140)
        self.entry_dep_city.grid(row=0, column=1, padx=(0, 5))

        self.date_picker = DateEntry(add_inner, width=12, background='darkblue', foreground='white', borderwidth=2,
                                     date_pattern='dd.mm.yyyy')
        self.date_picker.grid(row=0, column=2, padx=(0, 5))

        self.status_menu = ctk.CTkOptionMenu(add_inner, values=STATUS_OPTIONS, width=120)
        self.status_menu.grid(row=0, column=3, padx=(0, 5))
        self.status_menu.set("Планируется")

        ctk.CTkButton(add_inner, text="СОЗДАТЬ", command=self.add_trip, width=90).grid(row=0, column=4)

        # Таблица поездок
        self.tree_container = ctk.CTkFrame(self.left_column, corner_radius=20, fg_color=COLORS["card"])
        self.tree_container.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(self.tree_container, text="✈️ МОИ ПОЕЗДКИ", font=("Segoe UI", 14, "bold"),
                     text_color=COLORS["header_text"]).pack(pady=10, padx=20, anchor="w")

        # Создаем фрейм для Treeview и скроллбара
        tree_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Добавляем скроллбар
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(tree_frame,
                                 columns=("ID", "Название", "Дата", "Вылет", "Статус"),
                                 show="headings", height=8, yscrollcommand=tree_scroll.set)

        tree_scroll.config(command=self.tree.yview)

        # Настройка тегов для цветов
        self.tree.tag_configure('process', background=COLORS["process_bg"])
        self.tree.tag_configure('done', background=COLORS["done_bg"])

        for col in ("ID", "Название", "Дата", "Вылет", "Статус"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.column("ID", width=50)
        self.tree.column("Название", width=150)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_trip_select())

        # Кнопки управления поездкой
        self.trip_btns_frame = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.trip_btns_frame.pack(fill="x", pady=(0, 10))

        self.status_btn = ctk.CTkButton(self.trip_btns_frame, text="🔄 СМЕНИТЬ СТАТУС",
                                        fg_color=COLORS["accent"],
                                        command=self.change_trip_status)
        self.status_btn.pack(side="left")

        ctk.CTkButton(self.trip_btns_frame, text="УДАЛИТЬ ПОЕЗДКУ", fg_color=COLORS["danger"],
                      command=self.delete_trip).pack(side="right")

        # --- ПРАВАЯ КОЛОНКА ---
        # Блок добавления в план с бюджетом
        self.frame_loc_add = ctk.CTkFrame(self.right_column, corner_radius=20, fg_color=COLORS["card"])
        self.frame_loc_add.pack(fill="x", pady=(0, 10))

        loc_inner = ctk.CTkFrame(self.frame_loc_add, fg_color="transparent")
        loc_inner.pack(fill="x", padx=20, pady=20)

        self.entry_city = ctk.CTkEntry(loc_inner, placeholder_text="Город", width=150)
        self.entry_city.grid(row=0, column=0, padx=(0, 5))

        self.entry_day = ctk.CTkEntry(loc_inner, placeholder_text="День", width=70)
        self.entry_day.grid(row=0, column=1, padx=(0, 5))

        self.entry_cost = ctk.CTkEntry(loc_inner, placeholder_text="Расход (₽)", width=100)
        self.entry_cost.grid(row=0, column=2, padx=(0, 5))

        ctk.CTkButton(loc_inner, text="+ В ПЛАН", command=self.add_location, width=90).grid(row=0, column=3)

        # Таблица плана
        self.plan_container = ctk.CTkFrame(self.right_column, corner_radius=20, fg_color=COLORS["card"])
        self.plan_container.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(self.plan_container, text="📋 ПЛАН МАРШРУТА (двойной клик — Готово)",
                     font=("Segoe UI", 14, "bold"), text_color=COLORS["header_text"]).pack(pady=10, padx=20, anchor="w")

        # Создаем фрейм для Treeview плана и скроллбара
        plan_frame = ctk.CTkFrame(self.plan_container, fg_color="transparent")
        plan_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Добавляем скроллбар
        plan_scroll = ttk.Scrollbar(plan_frame)
        plan_scroll.pack(side="right", fill="y")

        self.plan_view = ttk.Treeview(plan_frame,
                                      columns=("LocID", "Status", "Day", "City", "Cost"),
                                      show="headings", height=10, yscrollcommand=plan_scroll.set)

        plan_scroll.config(command=self.plan_view.yview)

        # Настройка тегов для плана
        self.plan_view.tag_configure('done', background=COLORS["done_bg"])

        self.plan_view.heading("Status", text="Статус")
        self.plan_view.heading("Day", text="День")
        self.plan_view.heading("City", text="Место назначения")
        self.plan_view.heading("Cost", text="Расход (₽)")

        self.plan_view.column("LocID", width=0, stretch=False)
        self.plan_view.column("Status", width=80, anchor="center")
        self.plan_view.column("Day", width=70, anchor="center")
        self.plan_view.column("City", anchor="w", width=250)
        self.plan_view.column("Cost", width=120, anchor="center")
        self.plan_view.pack(side="left", fill="both", expand=True)
        self.plan_view.bind("<Double-1>", lambda e: self.toggle_location_done())

        # Итоговая сумма
        self.total_cost_label = ctk.CTkLabel(self.plan_container, text="ИТОГО: 0 ₽",
                                             font=("Segoe UI", 18, "bold"), text_color=COLORS["money"])
        self.total_cost_label.pack(anchor="e", padx=30, pady=5)

        # Кнопки управления планом
        self.plan_btns_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        self.plan_btns_frame.pack(fill="x")

        ctk.CTkButton(self.plan_btns_frame, text="УДАЛИТЬ ПУНКТ", fg_color=COLORS["danger"],
                      command=self.delete_location).pack(side="left")

        ctk.CTkButton(self.plan_btns_frame, text="ОЧИСТИТЬ ПЛАН", fg_color="transparent", border_width=1,
                      border_color=COLORS["danger"], text_color=COLORS["danger"],
                      command=self.clear_entire_plan).pack(side="right")

    # --- ЛОГИКА ---
    def update_trip_list(self, filter_text=""):
        for i in self.tree.get_children():
            self.tree.delete(i)

        if filter_text:
            self.cursor.execute("SELECT * FROM trips WHERE name LIKE ?", (f'%{filter_text}%',))
        else:
            self.cursor.execute("SELECT * FROM trips")

        for row in self.cursor.fetchall():
            # Присваиваем тег в зависимости от статуса
            tag = ''
            if row[4] == "Завершено":
                tag = 'done'
            elif row[4] == "В процессе":
                tag = 'process'
            self.tree.insert("", "end", values=row, tags=(tag,))

    def on_trip_select(self):
        sel = self.tree.selection()
        if sel:
            self.update_plan_view(self.tree.item(sel)['values'][0])

    def update_plan_view(self, trip_id):
        for i in self.plan_view.get_children():
            self.plan_view.delete(i)

        self.cursor.execute(
            "SELECT id, is_done, day_number, city, cost FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        rows = self.cursor.fetchall()
        total = 0
        for r in rows:
            tag = 'done' if r[1] else ''
            status_text = "✅ Готово" if r[1] else "⏳ План"
            self.plan_view.insert("", "end", values=(r[0], status_text, r[2], r[3], f"{r[4]:,.0f}"), tags=(tag,))
            total += r[4]
        self.total_cost_label.configure(text=f"ИТОГО: {total:,.0f} ₽")

    def add_trip(self):
        name = self.entry_trip_name.get().strip()
        dep = self.entry_dep_city.get().strip()
        date = self.date_picker.get()
        status = self.status_menu.get()

        if name and dep:
            self.cursor.execute("INSERT INTO trips (name, start_date, departure_city, status) VALUES (?,?,?,?)",
                                (name, date, dep, status))
            self.conn.commit()
            self.update_trip_list()
            self.entry_trip_name.delete(0, 'end')
            self.entry_dep_city.delete(0, 'end')
        else:
            messagebox.showwarning("Внимание", "Заполните поля")

    def change_trip_status(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Внимание", "Выберите поездку в списке!")

        item = self.tree.item(sel)
        trip_id = item['values'][0]
        current_status = item['values'][4]

        try:
            idx = STATUS_OPTIONS.index(current_status)
            next_idx = (idx + 1) % len(STATUS_OPTIONS)
            new_status = STATUS_OPTIONS[next_idx]
        except ValueError:
            new_status = STATUS_OPTIONS[0]

        self.cursor.execute("UPDATE trips SET status = ? WHERE id = ?", (new_status, trip_id))
        self.conn.commit()
        self.update_trip_list()

        # Восстанавливаем выделение
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == trip_id:
                self.tree.selection_set(item)
                break

    def add_location(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Ошибка", "Выберите поездку")

        t_id = self.tree.item(sel)['values'][0]
        city = self.entry_city.get().strip()
        day = self.entry_day.get().strip()
        cost = self.entry_cost.get().strip()

        if not city or not day:
            return messagebox.showwarning("Ошибка", "Заполните город и день")

        try:
            cost_val = float(cost) if cost else 0.0
            if day.isdigit():
                self.cursor.execute("INSERT INTO locations (trip_id, city, day_number, cost) VALUES (?,?,?,?)",
                                    (t_id, city, int(day), cost_val))
                self.conn.commit()
                self.update_plan_view(t_id)
                self.entry_city.delete(0, 'end')
                self.entry_day.delete(0, 'end')
                self.entry_cost.delete(0, 'end')
            else:
                messagebox.showwarning("Ошибка", "День должен быть числом")
        except ValueError:
            messagebox.showerror("Ошибка", "Цена должна быть числом")

    def delete_location(self):
        sel = self.plan_view.selection()
        if not sel:
            return messagebox.showwarning("Ошибка", "Выберите пункт плана")

        loc_id = self.plan_view.item(sel)['values'][0]
        trip_sel = self.tree.selection()
        if trip_sel:
            trip_id = self.tree.item(trip_sel)['values'][0]
            if messagebox.askyesno("Удаление", "Удалить выбранный пункт?"):
                self.cursor.execute("DELETE FROM locations WHERE id=?", (loc_id,))
                self.conn.commit()
                self.update_plan_view(trip_id)

    def toggle_location_done(self):
        sel = self.plan_view.selection()
        if not sel:
            return

        loc_id = self.plan_view.item(sel)['values'][0]
        trip_sel = self.tree.selection()
        if trip_sel:
            trip_id = self.tree.item(trip_sel)['values'][0]
            self.cursor.execute("UPDATE locations SET is_done = NOT is_done WHERE id=?", (loc_id,))
            self.conn.commit()
            self.update_plan_view(trip_id)

    def delete_trip(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Ошибка", "Выберите поездку")

        if messagebox.askyesno("Удаление", "Удалить поездку?"):
            self.cursor.execute("DELETE FROM trips WHERE id=?", (self.tree.item(sel)['values'][0],))
            self.conn.commit()
            self.update_trip_list()
            for i in self.plan_view.get_children():
                self.plan_view.delete(i)
            self.total_cost_label.configure(text="ИТОГО: 0 ₽")

    def clear_entire_plan(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Ошибка", "Выберите поездку")

        if messagebox.askyesno("Очистка", "Удалить все пункты?"):
            t_id = self.tree.item(sel)['values'][0]
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (t_id,))
            self.conn.commit()
            self.update_plan_view(t_id)


if __name__ == "__main__":
    app = TiliTripApp()
    app.mainloop()
