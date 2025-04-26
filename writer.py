#!/usr/bin/env python3
"""
Cyber Writer: A minimalist, focused writing application with theme support.

This application provides a distraction-free writing environment with
multiple themes, file management, and additional utilities.

Dependencies: tkinter (standard library)
"""

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

# Constants
SETTINGS_FILE = "writer_settings.json"
SMTP_CONFIG_FILE = "smtp_config.json"
BASE_DIR = "writing_files"


class CyberWriter:
    def __init__(self):
        """Initialize the Cyber Writer application."""
        # Ensure writing directory exists
        os.makedirs(BASE_DIR, exist_ok=True)

        # Load settings and themes
        self.settings = self._load_settings()
        self.themes = self.settings.get("themes", {})

        # Load SMTP configuration
        self.smtp_config = self._load_smtp_config()

        # Application state variables
        self.current_font_size = 12
        self.is_bold = True
        self.current_theme = "Dark"
        self.current_info_mode = None

        # User interface instructions
        self.instructions_text = (
            "Keyboard Shortcuts:\n"
            "Ctrl+H: Toggle Help\n"
            "Ctrl+S: Save\n"
            "Ctrl+N: New File\n"
            "Ctrl+B: Toggle Bold\n"
            "Ctrl+E: Edit File Name\n"
            "Ctrl+F: File Browser\n"
            "Ctrl+V: Load File\n"
            "Ctrl+D: Delete File\n"
            "Ctrl+M: Email Current Text\n"
            "Ctrl+Z: Undo\n"
            "Ctrl+Plus/Minus: Change Font Size\n"
            "Ctrl+T: Toggle Theme\n"
            "Ctrl+Alt-Shift-S: Shutdown"
        )

        # Initialize main application window
        self._setup_main_window()
        self._setup_key_bindings()
        self._setup_initial_state()

    def _load_settings(self):
        """
        Load application settings from JSON file.
        Creates default settings if file doesn't exist.
        """
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

        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                print("Settings loaded from file.")
            else:
                settings = default_settings
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(settings, f, indent=4)
                print("Default settings file created.")
        except Exception as e:
            print(f"Error loading/creating settings: {e}")
            settings = default_settings

        return settings

    def _load_smtp_config(self):
        """
        Load SMTP configuration from JSON file.
        Creates a template config file if it doesn't exist.
        """
        default_config = {"server": "smtp.gmail.com", "port": 587, "sender_email": "", "sender_password": "", "recipient_email": ""}

        try:
            if os.path.exists(SMTP_CONFIG_FILE):
                with open(SMTP_CONFIG_FILE, "r") as f:
                    config = json.load(f)
                print("SMTP configuration loaded.")
            else:
                config = default_config
                with open(SMTP_CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=4)
                print("Default SMTP configuration file created.")
        except Exception as e:
            print(f"Error loading/creating SMTP config: {e}")
            config = default_config

        return config

    def _setup_main_window(self):
        """Set up the main application window and initial configurations."""
        self.root = tk.Tk()
        self.root.title("Cyber Writer")
        self.root.geometry("1024x600")
        self.root.resizable(True, True)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Filename variable
        self.filename_var = tk.StringVar()
        self.filename_var.set(datetime.datetime.now().strftime("journal_%Y%m%d_%H%M.txt"))

        # Top frame
        self._create_top_frame()

        # Text frame with scrollbar
        self._create_text_frame()

        # Info frame for help and theme selection
        self.info_frame = tk.Frame(self.root)
        self.info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.info_frame.grid_remove()

        # Browser frame for file list
        self._create_browser_frame()

    def _create_top_frame(self):
        """Create the top frame with file name entry and labels."""
        top_frame = tk.Frame(self.root, height=50)
        top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        top_frame.grid_propagate(False)

        file_label = tk.Label(top_frame, text="File Name:", font=("Helvetica", 14))
        file_label.pack(side="left", padx=5)

        self.file_entry = tk.Entry(
            top_frame,
            textvariable=self.filename_var,
            font=("Helvetica", 14),
            state="disabled",
            takefocus=0,
        )
        self.file_entry.bind("<FocusOut>", self.finish_editing)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=5)

        help_hint = tk.Label(top_frame, text="Ctrl+H for help", font=("Helvetica", 12))
        self.word_count_label = tk.Label(top_frame, text="Words: 0", font=("Helvetica", 12))
        self.char_count_label = tk.Label(top_frame, text="Chars: 0", font=("Helvetica", 12))

        help_hint.pack(side="left", padx=5)
        self.word_count_label.pack(side="left", padx=5)
        self.char_count_label.pack(side="left", padx=5)

    def _create_text_frame(self):
        """Create the text editing frame with scrollbar."""
        text_frame = tk.Frame(self.root)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        text_frame.grid_propagate(False)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.text_widget = tk.Text(text_frame, wrap="word", undo=True)
        self.text_widget.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(text_frame, command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.text_widget.config(yscrollcommand=scrollbar.set)
        self.text_widget.bind("<KeyRelease>", self.update_counts)

    def _create_browser_frame(self):
        """Create the file browser frame."""
        self.browser_frame = tk.Frame(self.root)
        self.file_listbox = tk.Listbox(self.browser_frame)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        browser_scrollbar = tk.Scrollbar(self.browser_frame, orient="vertical", command=self.file_listbox.yview)
        browser_scrollbar.pack(side="right", fill="y")

        self.file_listbox.config(yscrollcommand=browser_scrollbar.set)
        self.file_listbox.bind("<Return>", self.load_selected_file)

    def _setup_key_bindings(self):
        """Set up all keyboard shortcuts."""
        # Application controls
        self.root.bind("<Control-s>", self.save_file)
        self.root.bind("<Control-n>", self.new_file)
        self.root.bind("<Control-f>", self.toggle_file_browser)

        # Editing
        self.root.bind("<Control-b>", self.toggle_bold)
        self.root.bind("<Control-e>", self.edit_filename)
        self.root.bind("<Control-z>", lambda e: self.text_widget.edit_undo())

        # Theme and UI
        self.root.bind("<Control-t>", self.toggle_theme)
        self.root.bind("<Control-h>", self.toggle_help)

        # Font manipulation
        self.root.bind("<Control-plus>", self.increase_font)
        self.root.bind("<Control-KP_Add>", self.increase_font)
        self.root.bind("<Control-minus>", self.decrease_font)
        self.root.bind("<Control-KP_Subtract>", self.decrease_font)

        # Special functions
        self.root.bind("<Control-m>", self.email_text)
        self.root.bind("<Control-Alt-Shift-s>", self.shutdown_system)

        # Filename editing
        self.file_entry.bind("<Return>", self.finish_editing)

        # File list bindings
        self.file_listbox.bind("<Control-v>", self.load_selected_file)
        self.file_listbox.bind("<Control-d>", self.delete_selected_file)

    def _setup_initial_state(self):
        """Set up initial application state."""
        # Apply default theme
        self.apply_theme(self.current_theme)

        # Update font and counts
        self.update_font()
        self.update_counts()

        # Set focus
        self.text_widget.focus_set()

        # Simulate initial filename edit
        self.root.after(100, self.simulate_ctrl_e)

    def simulate_ctrl_e(self):
        """Simulate Ctrl+E to set initial filename state."""
        self.edit_filename()
        self.finish_editing()
        next_widget = self.file_entry.tk_focusNext()
        if next_widget:
            next_widget.focus_set()

    def save_file(self, event=None):
        """Save current text to a file."""
        content = self.text_widget.get("1.0", tk.END).strip()
        filename = self.filename_var.get()

        if not filename:
            filename = datetime.datetime.now().strftime("journal_%Y%m%d-%H%M%S.txt")
            self.filename_var.set(filename)

        full_path = os.path.join(BASE_DIR, filename)
        try:
            with open(full_path, "w") as f:
                f.write(content)
            print(f"Saved file as {full_path}")
            messagebox.showinfo("Save", f"File saved: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving file: {e}")

        self.text_widget.focus_set()

    def new_file(self, event=None):
        """Create a new file."""
        self.text_widget.delete("1.0", tk.END)
        new_filename = datetime.datetime.now().strftime("journal_%Y%m%d-%H%M%S.txt")

        self.filename_var.set(new_filename)
        self.file_entry.config(state="normal")
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, new_filename)

        self.finish_editing()
        self.update_counts()
        self.text_widget.focus_set()

    def toggle_bold(self, event=None):
        """Toggle text boldness."""
        self.is_bold = not self.is_bold
        self.update_font()
        self.text_widget.focus_set()

    def update_font(self):
        """Update font based on current settings."""
        weight = "bold" if self.is_bold else "normal"
        new_font = font.Font(family="Courier New", size=self.current_font_size, weight=weight)
        self.text_widget.config(font=new_font)

    def increase_font(self, event=None):
        """Increase font size."""
        self.current_font_size += 2
        self.update_font()
        self.text_widget.focus_set()

    def decrease_font(self, event=None):
        """Decrease font size."""
        if self.current_font_size > 6:
            self.current_font_size -= 2
            self.update_font()
        self.text_widget.focus_set()

    def edit_filename(self, event=None):
        """Enable filename editing."""
        self.file_entry.config(state="normal")
        self.file_entry.focus_set()

    def finish_editing(self, event=None):
        """Finish filename editing."""
        theme = self.themes[self.current_theme]
        current_text = self.filename_var.get()

        self.file_entry.config(state="normal")
        self.file_entry.configure(
            bg=theme["filename_bg"],
            fg=theme["text_fg"],
            disabledbackground=theme["filename_bg"],
            disabledforeground=theme["text_fg"],
        )

        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, current_text)
        self.file_entry.update_idletasks()
        self.file_entry.config(state="disabled")

        self.text_widget.focus_set()
        return "break"

    def update_counts(self, event=None):
        """Update word and character counts."""
        content = self.text_widget.get("1.0", tk.END).strip()
        words = content.split()
        self.word_count_label.config(text=f"Words: {len(words)}")

        char_count = len(content.replace("\n", ""))
        self.char_count_label.config(text=f"Chars: {char_count}")

    def run(self):
        """Run the application main loop."""
        try:
            self.root.mainloop()
        except Exception as ex:
            self._log_error(ex)

    def _log_error(self, exception):
        """Log unhandled exceptions to an error file."""
        with open("error.log", "a") as log:
            log.write(f"{datetime.datetime.now()}: {traceback.format_exc()}\n")
        print("Unhandled exception occurred:")
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the Cyber Writer application."""
    app = CyberWriter()
    app.run()


if __name__ == "__main__":
    main()
