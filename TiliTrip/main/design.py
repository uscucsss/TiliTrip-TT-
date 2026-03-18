import tkinter as tk
import os


CURSORS_DIR = "assets/cursors"

# 1. Глобальные настройки (Центр управления дизайном)
THEME = {
    "default_cursor": "arrow",      # Стандартная стрелка
    "button_cursor": "hand2",       # Рука (встроенная в систему)
    "custom_file": "my_cursor.cur"  # Имя вашего файла .cur
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
def set_custom_cursor(widget, cursor_type="default"):
    """
    Меняет курсор для конкретного виджета.
    cursor_type может быть: 'default', 'action' (рука) или 'file' (из файла)
    """
    try:
        if cursor_type == "action":
            widget.configure(cursor=THEME["button_cursor"])
            
        elif cursor_type == "file":
            # Путь к файлу .cur (обязательно укажите @ перед путем в Windows)
            path = os.path.join(CURSORS_DIR, THEME["custom_file"])
            if os.path.exists(path):
                widget.configure(cursor=f"@{os.path.abspath(path)}")
            else:
                print(f"Файл {path} не найден, оставлен стандартный курсор")
                
        else:
            widget.configure(cursor=THEME["default_cursor"])
            
    except Exception as e:
        print(f"Ошибка при смене курсора: {e}")

# Пример интеграции в существующие функции стилизации:
def style_button(button):
    button.configure(
        bg="#007acc",
        fg="#ffffff",
        relief="flat"
    )
    # Автоматически ставим курсор "рука" при наведении на кнопку
    set_custom_cursor(button, cursor_type="action")
