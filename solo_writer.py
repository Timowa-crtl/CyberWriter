#!/usr/bin/env python3
import datetime
import glob
import json
import os
import smtplib
import subprocess
import sys
import tkinter as tk
import traceback
from email.mime.text import MIMEText
from tkinter import font, messagebox

# SETTINGS FILE & THEME LOADING
SETTINGS_FILE = "writer_settings.json"  # JSON formatted settings file


def load_settings():
    default_settings = {
        "themes": {
            "C64": {
                "text_bg": "#0000AA",
                "text_fg": "white",
                "window_bg": "#0000AA",
                "filename_bg": "#0000AA",
            },
            "Dark": {
                "text_bg": "#1a1a1a",
                "text_fg": "#ffffff",
                "window_bg": "#1a1a1a",
                "filename_bg": "#1a1a1a",
            },
        }
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            print("Settings loaded from file.")
        except Exception as e:
            print(f"Error loading settings file: {e}")
            settings = default_settings
        if "themes" not in settings:
            settings["themes"] = default_settings["themes"]
    else:
        settings = default_settings
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
            print("Default settings file created.")
        except Exception as e:
            print(f"Error saving default settings: {e}")
    return settings


settings = load_settings()
themes = settings["themes"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = ""
SENDER_PASSWORD = ""
RECIPIENT_EMAIL = ""

BASE_DIR = "writing_files"
os.makedirs(BASE_DIR, exist_ok=True)

current_font_size = 12
is_bold = True
current_theme = "Dark"

instructions_text = (
    "Ctrl+H: Toggle Help\n"
    "Ctrl+S: Save\n"
    "Ctrl+N: New File\n"
    "Ctrl+B: Toggle Bold\n"
    "Ctrl+E: Edit File Name\n"
    "Ctrl+F: File Browser\n"
    "Ctrl+V: Load File (in browser)\n"
    "Ctrl+D: Delete File (in browser)\n"
    "Ctrl+M: Email Current Text\n"
    "Ctrl+Z: Undo\n"
    "Ctrl+Plus/Minus: Change Font Size\n"
    "Ctrl+T: Toggle Theme Selector\n"
    "Ctrl+Alt-Shift-S: Shutdown"
)

# Global variable to track inline info mode ("help", "theme", or None)
current_info_mode = None


# Recursive function to update all widgets with the new theme.
def update_all_widgets(widget, theme):
    cls = widget.winfo_class()
    try:
        if cls in ("Frame", "TFrame", "LabelFrame", "Labelframe", "Canvas"):
            widget.configure(bg=theme["window_bg"])
        elif cls in ("Label", "Button", "Radiobutton", "Checkbutton"):
            widget.configure(bg=theme["window_bg"], fg=theme["text_fg"])
        elif cls in ("Text", "Entry"):
            widget.configure(
                bg=theme["text_bg"],
                fg=theme["text_fg"],
                insertbackground=theme["text_fg"],
                disabledbackground=theme["filename_bg"],
                disabledforeground=theme["text_fg"],
            )
        elif cls == "Listbox":
            widget.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        else:
            widget.configure(bg=theme["window_bg"])
    except Exception as e:
        print(f"Could not update {widget} ({cls}): {e}")
    for child in widget.winfo_children():
        update_all_widgets(child, theme)


def update_font():
    weight = "bold" if is_bold else "normal"
    new_font = font.Font(family="Courier New", size=current_font_size, weight=weight)
    text_widget.config(font=new_font)


def update_filename_entry_colors():
    global file_entry
    theme = themes[current_theme]
    # If the entry is disabled, force a refresh:
    if file_entry.cget("state") == "disabled":
        file_entry.config(state="normal")
        file_entry.config(
            bg=theme["filename_bg"],
            disabledbackground=theme["filename_bg"],
            fg=theme["text_fg"],
            disabledforeground=theme["text_fg"],
        )
        file_entry.update_idletasks()
        file_entry.config(state="disabled")


def apply_theme(theme_name):
    global current_theme
    if theme_name not in themes:
        print(f"Theme '{theme_name}' not found.")
        return
    current_theme = theme_name
    theme = themes[theme_name]
    print(f"Applying theme: {theme_name}")
    root.tk_setPalette(
        background=theme["window_bg"],
        foreground=theme["text_fg"],
        activeBackground=theme["text_bg"],
        highlightBackground=theme["window_bg"],
    )
    update_all_widgets(root, theme)
    root.after(5500, refresh_file_entry)
    root.update_idletasks()


def refresh_file_entry():
    theme = themes[current_theme]
    file_entry.configure(
        bg=theme["filename_bg"],
        fg=theme["text_fg"],
        disabledbackground=theme["filename_bg"],
        disabledforeground=theme["text_fg"],
    )


def save_file(event=None):
    content = text_widget.get("1.0", tk.END).strip()
    filename = filename_var.get()
    if not filename:
        filename = datetime.datetime.now().strftime("journal_%Y%m%d-%H%M%S.txt")
        filename_var.set(filename)
    full_path = os.path.join(BASE_DIR, filename)
    try:
        with open(full_path, "w") as f:
            f.write(content)
        print(f"Saved file as {full_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error saving file: {e}")
    text_widget.focus_set()


def new_file(event=None):
    text_widget.delete("1.0", tk.END)
    new_filename = datetime.datetime.now().strftime("journal_%Y%m%d-%H%M%S.txt")
    filename_var.set(new_filename)
    file_entry.config(state="normal")
    file_entry.delete(0, tk.END)
    file_entry.insert(0, new_filename)
    finish_editing()
    update_counts()
    text_widget.focus_set()


def increase_font(event=None):
    global current_font_size
    current_font_size += 2
    update_font()
    text_widget.focus_set()


def decrease_font(event=None):
    global current_font_size
    if current_font_size > 6:
        current_font_size -= 2
        update_font()
    text_widget.focus_set()


def toggle_bold(event=None):
    global is_bold
    is_bold = not is_bold
    update_font()
    text_widget.focus_set()


def populate_file_list():
    file_listbox.delete(0, tk.END)
    files = glob.glob(os.path.join(BASE_DIR, "*.txt"))
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for f in files:
        base = os.path.basename(f)
        if not base.startswith("journal_"):
            continue
        file_listbox.insert(tk.END, base)


def force_close_browser():
    if browser_frame.winfo_ismapped():
        browser_frame.place_forget()
        root.after(50, force_close_browser)


def toggle_file_browser(event=None):
    global browser_frame
    if not browser_frame.winfo_ismapped():
        # If the browser frame doesn't exist or isn't mapped, initialize and show it.
        if not browser_frame.winfo_exists():
            init_browser_frame()
        else:
            populate_file_list()
        browser_frame.place(relx=0.75, y=25, anchor="ne", width=250, height=200)
        file_listbox.focus_set()
    else:
        browser_frame.place_forget()
    text_widget.focus_set()


def load_selected_file(event=None):
    selection = file_listbox.curselection()
    if not selection:
        return
    selected_file = file_listbox.get(selection[0])

    # Reserved names check
    reserved = {"file_frame_bg", "filename_bg"}
    if selected_file in reserved:
        print(f"Ignoring reserved file: {selected_file}")
        return

    full_path = os.path.join(BASE_DIR, selected_file)
    if not os.path.exists(full_path):
        print(f"File not found: {selected_file}")
        return
    try:
        with open(full_path, "r") as f:
            content = f.read()
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)
        filename_var.set(selected_file)
        file_entry.config(state="normal")
        file_entry.delete(0, tk.END)
        file_entry.insert(0, selected_file)
        finish_editing()
        update_counts()
        # Destroy the browser frame and reinitialize it.
        browser_frame.destroy()
        init_browser_frame()
    except Exception as e:
        print(f"Error loading file '{selected_file}': {e}")
    text_widget.focus_set()

    selection = file_listbox.curselection()
    if not selection:
        return
    selected_file = file_listbox.get(selection[0])

    # Check for reserved names from your theme.
    reserved = {"file_frame_bg", "filename_bg"}
    if selected_file in reserved:
        print(f"Ignoring reserved file: {selected_file}")
        return

    full_path = os.path.join(BASE_DIR, selected_file)
    if not os.path.exists(full_path):
        print(f"File not found: {selected_file}")
        return
    try:
        with open(full_path, "r") as f:
            content = f.read()
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)
        filename_var.set(selected_file)
        file_entry.config(state="normal")
        file_entry.delete(0, tk.END)
        file_entry.insert(0, selected_file)
        finish_editing()
        update_counts()
        # Instead of forcing a hide, destroy the browser frame:
        browser_frame.destroy()
        # Reinitialize it so it can be opened again later:
        init_browser_frame()
    except Exception as e:
        print(f"Error loading file '{selected_file}': {e}")
    text_widget.focus_set()


def init_browser_frame():
    global browser_frame, file_listbox, browser_scrollbar
    browser_frame = tk.Frame(root)
    file_listbox = tk.Listbox(browser_frame)
    file_listbox.pack(side="left", fill="both", expand=True)
    browser_scrollbar = tk.Scrollbar(browser_frame, orient="vertical", command=file_listbox.yview)
    browser_scrollbar.pack(side="right", fill="y")
    file_listbox.config(yscrollcommand=browser_scrollbar.set)
    # Bind keys for file loading (if not already bound)
    file_listbox.bind("<Return>", load_selected_file)
    file_listbox.bind("<Control-v>", load_selected_file)
    file_listbox.bind("<Control-d>", delete_selected_file)


def delete_selected_file(event=None):
    selection = file_listbox.curselection()
    if not selection:
        messagebox.showinfo("Delete File", "No file selected.")
        return
    selected_file = file_listbox.get(selection[0])
    if selected_file != filename_var.get():
        messagebox.showerror("Delete File", "Selected file does not match the current file.")
        return
    if messagebox.askyesno("Delete File", f"Delete '{selected_file}'?"):
        full_path = os.path.join(BASE_DIR, selected_file)
        try:
            os.remove(full_path)
            text_widget.delete("1.0", tk.END)
            new_filename = datetime.datetime.now().strftime("journal_%Y%m%d-%H%M%S.txt")
            filename_var.set(new_filename)
            file_entry.config(state="normal")
            file_entry.delete(0, tk.END)
            file_entry.insert(0, new_filename)
            finish_editing()
            populate_file_list()
            update_counts()
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting file: {e}")
    text_widget.focus_set()


def toggle_help(event=None):
    global current_info_mode
    if current_info_mode == "help":
        info_frame.grid_remove()
        current_info_mode = None
        text_widget.focus_set()
    else:
        for widget in info_frame.winfo_children():
            widget.destroy()
        help_lbl = tk.Label(info_frame, text=instructions_text, font=("Helvetica", 14), justify="left")
        help_lbl.pack(padx=10, pady=10)
        info_frame.grid()
        current_info_mode = "help"
        text_widget.focus_set()


def apply_theme_selection(theme_var):
    global current_info_mode
    selected = theme_var.get()
    apply_theme(selected)
    info_frame.grid_remove()
    current_info_mode = None
    text_widget.focus_set()
    return "break"


def cancel_theme():
    global current_info_mode
    info_frame.grid_remove()
    current_info_mode = None
    text_widget.focus_set()
    return "break"


def toggle_theme(event=None):
    global current_info_mode
    if current_info_mode == "theme":
        info_frame.grid_remove()
        current_info_mode = None
        text_widget.focus_set()
        return

    for widget in info_frame.winfo_children():
        widget.destroy()
    info_frame.grid()
    current_info_mode = "theme"
    current_colors = themes.get(current_theme, themes["C64"])
    info_frame.configure(bg=current_colors["window_bg"])

    instr_lbl = tk.Label(
        info_frame,
        text="Select Theme (Arrow keys, Enter to apply, Escape to cancel):",
        font=("Helvetica", 14),
        bg=current_colors["window_bg"],
        fg=current_colors["text_fg"],
    )
    instr_lbl.pack(padx=10, pady=5)

    theme_var_local = tk.StringVar(value=current_theme)
    rb_widgets = []
    for t in themes:
        rb = tk.Radiobutton(
            info_frame,
            text=t,
            variable=theme_var_local,
            value=t,
            font=("Helvetica", 14),
            bg=current_colors["window_bg"],
            fg=current_colors["text_fg"],
            selectcolor=current_colors["window_bg"],
            indicatoron=True,
        )
        rb.pack(anchor="w", padx=10, pady=5)
        rb.bind("<Return>", lambda event, var=theme_var_local: apply_theme_selection(var))
        rb.bind("<Escape>", lambda event: cancel_theme())
        rb_widgets.append(rb)
    if rb_widgets:
        rb_widgets[0].focus_set()

    info_frame.bind("<Return>", lambda event: apply_theme_selection(theme_var_local))
    info_frame.bind("<Escape>", lambda event: cancel_theme())


# INLINE FILENAME EDITING (only one definition)
def edit_filename(event=None):
    file_entry.config(state="normal")
    update_all_widgets(root, themes[current_theme])
    file_entry.focus_set()


def finish_editing(event=None):
    theme = themes[current_theme]
    # Get the current filename from the variable
    current_text = filename_var.get()
    file_entry.config(state="normal")
    file_entry.configure(
        bg=theme["filename_bg"],
        fg=theme["text_fg"],
        disabledbackground=theme["filename_bg"],
        disabledforeground=theme["text_fg"],
    )
    # Reinsert the text to ensure it isn’t lost
    file_entry.delete(0, tk.END)
    file_entry.insert(0, current_text)
    file_entry.update_idletasks()  # force refresh
    file_entry.config(state="disabled")
    text_widget.focus_set()
    return "break"


def email_text(event=None):
    content = text_widget.get("1.0", tk.END).strip()
    filename = filename_var.get()
    if not all([SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        messagebox.showwarning("Email Setup", "Configure SMTP settings at the top of the script.")
        return
    msg = MIMEText(content)
    msg["Subject"] = f"Current Text: {filename}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        messagebox.showinfo("Email", "Email Sent")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send email: {e}")
    text_widget.focus_set()


def shutdown_system(event=None):
    if messagebox.askyesno("Shutdown", "Are you sure you want to shut down the system?"):
        if sys.platform.startswith("linux"):
            subprocess.call(["sudo", "shutdown", "now"])
        elif sys.platform.startswith("win"):
            subprocess.call(["shutdown", "/s", "/t", "0"])
    text_widget.focus_set()


def exit_app(event=None):
    root.destroy()


def update_counts(event=None):
    content = text_widget.get("1.0", tk.END).strip()
    words = content.split()
    word_count_label.config(text=f"Words: {len(words)}")
    char_count = len(content.replace("\n", ""))
    char_count_label.config(text=f"Chars: {char_count}")


def force_focus_main(event=None):
    global current_info_mode
    if info_frame.winfo_ismapped():
        info_frame.grid_remove()
        current_info_mode = None
    root.focus_force()
    text_widget.focus_set()
    return "break"


# MAIN WINDOW SETUP
root = tk.Tk()
root.title("Cyber Writer")
root.geometry("1024x600")
root.resizable(True, True)
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

filename_var = tk.StringVar()
filename_var.set(datetime.datetime.now().strftime("journal_%Y%m%d_%H%M.txt"))

top_frame = tk.Frame(root, height=50)
top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
top_frame.grid_propagate(False)

file_label = tk.Label(top_frame, text="File Name:", font=("Helvetica", 14))
file_label.pack(side="left", padx=5)


file_entry = tk.Entry(
    top_frame,
    textvariable=filename_var,
    font=("Helvetica", 14),
    state="disabled",
    takefocus=0,
)

file_entry.bind("<FocusOut>", finish_editing)
file_entry.pack(side="left", fill="x", expand=True, padx=5)

root.bind("<Control-e>", edit_filename)
file_entry.bind("<Return>", finish_editing)

help_hint = tk.Label(top_frame, text="Ctrl+H for help", font=("Helvetica", 12))
word_count_label = tk.Label(top_frame, text="Words: 0", font=("Helvetica", 12))
char_count_label = tk.Label(top_frame, text="Chars: 0", font=("Helvetica", 12))
help_hint.pack(side="left", padx=5)
word_count_label.pack(side="left", padx=5)
char_count_label.pack(side="left", padx=5)

text_frame = tk.Frame(root)
text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
text_frame.grid_propagate(False)
text_frame.grid_rowconfigure(0, weight=1)
text_frame.grid_columnconfigure(0, weight=1)

text_widget = tk.Text(text_frame, wrap="word", undo=True)
text_widget.grid(row=0, column=0, sticky="nsew")
scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
text_widget.config(yscrollcommand=scrollbar.set)

info_frame = tk.Frame(root)
info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
info_frame.grid_remove()

browser_frame = tk.Frame(root)
file_listbox = tk.Listbox(browser_frame)
file_listbox.pack(side="left", fill="both", expand=True)
file_listbox.bind("<Return>", load_selected_file)


browser_scrollbar = tk.Scrollbar(browser_frame, orient="vertical", command=file_listbox.yview)
browser_scrollbar.pack(side="right", fill="y")
file_listbox.config(yscrollcommand=browser_scrollbar.set)

text_widget.bind("<KeyRelease>", update_counts)
update_counts()
update_font()
apply_theme(current_theme)


def simulate_ctrl_e():
    edit_filename()
    finish_editing()
    next_widget = file_entry.tk_focusNext()
    if next_widget:
        next_widget.focus_set()


root.after(100, simulate_ctrl_e)


# KEY BINDINGS
root.bind("<Control-s>", save_file)
root.bind("<Control-n>", new_file)
root.bind("<Control-b>", toggle_bold)
root.bind("<Control-t>", toggle_theme)
root.bind("<Control-plus>", increase_font)
root.bind("<Control-KP_Add>", increase_font)
root.bind("<Control-minus>", decrease_font)
root.bind("<Control-KP_Subtract>", decrease_font)
root.bind("<Control-f>", toggle_file_browser)
root.bind("<Control-m>", email_text)
root.bind("<Control-z>", lambda e: text_widget.edit_undo())
root.bind("<Control-Alt-Shift-s>", shutdown_system)
root.bind("<Control-h>", toggle_help)
root.bind("<Control-F1>", force_focus_main)
file_listbox.bind("<Control-v>", load_selected_file)
file_listbox.bind("<Control-d>", delete_selected_file)

text_widget.focus_set()

try:
    root.mainloop()
except Exception as ex:
    with open("error.log", "a") as log:
        log.write(f"{datetime.datetime.now()}: {traceback.format_exc()}\n")
    print("Unhandled exception occurred:")
    traceback.print_exc()
    sys.exit(1)
