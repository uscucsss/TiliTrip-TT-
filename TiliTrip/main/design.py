import tkinter as tk

# 1. Глобальные настройки (Центр управления дизайном)
THEME = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "accent": "#007acc",
    "font_main": ("Segoe UI", 12),
    "font_bold": ("Segoe UI", 12, "bold"),
    "padding": 5
}

# 2. Функции-стилизаторы
def apply_window_style(root):
    """Настройка главного окна"""
    root.configure(bg=THEME["bg"])

def style_label(label, is_header=False):
    """Стилизация текстовых меток"""
    label.configure(
        bg=THEME["bg"],
        fg=THEME["fg"],
        font=THEME["font_bold"] if is_header else THEME["font_main"],
        padx=THEME["padding"],
        pady=THEME["padding"]
    )

def style_button(button):
    """Стилизация кнопок"""
    button.configure(
        bg=THEME["accent"],
        fg=THEME["fg"],
        font=THEME["font_bold"],
        activebackground=THEME["fg"],
        activeforeground=THEME["accent"],
        relief="flat",
        cursor="hand2"
    )

def style_entry(entry):
    """Стилизация полей ввода"""
    entry.configure(
        bg="#333333",
        fg=THEME["fg"],
        insertbackground=THEME["fg"], # Цвет курсора
        relief="flat",
        font=THEME["font_main"]
    )
