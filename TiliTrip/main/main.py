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
    "money": "#2E7D32"  # Зеленый для бюджета
}

STATUS_OPTIONS = ["Планируется", "В процессе", "Завершено"]

class TiliTripApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TiliTrip - Мои Поездки и Бюджет")
        self.geometry("1100x900")
        self.configure(fg_color=COLORS["bg"])

        try:
            pygame.mixer.init()
        except: pass

        self.init_db()
        self.setup_styles()
        self.create_widgets()
        self.update_trip_list()

    def init_db(self):
        self.conn = sqlite3.connect('tilitrip.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute('CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, name TEXT, start_date TEXT, departure_city TEXT, status TEXT)')
        # Добавлена колонка cost
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations 
            (id INTEGER PRIMARY KEY, trip_id INTEGER, city TEXT, day_number INTEGER, 
             cost REAL DEFAULT 0, is_done INTEGER DEFAULT 0, 
             FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE)''')
        self.conn.commit()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["card"], foreground="#333333", rowheight=40, fieldbackground=COLORS["card"], borderwidth=0, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=COLORS["header_blue"], foreground=COLORS["header_text"], relief="flat", padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', "white")])

    def create_widgets(self):
        self.header_label = ctk.CTkLabel(self, text="TiliTrip", font=("Segoe UI", 42, "bold"), text_color=COLORS["accent"])
        self.header_label.pack(pady=(15, 5))

        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_canvas.pack(padx=20, pady=0, fill="both", expand=True)

        # Поиск
        self.search_entry = ctk.CTkEntry(self.scroll_canvas, placeholder_text="🔍 Поиск поездки...", width=250)
        self.search_entry.pack(pady=(0, 10), anchor="e", padx=20)
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_trip_list(self.search_entry.get()))

        # Блок создания поездки
        self.frame_add = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_add.pack(fill="x", pady=10, padx=20)

        self.entry_trip_name = ctk.CTkEntry(self.frame_add, placeholder_text="Название поездки")
        self.entry_trip_name.grid(row=0, column=0, padx=10, pady=25)
        
        self.entry_dep_city = ctk.CTkEntry(self.frame_add, placeholder_text="Город вылета")
        self.entry_dep_city.grid(row=0, column=1, padx=10, pady=25)

        self.date_picker = DateEntry(self.frame_add, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        self.date_picker.grid(row=0, column=2, padx=10, pady=25)

        self.status_menu = ctk.CTkOptionMenu(self.frame_add, values=STATUS_OPTIONS, width=140)
        self.status_menu.grid(row=0, column=3, padx=10)
        self.status_menu.set("Планируется")

        ctk.CTkButton(self.frame_add, text="СОЗДАТЬ", command=self.add_trip, width=100).grid(row=0, column=4, padx=15)

        # Таблица поездок
        self.tree = ttk.Treeview(self.scroll_canvas, columns=("ID", "Название", "Дата", "Вылет", "Статус"), show="headings", height=5)
        for col in ("ID", "Название", "Дата", "Вылет", "Статус"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=160)
        self.tree.column("ID", width=50)
        self.tree.pack(fill="x", padx=20, pady=10)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_trip_select())

        ctk.CTkButton(self.scroll_canvas, text="УДАЛИТЬ ПОЕЗДКУ", fg_color=COLORS["danger"], command=self.delete_trip).pack(anchor="e", padx=20)

        ctk.CTkFrame(self.scroll_canvas, height=2, fg_color=COLORS["accent"]).pack(fill="x", pady=20, padx=20)
        
        # Блок добавления в план с бюджетом
        self.frame_loc_add = ctk.CTkFrame(self.scroll_canvas, corner_radius=20, fg_color=COLORS["card"])
        self.frame_loc_add.pack(fill="x", pady=10, padx=20)
        
        self.entry_city = ctk.CTkEntry(self.frame_loc_add, placeholder_text="Город")
        self.entry_city.grid(row=0, column=0, padx=10, pady=20)
        
        self.entry_day = ctk.CTkEntry(self.frame_loc_add, placeholder_text="День", width=60)
        self.entry_day.grid(row=0, column=1, padx=5)

        self.entry_cost = ctk.CTkEntry(self.frame_loc_add, placeholder_text="Расход (₽)", width=100)
        self.entry_cost.grid(row=0, column=2, padx=5)
        
        ctk.CTkButton(self.frame_loc_add, text="+ В ПЛАН", command=self.add_location).grid(row=0, column=3, padx=10)

        # Таблица плана
        self.plan_view = ttk.Treeview(self.scroll_canvas, columns=("LocID", "Status", "Day", "City", "Cost"), show="headings", height=8)
        self.plan_view.heading("Day", text="День")
        self.plan_view.heading("City", text="Место назначения")
        self.plan_view.heading("Status", text="Статус")
        self.plan_view.heading("Cost", text="Расход (₽)")
        
        self.plan_view.column("LocID", width=0, stretch=False)
        self.plan_view.column("Status", width=100, anchor="center")
        self.plan_view.column("Day", width=80, anchor="center")
        self.plan_view.column("Cost", width=120, anchor="center")
        self.plan_view.pack(fill="x", padx=20, pady=10)
        self.plan_view.bind("<Double-1>", lambda e: self.toggle_location_done())

        # Итоговая сумма
        self.total_cost_label = ctk.CTkLabel(self.scroll_canvas, text="ИТОГО ПОЕЗДКА: 0 ₽", font=("Segoe UI", 18, "bold"), text_color=COLORS["money"])
        self.total_cost_label.pack(anchor="e", padx=30, pady=5)

        self.plan_btns_frame = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.plan_btns_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(self.plan_btns_frame, text="УДАЛИТЬ ПУНКТ", fg_color=COLORS["danger"], command=self.delete_location).pack(side="left", padx=5)
        ctk.CTkButton(self.plan_btns_frame, text="ОЧИСТИТЬ ПЛАН", fg_color="transparent", border_width=1, border_color=COLORS["danger"], text_color=COLORS["danger"], command=self.clear_entire_plan).pack(side="right")

    # --- ЛОГИКА ---

    def add_trip(self):
        name, dep, date, status = self.entry_trip_name.get().strip(), self.entry_dep_city.get().strip(), self.date_picker.get(), self.status_menu.get()
        if name and dep:
            self.cursor.execute("INSERT INTO trips VALUES (NULL,?,?,?,?)", (name, date, dep, status))
            self.conn.commit()
            self.update_trip_list()
            [e.delete(0, 'end') for e in [self.entry_trip_name, self.entry_dep_city]]
        else: messagebox.showwarning("Внимание", "Заполните поля")

    def update_trip_list(self, query=""):
        [self.tree.delete(i) for i in self.tree.get_children()]
        sql = "SELECT * FROM trips WHERE name LIKE ?" if query else "SELECT * FROM trips"
        self.cursor.execute(sql, (f'%{query}%',) if query else ())
        [self.tree.insert("", "end", values=row) for row in self.cursor.fetchall()]

    def on_trip_select(self):
        sel = self.tree.selection()
        if sel: self.update_plan_view(self.tree.item(sel)['values'][0])

    def update_plan_view(self, trip_id):
        [self.plan_view.delete(i) for i in self.plan_view.get_children()]
        self.cursor.execute("SELECT id, is_done, day_number, city, cost FROM locations WHERE trip_id=? ORDER BY day_number", (trip_id,))
        rows = self.cursor.fetchall()
        total = 0
        for r in rows:
            self.plan_view.insert("", "end", values=(r[0], "✅" if r[1] else "⏳", r[2], r[3], f"{r[4]:,.0f}"))
            total += r[4]
        self.total_cost_label.configure(text=f"ИТОГО ПОЕЗДКА: {total:,.0f} ₽")

    def add_location(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Ошибка", "Выберите поездку")
        t_id = self.tree.item(sel)['values'][0]
        city, day, cost = self.entry_city.get().strip(), self.entry_day.get().strip(), self.entry_cost.get().strip()
        
        try:
            cost_val = float(cost) if cost else 0.0
            if city and day:
                self.cursor.execute("INSERT INTO locations (trip_id, city, day_number, cost) VALUES (?,?,?,?)", (t_id, city, day, cost_val))
                self.conn.commit()
                self.update_plan_view(t_id)
                [e.delete(0, 'end') for e in [self.entry_city, self.entry_day, self.entry_cost]]
        except ValueError: messagebox.showerror("Ошибка", "Цена должна быть числом")

    def delete_location(self):
        sel = self.plan_view.selection()
        if sel:
            loc_id = self.plan_view.item(sel)['values'][0]
            trip_id = self.tree.item(self.tree.selection())['values'][0]
            self.cursor.execute("DELETE FROM locations WHERE id=?", (loc_id,))
            self.conn.commit()
            self.update_plan_view(trip_id)

    def toggle_location_done(self):
        sel = self.plan_view.selection()
        if sel:
            loc_id, t_id = self.plan_view.item(sel)['values'][0], self.tree.item(self.tree.selection())['values'][0]
            self.cursor.execute("UPDATE locations SET is_done = NOT is_done WHERE id=?", (loc_id,))
            self.conn.commit()
            self.update_plan_view(t_id)

    def delete_trip(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Удаление", "Удалить поездку?"):
            self.cursor.execute("DELETE FROM trips WHERE id=?", (self.tree.item(sel)['values'][0],))
            self.conn.commit()
            self.update_trip_list()
            [self.plan_view.delete(i) for i in self.plan_view.get_children()]
            self.total_cost_label.configure(text="ИТОГО ПОЕЗДКА: 0 ₽")

    def clear_entire_plan(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Очистка", "Удалить все пункты?"):
            t_id = self.tree.item(sel)['values'][0]
            self.cursor.execute("DELETE FROM locations WHERE trip_id=?", (t_id,))
            self.conn.commit()
            self.update_plan_view(t_id)

if __name__ == "__main__":
    TiliTripApp().mainloop()
