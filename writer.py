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

# SETTINGS FILE
SETTINGS_FILE = "user_settings.json"


# Path for saving files
WRITING_DIR = "text_files"
os.makedirs(WRITING_DIR, exist_ok=True)

# Dark theme colors
THEME = {
    "text_bg": "#1a1a1a",  # Text background color
    "text_fg": "#ffffff",  # Text foreground color
    "window_bg": "#1a1a1a",  # Window background color
}

# Default filename
DEFAULT_FILENAME = "%Y%m%d_%H%M%S.txt"

# Help text
HELP_TEXT = "Ctrl+T: Toggle Help\n" "Ctrl+S: Save\n" "Ctrl+N: New File\n" "Ctrl+F: File Browser\n" "Ctrl+V: Load File (in browser)\n" "Ctrl+M: Email Current Text\n" "Ctrl+Q: Show Text QR-Code"


def apply_theme_to_widget(widget):
    """Apply dark theme to a widget and its children"""
    cls = widget.winfo_class()

    try:
        if cls in ("Frame", "TFrame", "LabelFrame", "Labelframe"):
            widget.configure(bg=THEME["window_bg"])
        elif cls in ("Label", "Button"):
            widget.configure(bg=THEME["window_bg"], fg=THEME["text_fg"])
        elif cls in ("Text", "Entry"):
            widget.configure(bg=THEME["text_bg"], fg=THEME["text_fg"], insertbackground=THEME["text_fg"])
        elif cls == "Listbox":
            widget.configure(bg=THEME["text_bg"], fg=THEME["text_fg"])
        elif cls == "Scrollbar":
            # Make sure scrollbars match the theme
            widget.configure(bg=THEME["window_bg"], troughcolor=THEME["text_bg"])
    except Exception:
        pass

    # Apply to all children widgets recursively
    for child in widget.winfo_children():
        apply_theme_to_widget(child)


def save_file(event=None):
    """Save current text to file"""
    content = text_widget.get("1.0", tk.END).strip()
    filename = filename_var.get()

    if not filename:
        filename = datetime.datetime.now().strftime(DEFAULT_FILENAME)
        filename_var.set(filename)

    full_path = os.path.join(WRITING_DIR, filename)

    try:
        with open(full_path, "w") as f:
            f.write(content)
    except Exception as e:
        messagebox.showerror("Error", f"Error saving file: {e}")

    text_widget.focus_set()
    return "break"


def new_file(event=None):
    """Create a new file"""
    text_widget.delete("1.0", tk.END)
    new_filename = datetime.datetime.now().strftime(DEFAULT_FILENAME)
    filename_var.set(new_filename)

    text_widget.focus_set()
    return "break"


def populate_file_list():
    """Fill the file browser with existing files"""
    file_listbox.delete(0, tk.END)
    files = glob.glob(os.path.join(WRITING_DIR, "*.txt"))
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    for f in files:
        file_listbox.insert(tk.END, os.path.basename(f))


def toggle_file_browser(event=None):
    """Show/hide the file browser"""
    if not browser_frame.winfo_ismapped():
        populate_file_list()
        browser_frame.place(relx=0.75, y=25, anchor="ne", width=250, height=200)
        file_listbox.focus_set()
    else:
        browser_frame.place_forget()

    return "break"


def load_selected_file(event=None):
    """Load the selected file from the browser"""
    selection = file_listbox.curselection()
    if not selection:
        return "break"

    selected_file = file_listbox.get(selection[0])
    full_path = os.path.join(WRITING_DIR, selected_file)

    if not os.path.exists(full_path):
        return "break"

    try:
        with open(full_path, "r") as f:
            content = f.read()

        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)
        filename_var.set(selected_file)

        browser_frame.place_forget()
    except Exception:
        pass

    text_widget.focus_set()
    return "break"


def toggle_help_panel(event=None):
    """Show or hide the help panel"""
    if help_frame.winfo_ismapped():
        help_frame.grid_remove()
    else:
        help_frame.grid()

    text_widget.focus_set()
    return "break"


def email_text(event=None):
    """Email the current text"""
    content = text_widget.get("1.0", tk.END).strip()
    filename = filename_var.get()

    if not all([SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        messagebox.showwarning("Email Setup", "Configure SMTP settings at the top of the script.")
        return "break"

    msg = MIMEText(content)
    msg["Subject"] = f"{filename}"
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
    return "break"


def show_qr_code(event=None):
    """Create and display QR Code to copy text"""
    content = text_widget.get("1.0", tk.END).strip()

    if not content:
        messagebox.showwarning("QR Code", "No text to encode")
        return "break"

    try:
        # Create a temporary file for the QR code
        import tempfile

        import PIL.ImageTk as ImageTk
        import qrcode
        from PIL import Image

        # Create QR code - simplified without constants
        qr_img = qrcode.make(content)

        # Create a temporary file for the image
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_filename = temp_file.name
        temp_file.close()

        # Save QR code image to temp file
        qr_img.save(temp_filename)

        # Display the QR code in a new window
        qr_window = tk.Toplevel(root)
        qr_window.title("Text QR Code")
        qr_window.configure(bg=THEME["window_bg"])

        # Open and display the image using PIL
        img = Image.open(temp_filename)
        photo = ImageTk.PhotoImage(img)

        # Create a label to display the image
        img_label = tk.Label(qr_window, image=photo, bg=THEME["window_bg"])
        # Store reference at window level to prevent garbage collection
        qr_window.photo = photo
        img_label.pack(padx=20, pady=20)

        # Add a note
        note_label = tk.Label(qr_window, text="Scan this QR code to copy the text", font=("Courier New", 12), bg=THEME["window_bg"], fg=THEME["text_fg"])
        note_label.pack(padx=10, pady=10)

        # Add a close button
        close_button = tk.Button(qr_window, text="Close", command=qr_window.destroy, bg=THEME["window_bg"], fg=THEME["text_fg"])
        close_button.pack(pady=10)

        # Center the window on screen
        qr_window.update_idletasks()
        width = qr_window.winfo_width()
        height = qr_window.winfo_height()
        x = (qr_window.winfo_screenwidth() // 2) - (width // 2)
        y = (qr_window.winfo_screenheight() // 2) - (height // 2)
        qr_window.geometry(f"{width}x{height}+{x}+{y}")

        # Configure the window to be modal
        qr_window.transient(root)
        qr_window.grab_set()

        # Clean up the temp file when the window is closed
        def on_close():
            try:
                os.unlink(temp_filename)
            except:
                pass
            qr_window.destroy()

        qr_window.protocol("WM_DELETE_WINDOW", on_close)
        close_button.config(command=on_close)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to create QR code: {e}")
        traceback.print_exc()

    text_widget.focus_set()
    return "break"


def load_email_settings():
    default_settings = {"smtp_server": "", "smtp_port": 587, "sender_email": "", "sender_password": "", "recipient_email": ""}

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)

            # Merge default settings with loaded settings
            for key in default_settings:
                if key not in settings:
                    settings[key] = default_settings[key]

            return settings
        except Exception as e:
            print(f"Error loading email settings: {e}")
            # Create a default settings file if loading fails
            try:
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(default_settings, f, indent=4)
                print("Default email settings file created.")
            except Exception as create_err:
                print(f"Error creating default settings file: {create_err}")
            return default_settings
    else:
        # Create default settings file if it doesn't exist
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_settings, f, indent=4)
            print("Default email settings file created.")
        except Exception as create_err:
            print(f"Error creating default settings file: {create_err}")
        return default_settings


# Load email settings
email_settings = load_email_settings()

# Use loaded settings
SMTP_SERVER = email_settings.get("smtp_server", "")
SMTP_PORT = email_settings.get("smtp_port", 587)
SENDER_EMAIL = email_settings.get("sender_email", "")
SENDER_PASSWORD = email_settings.get("sender_password", "")
RECIPIENT_EMAIL = email_settings.get("recipient_email", "")

# MAIN WINDOW SETUP
root = tk.Tk()
root.title("Focused Writer")
root.geometry("800x600")

# Make main window expandable
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

# File name tracking
filename_var = tk.StringVar()
filename_var.set(datetime.datetime.now().strftime(DEFAULT_FILENAME))

# Top bar with filename
header_frame = tk.Frame(root)
header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

file_label = tk.Label(header_frame, text="File:", font=("Courier New", 12))
file_label.pack(side="left", padx=5)

filename_label = tk.Label(header_frame, textvariable=filename_var, font=("Courier New", 12))
filename_label.pack(side="left", fill="x", expand=True, padx=5)

help_hint = tk.Label(header_frame, text="Ctrl+T for help", font=("Courier New", 10))
help_hint.pack(side="right", padx=5)

# Main text area
text_frame = tk.Frame(root)
text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
text_frame.grid_rowconfigure(0, weight=1)
text_frame.grid_columnconfigure(0, weight=1)

text_widget = tk.Text(text_frame, wrap="word", font=("Courier New", 12))
text_widget.grid(row=0, column=0, sticky="nsew")

scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
text_widget.config(yscrollcommand=scrollbar.set)

# Help panel
help_frame = tk.Frame(root)
help_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
help_label = tk.Label(help_frame, text=HELP_TEXT, font=("Courier New", 12), justify="left")
help_label.pack(padx=10, pady=10)
help_frame.grid_remove()  # Initially hidden

# File browser (initially hidden)
browser_frame = tk.Frame(root)
file_listbox = tk.Listbox(browser_frame, font=("Courier New", 10))
file_listbox.pack(side="left", fill="both", expand=True)

browser_scrollbar = tk.Scrollbar(browser_frame, orient="vertical", command=file_listbox.yview)
browser_scrollbar.pack(side="right", fill="y")
file_listbox.config(yscrollcommand=browser_scrollbar.set)

# Apply theme to all widgets
root.tk_setPalette(background=THEME["window_bg"], foreground=THEME["text_fg"])
apply_theme_to_widget(root)

# KEY BINDINGS
root.bind("<Control-s>", save_file)
root.bind("<Control-n>", new_file)
root.bind("<Control-f>", toggle_file_browser)
root.bind("<Control-t>", toggle_help_panel)
root.bind("<Control-m>", email_text)
root.bind("<Control-q>", show_qr_code)
file_listbox.bind("<Return>", load_selected_file)
file_listbox.bind("<Control-v>", load_selected_file)

# Start the app with focus on text
text_widget.focus_set()

if __name__ == "__main__":
    root.mainloop()
