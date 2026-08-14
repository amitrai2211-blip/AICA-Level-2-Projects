import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from modules.license import generate_signature

# Color Palette (Matches GYM PRO+)
BG_PRIMARY = "#F3F4F6"
BG_SECONDARY = "#FFFFFF"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
TEXT_MAIN = "#111827"
TEXT_MUTED = "#4B5563"
SUCCESS = "#047857"
CARD_BORDER = "#D1D5DB"
CURSOR_COLOR = "red"

class KeyGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GYM PRO+ | Subscription Activation Key Generator")
        self.geometry("500x520")
        self.configure(bg=BG_PRIMARY)
        self.resizable(False, False)
        
        # Build UI layout
        self.build_ui()
        
    def build_ui(self):
        # Card Panel
        panel = tk.Frame(self, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=30, pady=30)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=440, height=460)
        
        # Header
        tk.Label(panel, text="🔑 KEY GENERATOR", font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(0, 2))
        tk.Label(panel, text="GYM PRO+ Subscription Manager", font=("Segoe UI", 10), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 20))
        
        # 1. Machine ID Input
        tk.Label(panel, text="CLIENT MACHINE ID:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.ent_mid = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 11), bd=1, highlightbackground=CARD_BORDER)
        self.ent_mid.pack(fill="x", pady=(5, 15), ipady=6)
        self.ent_mid.focus_set()
        
        # 2. Expiry Date Input (Pre-filled with 1 year from today)
        today = datetime.now()
        one_year_later = today + timedelta(days=365)
        default_expiry = one_year_later.strftime("%d-%m-%Y")
        
        tk.Label(panel, text="EXPIRY DATE (DD-MM-YYYY):", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.ent_expiry = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 11), bd=1, highlightbackground=CARD_BORDER)
        self.ent_expiry.insert(0, default_expiry)
        self.ent_expiry.pack(fill="x", pady=(5, 20), ipady=6)
        
        # 3. Generate Button
        btn_gen = tk.Button(panel, text="GENERATE ACTIVATION KEY", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY,
                            activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, pady=8,
                            cursor="hand2", command=self.generate_key)
        btn_gen.pack(fill="x", pady=(0, 20))
        
        # 4. Result Key Frame (Readonly key + Copy button)
        tk.Label(panel, text="GENERATED KEY:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        res_frame = tk.Frame(panel, bg=BG_SECONDARY)
        res_frame.pack(fill="x", pady=(5, 0))
        
        self.ent_key = tk.Entry(res_frame, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"), bd=1, highlightbackground=CARD_BORDER)
        self.ent_key.pack(side="left", fill="x", expand=True, ipady=6)
        self.ent_key.config(state="readonly")
        
        self.btn_copy = tk.Button(res_frame, text="📋 Copy", font=("Segoe UI", 9, "bold"), bg=SUCCESS, fg=BG_SECONDARY,
                                  activebackground="#03543F", activeforeground=BG_SECONDARY, bd=0, padx=12, pady=5,
                                  cursor="hand2", command=self.copy_key)
        self.btn_copy.pack(side="right", padx=(8, 0))
        self.btn_copy.config(state="disabled")
        
        # Footer Credits
        tk.Label(panel, text="Developed by \"CA Amit Rai, Bhilai\"", font=("Segoe UI", 9, "italic", "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(25, 0))

    def generate_key(self):
        mid = self.ent_mid.get().strip().upper()
        if not mid:
            messagebox.showerror("Validation Error", "Client Machine ID cannot be empty.")
            return
            
        expiry_ui = self.ent_expiry.get().strip()
        try:
            dt = datetime.strptime(expiry_ui, "%d-%m-%Y")
            expiry_db = dt.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid expiry date format. Use DD-MM-YYYY.")
            return
            
        # Compute activation key signature
        sig = generate_signature(mid, expiry_db)
        license_key = f"{mid}-{expiry_db}-{sig}"
        
        # Display key
        self.ent_key.config(state="normal")
        self.ent_key.delete(0, tk.END)
        self.ent_key.insert(0, license_key)
        self.ent_key.config(state="readonly")
        
        # Enable copy button
        self.btn_copy.config(state="normal")
        
    def copy_key(self):
        key = self.ent_key.get().strip()
        if key:
            self.clipboard_clear()
            self.clipboard_append(key)
            messagebox.showinfo("Copied Successfully", "Activation key copied to clipboard!")

if __name__ == "__main__":
    app = KeyGeneratorApp()
    app.mainloop()
