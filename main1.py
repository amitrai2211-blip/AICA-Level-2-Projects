import os
import sys
import shutil
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta

# Import modules
from modules.config import load_settings, save_settings, get_current_year_string, get_data_dir, get_project_base_dir
from modules.database import initialize_database, load_dataframe, save_dataframe
from modules.license import load_license_info, verify_key, activate_license, get_machine_id
from modules.members import (
    add_member, update_member, delete_member, get_member_details, get_reminders, check_and_update_statuses
)
from modules.trainers import (
    add_trainer, update_trainer, delete_trainer, reassign_members, get_trainer_members
)
from modules.attendance import check_in_member, check_out_member, generate_member_qr, get_today_checkins, get_events_by_date_range, delete_attendance_record, check_out_member_by_record_id
from modules.workouts import (
    get_workout_templates, add_workout_plan, get_member_workout_plans, assign_plan_to_member, delete_workout_plan, update_workout_plan
)
from modules.diet import (
    get_diet_templates, add_diet_plan, get_member_diet_plans, assign_diet_to_member, delete_diet_plan, update_diet_plan
)
from modules.payments import (
    record_payment, get_member_payments, get_financial_summary, add_measurement, get_member_measurements, calculate_bmi
)
from modules.reports import export_all_reports
from modules.backup import create_backup, restore_backup, split_data_for_new_year
from modules.users import authenticate_user, add_user, change_password, get_users_list, delete_user
from modules.visitors import add_visitor, get_visitors_list

# Try to import PIL
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

def db_to_ui_date(db_date_str):
    """Converts YYYY-MM-DD from DB to DD-MM-YYYY for display in UI."""
    if not db_date_str:
        return ""
    db_date_str = str(db_date_str).strip()
    if len(db_date_str) == 10 and db_date_str[2] == "-" and db_date_str[5] == "-":
        return db_date_str
    try:
        dt = datetime.strptime(db_date_str, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return db_date_str

def ui_to_db_date(ui_date_str):
    """Converts DD-MM-YYYY back to YYYY-MM-DD for DB storage."""
    if not ui_date_str:
        return ""
    ui_date_str = str(ui_date_str).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(ui_date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ui_date_str

# Color Palette (High-Contrast Bright Theme)
BG_PRIMARY = "#F3F4F6"      # Light grey screen background
BG_SECONDARY = "#FFFFFF"    # White card/panel background
BG_SIDEBAR = "#E5E7EB"      # Slightly darker grey for sidebar
ACCENT = "#2563EB"          # Royal Blue Accent
ACCENT_HOVER = "#1D4ED8"
TEXT_MAIN = "#111827"       # Dark grey/black text
TEXT_MUTED = "#4B5563"      # Medium grey text
SUCCESS = "#047857"         # Dark Green Accent
ALERT = "#B91C1C"           # Dark Red Accent
CARD_BORDER = "#D1D5DB"     # Border grey
CURSOR_COLOR = "red"        # Bright flashing cursor

class GymProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GYM PRO+ | Gym Management System")
        self.geometry("1180x760")
        self.configure(bg=BG_PRIMARY)
        
        # Initialize database structures
        initialize_database()
        check_and_update_statuses()
        
        self.settings = load_settings()
        self.current_user = None
        self.current_view = None
        
        # Date range filters on Dashboard (Default: past 30 days)
        today = datetime.now()
        start = today - timedelta(days=30)
        self.dash_start_date = start.strftime("%Y-%m-%d")
        self.dash_end_date = today.strftime("%Y-%m-%d")
        
        # Custom styles configuration
        self.setup_styles()
        
        # Initialize structures
        self.login_frame = None
        self.main_container = None
        self.sidebar_frame = None
        self.content_frame = None
        
        # Check license key on startup
        self.license_expiry = None
        key = load_license_info()
        valid, info = verify_key(key)
        if valid:
            self.license_expiry = info
            self.show_login_screen()
        else:
            self.show_activation_screen(info)
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        
        # Notebook setup
        style.configure("TNotebook", background=BG_PRIMARY, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_SIDEBAR, foreground=TEXT_MAIN, borderwidth=0, padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", BG_SECONDARY)])
        
        # Treeview styling
        style.configure("Treeview", 
                        background=BG_SECONDARY, 
                        foreground=TEXT_MAIN, 
                        fieldbackground=BG_SECONDARY,
                        rowheight=35,
                        font=("Segoe UI", 10),
                        borderwidth=1,
                        gridcolor=CARD_BORDER)
        style.configure("Treeview.Heading", 
                        background=BG_SIDEBAR, 
                        foreground=TEXT_MAIN, 
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=1)
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", BG_SECONDARY)])
        style.configure("Vertical.TScrollbar", gripcount=0, background=BG_SIDEBAR, troughcolor=BG_PRIMARY, borderwidth=0)

    # --- VIEW: LOGIN PORTAL (Blank entries on startup) ---
    def show_login_screen(self):
        if self.main_container:
            self.main_container.destroy()
        if self.login_frame:
            self.login_frame.destroy()
            
        self.login_frame = tk.Frame(self, bg=BG_PRIMARY)
        self.login_frame.pack(fill="both", expand=True)
        
        # Login Card Panel
        panel = tk.Frame(self.login_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=40, pady=40)
        panel.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(panel, text="💪 GYM PRO+", font=("Segoe UI", 26, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(0, 5))
        tk.Label(panel, text="Operational Login Portal", font=("Segoe UI", 11), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 25))
        
        # Username ID entry (Blank)
        tk.Label(panel, text="USERNAME:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.ent_login_user = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 11), bd=1, highlightbackground=CARD_BORDER, width=28)
        self.ent_login_user.pack(pady=(5, 15), ipady=6)
        self.ent_login_user.focus_set()
        
        # Password entry (Blank)
        tk.Label(panel, text="PASSWORD:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.ent_login_pass = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 11), show="*", bd=1, highlightbackground=CARD_BORDER, width=28)
        self.ent_login_pass.pack(pady=(5, 25), ipady=6)
        
        btn_login = tk.Button(panel, text="LOG IN SECURELY", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY,
                              activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, width=28, pady=10,
                              cursor="hand2", command=self.handle_login)
        btn_login.pack()
        
        # Developer Credits
        tk.Label(panel, text="Developed by \"CA Amit Rai, Bhilai\"", font=("Segoe UI", 9, "italic", "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(20, 0))
        
    def handle_login(self):
        username = self.ent_login_user.get().strip()
        password = self.ent_login_pass.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all credentials.")
            return
            
        success, role = authenticate_user(username, password)
        if success:
            self.current_user = {"username": username, "role": role}
            self.login_frame.destroy()
            
            # Check gym details setup
            gym_name = self.settings.get("gym_name", "")
            gym_address = self.settings.get("gym_address", "")
            if not gym_name or not gym_address:
                self.show_gym_setup_modal()
            else:
                self.build_main_app()
        else:
            messagebox.showerror("Unauthorized", "Invalid credentials entered.")

    def show_gym_setup_modal(self):
        modal = tk.Toplevel(self)
        modal.title("Configure Gym Details")
        modal.geometry("450x320")
        modal.configure(bg=BG_PRIMARY)
        modal.transient(self)
        modal.grab_set()
        modal.focus_set()
        
        modal.update_idletasks()
        w = modal.winfo_width()
        h = modal.winfo_height()
        extra_w = (modal.winfo_screenwidth() - w) // 2
        extra_h = (modal.winfo_screenheight() - h) // 2
        modal.geometry(f"+{extra_w}+{extra_h}")
        
        panel = tk.Frame(modal, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=30, pady=25)
        panel.pack(fill="both", expand=True, padx=15, pady=15)
        
        tk.Label(panel, text="🏢 Gym Configuration", font=("Segoe UI", 16, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(0, 15))
        
        tk.Label(panel, text="GYM NAME:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ent_name = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 11), bd=1, highlightbackground=CARD_BORDER)
        ent_name.pack(fill="x", pady=(5, 15), ipady=4)
        ent_name.focus_set()
        
        tk.Label(panel, text="GYM ADDRESS:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ent_addr = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 11), bd=1, highlightbackground=CARD_BORDER)
        ent_addr.pack(fill="x", pady=(5, 20), ipady=4)
        
        def save_details():
            name = ent_name.get().strip()
            addr = ent_addr.get().strip()
            if not name or not addr:
                messagebox.showerror("Error", "Both name and address are required.")
                return
            self.settings["gym_name"] = name
            self.settings["gym_address"] = addr
            save_settings(self.settings)
            
            modal.destroy()
            self.build_main_app()
            
        btn_save = tk.Button(panel, text="SAVE GYM DETAILS", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY,
                             activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, pady=8,
                             cursor="hand2", command=save_details)
        btn_save.pack(fill="x")
        
        modal.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    def show_activation_screen(self, error_msg=""):
        if self.main_container:
            self.main_container.destroy()
        if self.login_frame:
            self.login_frame.destroy()
            
        self.login_frame = tk.Frame(self, bg=BG_PRIMARY)
        self.login_frame.pack(fill="both", expand=True)
        
        # Activation Card Panel
        panel = tk.Frame(self.login_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=40, pady=40)
        panel.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(panel, text="💪 GYM PRO+", font=("Segoe UI", 26, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(pady=(0, 5))
        tk.Label(panel, text="Software Activation & Licensing", font=("Segoe UI", 11, "bold"), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 10))
        
        if error_msg:
            tk.Label(panel, text=error_msg, font=("Segoe UI", 9, "bold"), fg=ALERT, bg=BG_SECONDARY, wraplength=300).pack(pady=(0, 15))
            
        m_id = get_machine_id()
        
        # Machine ID Display
        tk.Label(panel, text="YOUR MACHINE ID:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ent_mid = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 11, "bold"), bd=1, highlightbackground=CARD_BORDER, width=28)
        ent_mid.insert(0, m_id)
        ent_mid.config(state="readonly")
        ent_mid.pack(pady=(5, 15), ipady=6)
        
        # Activation Key Input
        tk.Label(panel, text="ENTER ACTIVATION KEY:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.ent_activation_key = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER, width=28)
        self.ent_activation_key.pack(pady=(5, 25), ipady=6)
        
        btn_activate = tk.Button(panel, text="ACTIVATE APPLICATION", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY,
                                activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, width=28, pady=10,
                                cursor="hand2", command=self.submit_activation)
        btn_activate.pack()
        
        # Developer Credits
        tk.Label(panel, text="Developed by \"CA Amit Rai, Bhilai\"\nFor keys, please email/contact developer.", font=("Segoe UI", 9, "italic", "bold"), fg=ACCENT, bg=BG_SECONDARY, justify="center").pack(pady=(20, 0))

    def submit_activation(self):
        key = self.ent_activation_key.get().strip()
        if not key:
            messagebox.showerror("Activation Failed", "Please enter an activation key.")
            return
            
        success, msg = activate_license(key)
        if success:
            messagebox.showinfo("Activation Successful", msg)
            self.license_expiry = key.split("-")[1] # extract YYYY-MM-DD from key
            self.show_login_screen()
        else:
            messagebox.showerror("Activation Failed", msg)

    def handle_logout_exit(self):
        modal = tk.Toplevel(self)
        modal.title("Log Out or Exit")
        modal.geometry("520x180")
        modal.configure(bg=BG_PRIMARY)
        modal.transient(self)
        modal.grab_set()
        modal.focus_set()
        
        modal.update_idletasks()
        w = modal.winfo_width()
        h = modal.winfo_height()
        extra_w = (modal.winfo_screenwidth() - w) // 2
        extra_h = (modal.winfo_screenheight() - h) // 2
        modal.geometry(f"+{extra_w}+{extra_h}")
        
        panel = tk.Frame(modal, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        panel.pack(fill="both", expand=True, padx=15, pady=15)
        
        tk.Label(panel, text="What would you like to do?", font=("Segoe UI", 12, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(pady=(0, 15))
        
        btn_box = tk.Frame(panel, bg=BG_SECONDARY)
        btn_box.pack(fill="x")
        
        def change_user():
            modal.destroy()
            self.current_user = None
            if self.main_container:
                self.main_container.destroy()
            self.show_login_screen()
            
        def exit_app():
            modal.destroy()
            self.destroy()
            
        btn_logout = tk.Button(btn_box, text="🔑 Change Login ID", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY,
                               activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, padx=10, pady=8,
                               cursor="hand2", command=change_user)
        btn_logout.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_exit = tk.Button(btn_box, text="🚪 Exit Application", font=("Segoe UI", 10, "bold"), bg=ALERT, fg=BG_SECONDARY,
                             activebackground="#991B1B", activeforeground=BG_SECONDARY, bd=0, padx=10, pady=8,
                             cursor="hand2", command=exit_app)
        btn_exit.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        btn_cancel = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 10, "bold"), bg=BG_SIDEBAR, fg=TEXT_MAIN,
                               activebackground="#D1D5DB", activeforeground=TEXT_MAIN, bd=0, padx=10, pady=8,
                               cursor="hand2", command=modal.destroy)
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(5, 0))

    def build_main_app(self):
        self.main_container = tk.Frame(self, bg=BG_PRIMARY)
        self.main_container.pack(fill="both", expand=True)
        
        # Create Sidebar
        self.create_sidebar()
        
        # Create Content Frame
        self.content_frame = tk.Frame(self.main_container, bg=BG_PRIMARY)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        # Load default Dashboard
        self.show_dashboard()
        
    def create_sidebar(self):
        self.sidebar_frame = tk.Frame(self.main_container, bg=BG_SIDEBAR, width=225)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)
        
        # Header
        lbl_logo = tk.Label(self.sidebar_frame, text="💪 GYM PRO+", font=("Segoe UI", 18, "bold"), fg=ACCENT, bg=BG_SIDEBAR)
        lbl_logo.pack(pady=20)
        
        lbl_user = tk.Label(self.sidebar_frame, text=f"👤 {self.current_user['username']} ({self.current_user['role']})", 
                            font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG_SIDEBAR)
        lbl_user.pack(pady=(0, 5))
        
        lbl_sub = tk.Label(self.sidebar_frame, text=f"FY: {self.settings.get('current_year', get_current_year_string())}", 
                           font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SIDEBAR)
        lbl_sub.pack(pady=(0, 15))
        
        # Nav Buttons
        nav_items = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 Members", self.show_members),
            ("🤝 Trainers", self.show_trainers),
            ("📅 Attendance", self.show_attendance),
            ("🏋️ Workouts & Diet", self.show_planners)
        ]
        
        if self.current_user["role"] == "Admin":
            nav_items.append(("💳 Payments & Billing", self.show_payments))
            nav_items.append(("⚙️ Maintenance", self.show_settings))
        else:
            nav_items.append(("⚙️ Change Password", self.open_change_password_modal))
            
        nav_items.append(("🚪 Log Out & Exit", self.handle_logout_exit))
        
        self.nav_buttons = {}
        for text, command in nav_items:
            btn = tk.Button(self.sidebar_frame, text=text, font=("Segoe UI", 11), fg=TEXT_MAIN, bg=BG_SIDEBAR,
                            activebackground=BG_SECONDARY, activeforeground=ACCENT,
                            bd=0, anchor="w", padx=20, pady=12, command=command, cursor="hand2")
            btn.pack(fill="x")
            self.nav_buttons[text] = btn
            
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=BG_SECONDARY))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG_SIDEBAR))
            
        # Developer Credits & Subscription Info
        credits_frame = tk.Frame(self.sidebar_frame, bg=BG_SIDEBAR, pady=15)
        credits_frame.pack(side="bottom", fill="x")
        
        lbl_dev = tk.Label(credits_frame, text="Developed by:\nCA Amit Rai, Bhilai", font=("Segoe UI", 8, "bold", "italic"), fg=TEXT_MUTED, bg=BG_SIDEBAR)
        lbl_dev.pack()
        
        if self.license_expiry:
            expiry_ui = db_to_ui_date(self.license_expiry)
            lbl_lic = tk.Label(credits_frame, text=f"Subscription expires:\n{expiry_ui}", font=("Segoe UI", 7), fg=TEXT_MUTED, bg=BG_SIDEBAR)
            lbl_lic.pack(pady=(5, 0))
            
    def clear_content(self, active_tab_text):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        for text, btn in self.nav_buttons.items():
            if text == active_tab_text:
                btn.config(fg=ACCENT, font=("Segoe UI", 11, "bold"))
            else:
                btn.config(fg=TEXT_MAIN, font=("Segoe UI", 11))
                
        # Draw background watermark
        self.add_page_watermark(self.content_frame)

    def add_page_watermark(self, frame):
        """Adds a subtle, large watermark of the Gym Name and Address centered in the background of the frame."""
        gym_name = self.settings.get("gym_name", "GYM PRO+")
        gym_address = self.settings.get("gym_address", "")
        watermark_txt = f"{gym_name}\n{gym_address}" if gym_address else gym_name
        watermark_lbl = tk.Label(frame, text=watermark_txt, font=("Segoe UI", 40, "bold"), fg="#EBEFF9", bg=frame.cget("bg"), justify="center")
        watermark_lbl.place(relx=0.5, rely=0.5, anchor="center")
        watermark_lbl.lower()

    def add_gym_branding_header(self, header_frame, is_dashboard=False):
        """Displays Gym Name and Address in Bold at the top right of each tab page header."""
        gym_name = self.settings.get("gym_name", "GYM PRO+")
        gym_address = self.settings.get("gym_address", "")
        
        if is_dashboard:
            brand_frame = tk.Frame(header_frame, bg=header_frame.cget("bg"))
            brand_frame.pack(side="right", padx=(0, 25))
            
            lbl_name = tk.Label(brand_frame, text=gym_name.upper(), font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=header_frame.cget("bg"))
            lbl_name.pack(anchor="e")
            
            if gym_address:
                lbl_addr = tk.Label(brand_frame, text=gym_address, font=("Segoe UI", 10, "bold"), fg=TEXT_MUTED, bg=header_frame.cget("bg"))
                lbl_addr.pack(anchor="e")
        else:
            branding_txt = f"🏢 {gym_name} ({gym_address})" if gym_address else f"🏢 {gym_name}"
            lbl = tk.Label(header_frame, text=branding_txt, font=("Segoe UI", 10, "bold"), fg=ACCENT, bg=header_frame.cget("bg"))
            lbl.pack(side="right", padx=(0, 25))

    # --- VIEW: DASHBOARD (Date Range Filtered & Light Theme) ---
    def show_dashboard(self):
        self.clear_content("📊 Dashboard")
        
        # View Header
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        
        tk.Label(header, text="Operational Dashboard", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        self.add_gym_branding_header(header, is_dashboard=True)
        
        # Dashboard Date Range Filter Panel (Requirement 4)
        date_filter_panel = tk.Frame(self.content_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=10)
        date_filter_panel.pack(fill="x", padx=25, pady=5)
        
        tk.Label(date_filter_panel, text="🗓️ Report Period Filter:", font=("Segoe UI", 10, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(side="left", padx=(0, 15))
        
        tk.Label(date_filter_panel, text="From Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left")
        self.ent_dash_start = tk.Entry(date_filter_panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_dash_start.pack(side="left", padx=5, ipady=2)
        self.ent_dash_start.insert(0, db_to_ui_date(self.dash_start_date))
        
        tk.Label(date_filter_panel, text="To Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left", padx=(10, 0))
        self.ent_dash_end = tk.Entry(date_filter_panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_dash_end.pack(side="left", padx=5, ipady=2)
        self.ent_dash_end.insert(0, db_to_ui_date(self.dash_end_date))
        
        btn_apply = tk.Button(date_filter_panel, text="🔍 Apply Filter", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=12, pady=4, cursor="hand2", command=self.apply_dashboard_date_filter)
        btn_apply.pack(side="left", padx=15)
        
        # Scrollable stats frame
        scroll_container = tk.Frame(self.content_frame, bg=BG_PRIMARY)
        scroll_container.pack(fill="both", expand=True, padx=25, pady=(5, 20))
        
        # Load stats based on dates
        m_df = load_dataframe("members.xlsx")
        t_df = load_dataframe("trainers.xlsx")
        v_df = load_dataframe("visitors.xlsx")
        pay_df = load_dataframe("payments.xlsx")
        att_df = load_dataframe("attendance.xlsx")
        
        # Compute Stats in Date Range
        start_d = self.dash_start_date
        end_d = self.dash_end_date
        start_dt = pd.to_datetime(start_d, errors="coerce")
        end_dt = pd.to_datetime(end_d, errors="coerce")
        
        total_members = len(m_df)
        active_members = len(m_df[m_df["Status"] == "Active"])
        active_coaches = len(t_df[t_df["Status"] == "Active"])
        
        # Checkins in Period
        checkins_in_period = 0
        if not att_df.empty:
            try:
                att_df["Date_Parsed"] = pd.to_datetime(att_df["Date"], errors="coerce")
                ci_filtered = att_df[(att_df["Date_Parsed"] >= start_dt) & (att_df["Date_Parsed"] <= end_dt) & (att_df["Check-In Time"].astype(str).str.strip() != "")]
                checkins_in_period = len(ci_filtered)
            except Exception as e:
                print(f"Error parse att date: {e}")
                
        # Income in Period
        income_in_period = 0.0
        if not pay_df.empty:
            try:
                pay_df["Date_Parsed"] = pd.to_datetime(pay_df["Payment Date"], errors="coerce")
                pay_filtered = pay_df[(pay_df["Date_Parsed"] >= start_dt) & (pay_df["Date_Parsed"] <= end_dt)]
                income_in_period = pay_filtered["Amount Paid"].sum()
            except Exception as e:
                print(f"Error parse pay date: {e}")
                
        # Visitors in Period
        visitors_in_period = 0
        if not v_df.empty:
            try:
                v_df["Date_Parsed"] = pd.to_datetime(v_df["Visit Date"], errors="coerce")
                v_filtered = v_df[(v_df["Date_Parsed"] >= start_dt) & (v_df["Date_Parsed"] <= end_dt)]
                visitors_in_period = len(v_filtered)
            except Exception as e:
                print(f"Error parse visitor date: {e}")
                
        # Cards Layout Grid
        cards_frame = tk.Frame(scroll_container, bg=BG_PRIMARY)
        cards_frame.pack(fill="x", pady=10)
        
        cards_data = [
            ("Total Active Members", f"{active_members} / {total_members}", "👥", ACCENT, self.show_members),
            ("Check-ins in Period", str(checkins_in_period), "📅", SUCCESS, self.show_attendance),
            ("Active Coaches", str(active_coaches), "🤝", ACCENT_HOVER, self.show_trainers)
        ]
        
        if self.current_user["role"] == "Admin":
            cards_data.append(("Income in Period", f"{self.settings.get('currency', 'Rs.')}{income_in_period:,.2f}", "💳", "#D97706", self.open_income_details_modal))
        else:
            cards_data.append(("Visitors in Period", str(visitors_in_period), "🚶", "#D97706", self.show_attendance))
            
        for i, (title, val, icon, color, dbl_click_cmd) in enumerate(cards_data):
            card = tk.Frame(cards_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=18)
            card.grid(row=0, column=i, sticky="nsew", padx=8)
            cards_frame.columnconfigure(i, weight=1)
            
            card.bind("<Enter>", lambda e, c=card: c.config(bg="#F3F4F6"))
            card.bind("<Leave>", lambda e, c=card: c.config(bg=BG_SECONDARY))
            card.bind("<Double-Button-1>", lambda e, cmd=dbl_click_cmd: cmd())
            
            lbl_icon = tk.Label(card, text=icon, font=("Segoe UI", 24), fg=color, bg=BG_SECONDARY)
            lbl_icon.pack(anchor="w")
            lbl_icon.bind("<Double-Button-1>", lambda e, cmd=dbl_click_cmd: cmd())
            
            lbl_title = tk.Label(card, text=title, font=("Segoe UI", 10, "bold"), fg=TEXT_MUTED, bg=BG_SECONDARY)
            lbl_title.pack(anchor="w", pady=(8, 0))
            lbl_title.bind("<Double-Button-1>", lambda e, cmd=dbl_click_cmd: cmd())
            
            lbl_val = tk.Label(card, text=val, font=("Segoe UI", 18, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY)
            lbl_val.pack(anchor="w", pady=(2, 0))
            lbl_val.bind("<Double-Button-1>", lambda e, cmd=dbl_click_cmd: cmd())
            
        # Lower Split Area
        lower_frame = tk.Frame(scroll_container, bg=BG_PRIMARY)
        lower_frame.pack(fill="both", expand=True, pady=15)
        
        # 1. Reminders
        reminders_frame = tk.Frame(lower_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=15)
        reminders_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(reminders_frame, text="🔔 Expiry & Renewal Reminders", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
        
        rem_list = get_reminders(days_threshold=7)
        if rem_list:
            tree = ttk.Treeview(reminders_frame, columns=("ID", "Name", "Expiry", "Days"), show="headings", height=8)
            tree.heading("ID", text="ID")
            tree.heading("Name", text="Member Name")
            tree.heading("Expiry", text="Expiry Date")
            tree.heading("Days", text="Days Left")
            
            tree.column("ID", width=70, anchor="center")
            tree.column("Name", width=120)
            tree.column("Expiry", width=90, anchor="center")
            tree.column("Days", width=90, anchor="center")
            
            # Configure Row Tag Colors (Requirement 1)
            tree.tag_configure("overdue", foreground="red")
            tree.tag_configure("warning", foreground="#D97706") # Dark gold/yellow
            
            tree.pack(fill="both", expand=True)
            
            for r in rem_list:
                days = r["Days Remaining"]
                if days < 0:
                    days_label = f"{abs(days)}d Overdue"
                    tag = "overdue"
                elif days == 0:
                    days_label = "Today"
                    tag = "overdue"
                else:
                    days_label = f"{days}d left"
                    tag = "warning"
                    
                tree.insert("", "end", values=(r["Member ID"], r["Name"], db_to_ui_date(r["Expiry Date"]), days_label), tags=(tag,))
            tree.bind("<Double-Button-1>", lambda e: self.on_reminder_double_click(tree))
        else:
            tk.Label(reminders_frame, text="No memberships expiring or overdue.", font=("Segoe UI", 10, "italic"), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(expand=True)
            
        # 2. Charts / Analytics
        right_panel = tk.Frame(lower_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=15)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        if self.current_user["role"] == "Admin":
            tk.Label(right_panel, text="📈 Monthly Revenue Chart", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
            chart_canvas = tk.Canvas(right_panel, bg=BG_SECONDARY, highlightthickness=0)
            chart_canvas.pack(fill="both", expand=True)
            self.draw_revenue_chart(chart_canvas)
        else:
            tk.Label(right_panel, text="🚶 Guest Logs Summary", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
            v_list = get_visitors_list()
            if v_list:
                v_tree = ttk.Treeview(right_panel, columns=("ID", "Name", "Contact", "Plan"), show="headings", height=8)
                v_tree.heading("ID", text="ID")
                v_tree.heading("Name", text="Visitor Name")
                v_tree.heading("Contact", text="Contact No")
                v_tree.heading("Plan", text="Interest Plan")
                
                v_tree.column("ID", width=70, anchor="center")
                v_tree.column("Name", width=110)
                v_tree.column("Contact", width=100, anchor="center")
                v_tree.column("Plan", width=120)
                v_tree.pack(fill="both", expand=True)
                
                for v in v_list[-6:]:
                    v_tree.insert("", "end", values=(v["Visitor ID"], v["Name"], v["Contact"], v["Plan to Join"]))
            else:
                tk.Label(right_panel, text="No visitor entries logged yet.", font=("Segoe UI", 10, "italic"), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(expand=True)
                
    def apply_dashboard_date_filter(self):
        start = self.ent_dash_start.get().strip()
        end = self.ent_dash_end.get().strip()
        
        start_db = ui_to_db_date(start)
        end_db = ui_to_db_date(end)
        
        try:
            datetime.strptime(start_db, "%Y-%m-%d")
            datetime.strptime(end_db, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid Date format. Use DD-MM-YYYY.")
            return
            
        self.dash_start_date = start_db
        self.dash_end_date = end_db
        self.show_dashboard()
        
    def open_income_details_modal(self):
        TotalIncomeDetailsModal(self, self.dash_start_date, self.dash_end_date)
        
    def on_reminder_double_click(self, tree):
        selected = tree.selection()
        if not selected: return
        m_id = tree.item(selected[0])["values"][0]
        if self.current_user["role"] == "Admin":
            self.show_payments()
            self.load_billing_for_member(m_id)
        else:
            messagebox.showinfo("Renewal Alert", f"Member {m_id} requires renewal. Notify Admin.")

    def draw_revenue_chart(self, canvas):
        canvas.update()
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1: width = 300
        if height <= 1: height = 180
            
        summary = get_financial_summary()
        if not summary:
            canvas.create_text(width/2, height/2, text="No billing transactions recorded yet.", fill=TEXT_MUTED, font=("Segoe UI", 10, "italic"))
            return
            
        sorted_months = sorted(summary.keys())
        if len(sorted_months) > 6:
            sorted_months = sorted_months[-6:]
            
        vals = [summary[m] for m in sorted_months]
        max_val = max(vals) if vals else 1.0
        if max_val == 0: max_val = 1.0
            
        padding_left = 50
        padding_bottom = 30
        padding_top = 20
        padding_right = 20
        
        chart_w = width - padding_left - padding_right
        chart_h = height - padding_top - padding_bottom
        
        for i in range(4):
            y = padding_top + chart_h * (i / 3)
            val = max_val * (1 - i / 3)
            canvas.create_line(padding_left, y, width - padding_right, y, fill=CARD_BORDER, width=1)
            canvas.create_text(padding_left - 8, y, text=f"{val:.0f}", fill=TEXT_MUTED, anchor="e", font=("Segoe UI", 8))
            
        bar_count = len(sorted_months)
        bar_spacing = chart_w / bar_count
        bar_width = bar_spacing * 0.65
        
        for idx, month in enumerate(sorted_months):
            val = summary[month]
            bar_h = (val / max_val) * chart_h
            
            x1 = padding_left + idx * bar_spacing + (bar_spacing - bar_width)/2
            y1 = height - padding_bottom - bar_h
            x2 = x1 + bar_width
            y2 = height - padding_bottom
            
            canvas.create_rectangle(x1, y1, x2, y2, fill=ACCENT, outline="", width=0)
            canvas.create_text((x1+x2)/2, y1 - 8, text=f"{val:.0f}", fill=TEXT_MAIN, font=("Segoe UI", 8, "bold"))
            
            try:
                dt = datetime.strptime(month, "%Y-%m")
                label = dt.strftime("%b")
            except:
                label = month
            canvas.create_text((x1+x2)/2, height - padding_bottom + 12, text=label, fill=TEXT_MUTED, font=("Segoe UI", 9))

    # --- VIEW: MEMBERS DIRECTORY (Requirement 5: Shows all members enrolled) ---
    def show_members(self):
        self.clear_content("👥 Members")
        
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        
        tk.Label(header, text="Members Directory", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        
        # Right Actions
        btn_frame = tk.Frame(header, bg=BG_PRIMARY)
        btn_frame.pack(side="right")
        self.add_gym_branding_header(header)
        
        btn_add = tk.Button(btn_frame, text="+ Enroll Member", font=("Segoe UI", 10, "bold"), fg=BG_SECONDARY, bg=ACCENT,
                            activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, padx=15, pady=6,
                            cursor="hand2", command=self.open_add_member_modal)
        btn_add.pack(side="right", padx=5)
        
        # Search Entry
        search_frame = tk.Frame(self.content_frame, bg=BG_PRIMARY, padx=25, pady=5)
        search_frame.pack(fill="x")
        
        tk.Label(search_frame, text="Search Member Name/ID:", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 10)).pack(side="left", padx=(0, 5))
        self.ent_search_member = tk.Entry(search_frame, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10), width=30)
        self.ent_search_member.pack(side="left", padx=5, ipady=4)
        self.ent_search_member.bind("<KeyRelease>", self.filter_members)
        
        # Data grid (Treeview)
        table_frame = tk.Frame(self.content_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=25, pady=10)
        
        self.member_tree = ttk.Treeview(table_frame, columns=("ID", "Name", "Contact", "Plan", "Joined", "Expiry", "Trainer", "Status"), show="headings")
        self.member_tree.heading("ID", text="ID")
        self.member_tree.heading("Name", text="Name")
        self.member_tree.heading("Contact", text="Contact No")
        self.member_tree.heading("Plan", text="Membership Plan")
        self.member_tree.heading("Joined", text="Date of Admission")
        self.member_tree.heading("Expiry", text="Expiry Date")
        self.member_tree.heading("Trainer", text="Coach / Trainer")
        self.member_tree.heading("Status", text="Status")
        
        self.member_tree.column("ID", width=80, anchor="center")
        self.member_tree.column("Name", width=140)
        self.member_tree.column("Contact", width=110, anchor="center")
        self.member_tree.column("Plan", width=110, anchor="center")
        self.member_tree.column("Joined", width=120, anchor="center")
        self.member_tree.column("Expiry", width=100, anchor="center")
        self.member_tree.column("Trainer", width=130)
        self.member_tree.column("Status", width=90, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.member_tree.yview)
        self.member_tree.configure(yscrollcommand=scrollbar.set)
        
        self.member_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Double Click Action (Requirement 4)
        self.member_tree.bind("<Double-Button-1>", lambda e: self.edit_selected_member())
        
        # Operations footer
        footer_frame = tk.Frame(self.content_frame, bg=BG_PRIMARY, padx=25, pady=15)
        footer_frame.pack(fill="x")
        
        ops = [
            ("Edit Member Info", self.edit_selected_member, BG_SECONDARY, TEXT_MAIN),
            ("Delete Record", self.delete_selected_member, ALERT, BG_SECONDARY),
            ("Workout/Diet Programs", self.assign_plans_selected_member, BG_SECONDARY, TEXT_MAIN),
            ("Fitness & BMI Tracking", self.track_progress_selected_member, ACCENT, BG_SECONDARY)
        ]
        if self.current_user["role"] == "Admin":
            ops.insert(2, ("Record Payment", self.bill_selected_member, BG_SECONDARY, TEXT_MAIN))
            
        for text, cmd, bg, fg in ops:
            btn = tk.Button(footer_frame, text=text, font=("Segoe UI", 9, "bold"), bg=bg, fg=fg, bd=1, highlightbackground=CARD_BORDER, padx=12, pady=6, cursor="hand2", command=cmd)
            btn.pack(side="left", padx=4)
            
        # Clear search box and load members (Requirement 1 - clears filter on load)
        self.ent_search_member.delete(0, tk.END)
        self.load_members_table()
        
    def load_members_table(self):
        for item in self.member_tree.get_children():
            self.member_tree.delete(item)
            
        df = load_dataframe("members.xlsx")
        if df.empty: return
            
        for _, row in df.iterrows():
            trainer_info = "None"
            if row.get("Trainer Required") == "Yes":
                trainer_info = f"{row.get('Trainer Name', 'Coach')} ({row.get('Trainer ID', '')})"
            self.member_tree.insert("", "end", values=(
                row["Member ID"], row["Name"], row["Contact"], row["Plan Type"],
                db_to_ui_date(row.get("Date Added", "")), db_to_ui_date(row["Expiry Date"]),
                trainer_info, row["Status"]
            ))
            
    def filter_members(self, event=None):
        query = self.ent_search_member.get().lower()
        for item in self.member_tree.get_children():
            self.member_tree.delete(item)
        df = load_dataframe("members.xlsx")
        if df.empty: return
        for _, row in df.iterrows():
            if query in str(row["Name"]).lower() or query in str(row["Member ID"]).lower() or query in str(row["Contact"]).lower():
                trainer_info = "None"
                if row.get("Trainer Required") == "Yes":
                    trainer_info = f"{row.get('Trainer Name', 'Coach')} ({row.get('Trainer ID', '')})"
                self.member_tree.insert("", "end", values=(
                    row["Member ID"], row["Name"], row["Contact"], row["Plan Type"],
                    db_to_ui_date(row.get("Date Added", "")), db_to_ui_date(row["Expiry Date"]),
                    trainer_info, row["Status"]
                ))
                
    def get_selected_member_id(self):
        selected = self.member_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a member from the table first.")
            return None
        return self.member_tree.item(selected[0])["values"][0]

    def open_add_member_modal(self):
        MemberFormModal(self, mode="add")

    def edit_selected_member(self):
        m_id = self.get_selected_member_id()
        if m_id:
            MemberFormModal(self, mode="edit", member_id=m_id)
            
    def delete_selected_member(self):
        m_id = self.get_selected_member_id()
        if not m_id: return
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete member {m_id}?")
        if confirm:
            if delete_member(m_id):
                messagebox.showinfo("Deleted", f"Member {m_id} removed.")
                self.load_members_table()
            else:
                messagebox.showerror("Error", "Could not delete member.")
                
    def bill_selected_member(self):
        m_id = self.get_selected_member_id()
        if m_id:
            self.show_payments()
            self.load_billing_for_member(m_id)
            
    def assign_plans_selected_member(self):
        m_id = self.get_selected_member_id()
        if m_id:
            AssignPlanModal(self, member_id=m_id)
            
    def track_progress_selected_member(self):
        m_id = self.get_selected_member_id()
        if m_id:
            FitnessTrackerModal(self, member_id=m_id)

    # --- VIEW: TRAINERS DIRECTORY ---
    def show_trainers(self):
        self.clear_content("🤝 Trainers")
        
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        
        tk.Label(header, text="Coaches & Trainers", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        
        if self.current_user["role"] == "Admin":
            btn_frame = tk.Frame(header, bg=BG_PRIMARY)
            btn_frame.pack(side="right")
            
            btn_add = tk.Button(btn_frame, text="+ Add Coach", font=("Segoe UI", 10, "bold"), fg=BG_SECONDARY, bg=ACCENT,
                                activebackground=ACCENT_HOVER, activeforeground=BG_SECONDARY, bd=0, padx=15, pady=6,
                                cursor="hand2", command=self.open_add_trainer_modal)
            btn_add.pack(side="right", padx=5)
            
            btn_realloc = tk.Button(btn_frame, text="🔄 Transfer Trainees", font=("Segoe UI", 10, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY,
                                activebackground=BG_PRIMARY, activeforeground=ACCENT, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=5,
                                cursor="hand2", command=self.open_reallocation_modal)
            btn_realloc.pack(side="right", padx=5)
            
        self.add_gym_branding_header(header)
        table_frame = tk.Frame(self.content_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=25, pady=10)
        
        self.trainer_tree = ttk.Treeview(table_frame, columns=("ID", "Name", "Contact", "Specialty", "Fees", "Status"), show="headings")
        self.trainer_tree.heading("ID", text="Trainer ID")
        self.trainer_tree.heading("Name", text="Trainer Name")
        self.trainer_tree.heading("Contact", text="Contact No")
        self.trainer_tree.heading("Specialty", text="Specialty")
        self.trainer_tree.heading("Fees", text="Monthly Fees")
        self.trainer_tree.heading("Status", text="Status")
        
        self.trainer_tree.column("ID", width=100, anchor="center")
        self.trainer_tree.column("Name", width=180)
        self.trainer_tree.column("Contact", width=130, anchor="center")
        self.trainer_tree.column("Specialty", width=160)
        self.trainer_tree.column("Fees", width=110, anchor="center")
        self.trainer_tree.column("Status", width=90, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.trainer_tree.yview)
        self.trainer_tree.configure(yscrollcommand=scrollbar.set)
        
        self.trainer_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.trainer_tree.bind("<Double-Button-1>", lambda e: self.edit_selected_trainer())
        
        footer_frame = tk.Frame(self.content_frame, bg=BG_PRIMARY, padx=25, pady=15)
        footer_frame.pack(fill="x")
        
        if self.current_user["role"] == "Admin":
            btn_edit = tk.Button(footer_frame, text="Edit Coach Info", font=("Segoe UI", 9, "bold"), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=6, cursor="hand2", command=self.edit_selected_trainer)
            btn_edit.pack(side="left", padx=5)
            
            btn_del = tk.Button(footer_frame, text="Remove Coach", font=("Segoe UI", 9, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, padx=15, pady=6, cursor="hand2", command=self.delete_selected_trainer)
            btn_del.pack(side="left", padx=5)
            
        btn_assigned = tk.Button(footer_frame, text="View Assigned Trainees", font=("Segoe UI", 9, "bold"), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=6, cursor="hand2", command=self.view_assigned_trainees)
        btn_assigned.pack(side="left", padx=5)
        
        self.load_trainers_table()
        
    def load_trainers_table(self):
        for item in self.trainer_tree.get_children():
            self.trainer_tree.delete(item)
        df = load_dataframe("trainers.xlsx")
        if df.empty: return
        for _, row in df.iterrows():
            self.trainer_tree.insert("", "end", values=(
                row["Trainer ID"], row["Name"], row["Contact"], row["Specialty"],
                f"{self.settings.get('currency', 'Rs.')}{float(row['Base Fees']):,.2f}", row["Status"]
            ))
            
    def get_selected_trainer_id(self):
        selected = self.trainer_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a coach first.")
            return None
        return self.trainer_tree.item(selected[0])["values"][0]

    def open_add_trainer_modal(self):
        TrainerFormModal(self, mode="add")

    def edit_selected_trainer(self):
        if self.current_user["role"] != "Admin": return
        t_id = self.get_selected_trainer_id()
        if t_id:
            TrainerFormModal(self, mode="edit", trainer_id=t_id)
            
    def delete_selected_trainer(self):
        t_id = self.get_selected_trainer_id()
        if not t_id: return
        confirm = messagebox.askyesno("Confirm Remove", f"Remove coach {t_id}?")
        if confirm:
            if delete_trainer(t_id):
                messagebox.showinfo("Removed", "Trainer removed.")
                self.load_trainers_table()
                
    def open_reallocation_modal(self):
        ReallocateTrainerModal(self)
        
    def view_assigned_trainees(self):
        t_id = self.get_selected_trainer_id()
        if not t_id: return
        trainees = get_trainer_members(t_id)
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Trainees - Coach {t_id}")
        dialog.geometry("500x350")
        dialog.configure(bg=BG_PRIMARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Assigned Trainees ({len(trainees)})", font=("Segoe UI", 12, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY, pady=10).pack()
        t_frame = tk.Frame(dialog, bg=BG_SECONDARY)
        t_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(t_frame, columns=("ID", "Name", "Contact", "Status"), show="headings")
        tree.heading("ID", text="ID")
        tree.heading("Name", text="Name")
        tree.heading("Contact", text="Contact")
        tree.heading("Status", text="Status")
        tree.column("ID", width=70, anchor="center")
        tree.column("Status", width=80, anchor="center")
        tree.pack(fill="both", expand=True)
        
        for tr in trainees:
            tree.insert("", "end", values=(tr["Member ID"], tr["Name"], tr["Contact"], tr["Status"]))
        tk.Button(dialog, text="Close", bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=5, command=dialog.destroy).pack(pady=10)

    # --- VIEW: ATTENDANCE (Requirement 6: Check-in/out and historical queries with Date Filters) ---
    def show_attendance(self):
        self.clear_content("📅 Attendance")
        
        # View Header
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        tk.Label(header, text="Gate Attendance Registry", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        self.add_gym_branding_header(header)
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=25, pady=(5, 15))
        
        # Sub-tab 1: Daily Checkin/out Console
        ci_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(ci_tab, text="🔑 Gate Check-In & Check-Out")
        
        split_frame = tk.Frame(ci_tab, bg=BG_PRIMARY)
        split_frame.pack(fill="both", expand=True, pady=10)
        
        # Left Panel (Gate controls)
        left_panel = tk.Frame(split_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Right Panel (Today's logs)
        right_panel = tk.Frame(split_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=20)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Autocomplete search checkin
        tk.Label(left_panel, text="Gate Console (Check-In & Check-Out)", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
        tk.Label(left_panel, text="Search Member ID or Name:", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9)).pack(anchor="w")
        
        self.suggest_wrapper = tk.Frame(left_panel, bg=BG_SECONDARY)
        self.suggest_wrapper.pack(fill="x", pady=10)
        
        self.ent_checkin_suggest = tk.Entry(self.suggest_wrapper, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 12), bd=1, highlightbackground=CARD_BORDER)
        self.ent_checkin_suggest.pack(fill="x", ipady=8)
        self.ent_checkin_suggest.bind("<KeyRelease>", self.on_checkin_typing)
        
        # Suggestions list box
        self.checkin_listbox = tk.Listbox(left_panel, bg=BG_PRIMARY, fg=TEXT_MAIN, selectbackground=ACCENT, selectforeground=BG_SECONDARY, font=("Segoe UI", 10), height=5, bd=1, highlightbackground=CARD_BORDER)
        self.checkin_listbox.pack(fill="x", pady=(0, 10))
        
        # Manual adjustment panel (Requirements 2 & 3)
        adj_box = tk.LabelFrame(left_panel, text="🗓️ Manual Date & Time Override", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG_SECONDARY, bd=1, highlightbackground=CARD_BORDER, padx=10, pady=10)
        adj_box.pack(fill="x", pady=(0, 15))
        adj_box.columnconfigure(0, weight=1)
        adj_box.columnconfigure(1, weight=1)
        
        # Date & Time for Check-In
        tk.Label(adj_box, text="Check-In Date (DD-MM-YYYY):", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.ent_ci_date = tk.Entry(adj_box, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_ci_date.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self.ent_ci_date.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 10))
        
        tk.Label(adj_box, text="Check-In Time (HH:MM):", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.ent_ci_time = tk.Entry(adj_box, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_ci_time.insert(0, datetime.now().strftime("%H:%M"))
        self.ent_ci_time.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 10))
        
        # Time for Check-Out
        tk.Label(adj_box, text="Check-Out Time (HH:MM):", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.ent_co_time = tk.Entry(adj_box, bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_co_time.insert(0, datetime.now().strftime("%H:%M"))
        self.ent_co_time.grid(row=3, column=0, sticky="ew", padx=(0, 5))
        
        # Check-in and Check-out buttons
        btn_box = tk.Frame(left_panel, bg=BG_SECONDARY)
        btn_box.pack(fill="x", pady=5)
        
        btn_ci = tk.Button(btn_box, text="🔑 Check-In Member", font=("Segoe UI", 10, "bold"), bg=SUCCESS, fg=BG_SECONDARY, bd=0, padx=10, pady=10, cursor="hand2", command=lambda: self.on_gate_action("Check-In"))
        btn_ci.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_co = tk.Button(btn_box, text="🚪 Check-Out Member", font=("Segoe UI", 10, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, padx=10, pady=10, cursor="hand2", command=lambda: self.on_gate_action("Check-Out"))
        btn_co.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # today's listbox logs
        self.att_tree = ttk.Treeview(right_panel, columns=("ID", "MemberID", "Name", "CheckInTime", "CheckOutTime"), show="headings")
        self.att_tree.heading("ID", text="Record ID")
        self.att_tree.heading("MemberID", text="Member ID")
        self.att_tree.heading("Name", text="Name")
        self.att_tree.heading("CheckInTime", text="Check-In Time")
        self.att_tree.heading("CheckOutTime", text="Check-Out Time")
        self.att_tree.column("ID", width=80, anchor="center")
        self.att_tree.column("MemberID", width=90, anchor="center")
        self.att_tree.column("CheckInTime", width=110, anchor="center")
        self.att_tree.column("CheckOutTime", width=110, anchor="center")
        self.att_tree.pack(fill="both", expand=True)
        
        # Remove Selected Record button (Requirement: gate record deletion)
        btn_remove_att = tk.Button(right_panel, text="❌ Remove Selected Record", font=("Segoe UI", 10, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, pady=8, cursor="hand2", command=self.remove_selected_attendance_record)
        btn_remove_att.pack(fill="x", pady=(10, 0))
        
        self.load_today_attendance()
        
        # Sub-tab 2: Historical logs with range queries (Requirement 6)
        hist_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(hist_tab, text="📅 Historical Logs & Queries")
        
        hist_panel = tk.Frame(hist_tab, bg=BG_PRIMARY, pady=10)
        hist_panel.pack(fill="both", expand=True)
        
        # Filters row
        hist_filter = tk.Frame(hist_panel, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=10)
        hist_filter.pack(fill="x", padx=10, pady=5)
        
        tk.Label(hist_filter, text="Start Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left")
        self.ent_hist_start = tk.Entry(hist_filter, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_hist_start.pack(side="left", padx=5, ipady=2)
        self.ent_hist_start.insert(0, db_to_ui_date(self.dash_start_date))
        
        tk.Label(hist_filter, text="End Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left", padx=(10, 0))
        self.ent_hist_end = tk.Entry(hist_filter, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_hist_end.pack(side="left", padx=5, ipady=2)
        self.ent_hist_end.insert(0, db_to_ui_date(self.dash_end_date))
        
        btn_hist_query = tk.Button(hist_filter, text="🔍 Query Logs", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=12, pady=4, cursor="hand2", command=self.query_attendance_logs)
        btn_hist_query.pack(side="left", padx=15)
        
        # Query results grid
        q_frame = tk.Frame(hist_panel, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1)
        q_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.q_tree = ttk.Treeview(q_frame, columns=("ID", "MemberID", "Name", "Date", "CheckInTime", "CheckOutTime"), show="headings")
        self.q_tree.heading("ID", text="Record ID")
        self.q_tree.heading("MemberID", text="Member ID")
        self.q_tree.heading("Name", text="Name")
        self.q_tree.heading("Date", text="Event Date")
        self.q_tree.heading("CheckInTime", text="Check-In Time")
        self.q_tree.heading("CheckOutTime", text="Check-Out Time")
        self.q_tree.column("ID", width=80, anchor="center")
        self.q_tree.column("MemberID", width=90, anchor="center")
        self.q_tree.column("Date", width=95, anchor="center")
        self.q_tree.column("CheckInTime", width=110, anchor="center")
        self.q_tree.column("CheckOutTime", width=110, anchor="center")
        self.q_tree.pack(fill="both", expand=True)
        
        # Sub-tab 3: Guest Logs
        vis_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(vis_tab, text="🚶 Guest & Visitor Passes")
        
        v_split = tk.Frame(vis_tab, bg=BG_PRIMARY, pady=10)
        v_split.pack(fill="both", expand=True)
        
        v_left = tk.Frame(v_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        v_left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        v_right = tk.Frame(v_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=20)
        v_right.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        tk.Label(v_left, text="New Visitor Registration", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 15))
        
        v_fields = [
            ("Visitor Full Name:", "ent_v_name"),
            ("Contact Number:", "ent_v_contact")
        ]
        self.visitor_form = {}
        for lbl, var in v_fields:
            tk.Label(v_left, text=lbl, fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w", pady=(5, 2))
            ent = tk.Entry(v_left, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
            ent.pack(fill="x", ipady=4)
            self.visitor_form[var] = ent
            
        tk.Label(v_left, text="Plan Intent to Join (Target):", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w", pady=(5, 2))
        self.cb_v_plan = ttk.Combobox(v_left, values=["Cardio Fitness", "Weight Loss / Cut", "Strength / Bulk", "Yoga & Flexibility", "General Weight training"], state="readonly")
        self.cb_v_plan.pack(fill="x", pady=2)
        self.cb_v_plan.set("Cardio Fitness")
        
        tk.Label(v_left, text="Notes / Remarks:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w", pady=(5, 2))
        self.ent_v_notes = tk.Entry(v_left, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_v_notes.pack(fill="x", ipady=4, pady=(0, 15))
        
        btn_v_save = tk.Button(v_left, text="🎫 Generate Visitor Prospect Pass", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=8, command=self.save_visitor_prospect)
        btn_v_save.pack(fill="x")
        
        self.v_tree = ttk.Treeview(v_right, columns=("ID", "Name", "Contact", "Plan", "Date"), show="headings")
        self.v_tree.heading("ID", text="Guest ID")
        self.v_tree.heading("Name", text="Visitor Name")
        self.v_tree.heading("Contact", text="Contact No")
        self.v_tree.heading("Plan", text="Interest Plan")
        self.v_tree.heading("Date", text="Visit Date")
        self.v_tree.column("ID", width=80, anchor="center")
        self.v_tree.column("Contact", width=100, anchor="center")
        self.v_tree.column("Date", width=95, anchor="center")
        self.v_tree.pack(fill="both", expand=True)
        
        self.load_visitors_table()
        self.query_attendance_logs()
        
    def on_checkin_typing(self, event=None):
        query = self.ent_checkin_suggest.get().strip().lower()
        self.checkin_listbox.delete(0, tk.END)
        if not query: return
        
        m_df = load_dataframe("members.xlsx")
        if m_df.empty: return
        
        matches = []
        for _, r in m_df.iterrows():
            if query in str(r["Name"]).lower() or query in str(r["Member ID"]).lower():
                matches.append(f"[{r['Member ID']}] {r['Name']} ({r['Status']})")
                
        for m in matches[:10]:
            self.checkin_listbox.insert(tk.END, m)
            
    def on_gate_action(self, event_type):
        if event_type == "Check-Out":
            selected_tree = self.att_tree.selection()
            if selected_tree:
                att_id = self.att_tree.item(selected_tree[0])["values"][0]
                co_time = self.ent_co_time.get().strip()
                try:
                    datetime.strptime(co_time, "%H:%M")
                except ValueError:
                    messagebox.showerror("Error", "Invalid Check-Out time format. Use HH:MM (e.g. 17:30).")
                    return
                success, msg = check_out_member_by_record_id(att_id, custom_time=co_time)
                if success:
                    messagebox.showinfo("Gate Entry Recorded", msg)
                    self.load_today_attendance()
                    self.query_attendance_logs()
                else:
                    messagebox.showerror("Gate Action Denied", msg)
                return

        # Fallback to search listbox lookup
        selection = self.checkin_listbox.curselection()
        if not selection:
            raw_text = self.ent_checkin_suggest.get().strip()
            if "[" in raw_text and "]" in raw_text:
                m_id = raw_text.split("]")[0].replace("[", "").strip()
            else:
                m_id = raw_text.upper()
        else:
            selected_text = self.checkin_listbox.get(selection[0])
            m_id = selected_text.split("]")[0].replace("[", "").strip()
            
        if not m_id:
            messagebox.showerror("Error", "Please search and select a member first, or select a record from the today's log list.")
            return
            
        if event_type == "Check-In":
            ci_date = ui_to_db_date(self.ent_ci_date.get().strip())
            ci_time = self.ent_ci_time.get().strip()
            try:
                datetime.strptime(ci_date, "%Y-%m-%d")
                datetime.strptime(ci_time, "%H:%M")
            except ValueError:
                messagebox.showerror("Error", "Invalid Check-In Date or Time format. Use Date: DD-MM-YYYY, Time: HH:MM.")
                return
            success, msg = check_in_member(m_id, custom_date=ci_date, custom_time=ci_time)
        else:
            co_time = self.ent_co_time.get().strip()
            try:
                datetime.strptime(co_time, "%H:%M")
            except ValueError:
                messagebox.showerror("Error", "Invalid Check-Out time format. Use HH:MM (e.g. 17:30).")
                return
            success, msg = check_out_member(m_id, custom_time=co_time)
            
        if success:
            messagebox.showinfo("Gate Entry Recorded", msg)
            self.ent_checkin_suggest.delete(0, tk.END)
            self.checkin_listbox.delete(0, tk.END)
            self.load_today_attendance()
            self.query_attendance_logs()
        else:
            messagebox.showerror("Gate Action Denied", msg)
            
    def load_today_attendance(self):
        for item in self.att_tree.get_children():
            self.att_tree.delete(item)
        for c in get_today_checkins():
            self.att_tree.insert("", "end", values=(
                c["Attendance ID"], c.get("Member ID", ""), c.get("Name", ""), 
                c.get("Check-In Time", ""), c.get("Check-Out Time", "")
            ))
            
    def remove_selected_attendance_record(self):
        selected = self.att_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select an attendance record from the list to remove.")
            return
            
        record_values = self.att_tree.item(selected[0])["values"]
        att_id = record_values[0]
        member_name = record_values[2]
        
        confirm = messagebox.askyesno("Confirm Removal", f"Are you sure you want to delete attendance record {att_id} for {member_name}?")
        if confirm:
            success, msg = delete_attendance_record(att_id)
            if success:
                messagebox.showinfo("Success", msg)
                self.load_today_attendance()
                self.query_attendance_logs()
            else:
                messagebox.showerror("Error", msg)
            
    def query_attendance_logs(self):
        start = ui_to_db_date(self.ent_hist_start.get().strip())
        end = ui_to_db_date(self.ent_hist_end.get().strip())
        for item in self.q_tree.get_children():
            self.q_tree.delete(item)
        events = get_events_by_date_range(start, end)
        for e in events:
            self.q_tree.insert("", "end", values=(
                e["Attendance ID"], e.get("Member ID", ""), e.get("Name", ""), 
                db_to_ui_date(e.get("Date", "")), e.get("Check-In Time", ""), e.get("Check-Out Time", "")
            ))
            
    def save_visitor_prospect(self):
        name = self.visitor_form["ent_v_name"].get().strip()
        contact = self.visitor_form["ent_v_contact"].get().strip()
        plan = self.cb_v_plan.get()
        notes = self.ent_v_notes.get().strip()
        if not name or not contact:
            messagebox.showerror("Validation Error", "Name and Contact numbers are required.")
            return
        v_id = add_visitor(name, contact, plan, notes)
        
        base_dir = get_project_base_dir()
        dest = os.path.join(base_dir, "data", "receipts", f"VisitorPass_{v_id}.txt")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        pass_txt = f"""
==================================================
              VISITOR PASS - GYM PRO+
==================================================
Pass ID     : {v_id}
Date        : {datetime.now().strftime("%Y-%m-%d")}
Name        : {name}
Contact     : {contact}
Plan Interest: {plan}
--------------------------------------------------
Note: Registered guest database.
==================================================
"""
        with open(dest, "w") as f:
            f.write(pass_txt)
        messagebox.showinfo("Guest Pass Saved", f"Visitor Logged! ID: {v_id}\nTicket Pass saved.")
        self.visitor_form["ent_v_name"].delete(0, tk.END)
        self.visitor_form["ent_v_contact"].delete(0, tk.END)
        self.ent_v_notes.delete(0, tk.END)
        self.load_visitors_table()
        
    def load_visitors_table(self):
        for item in self.v_tree.get_children():
            self.v_tree.delete(item)
        for v in get_visitors_list():
            self.v_tree.insert("", "end", values=(v["Visitor ID"], v["Name"], v["Contact"], v["Plan to Join"], db_to_ui_date(v["Visit Date"])))

    # --- VIEW: WORKOUTS & DIETS PLANNER ---
    def show_planners(self):
        self.clear_content("🏋️ Workouts & Diet")
        
        # View Header
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        tk.Label(header, text="Workouts & Diet Planners", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        self.add_gym_branding_header(header)
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=25, pady=(5, 15))
        
        pres_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(pres_tab, text="👥 Member Assigned Planners")
        
        grid_frame = tk.Frame(pres_tab, bg=BG_PRIMARY, pady=10)
        grid_frame.pack(fill="both", expand=True)
        
        table_frame = tk.Frame(grid_frame, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.planner_m_tree = ttk.Treeview(table_frame, columns=("ID", "Name", "WorkoutPlan", "DietPlan"), show="headings")
        self.planner_m_tree.heading("ID", text="Member ID")
        self.planner_m_tree.heading("Name", text="Member Name")
        self.planner_m_tree.heading("WorkoutPlan", text="Workout Program Prescribed")
        self.planner_m_tree.heading("DietPlan", text="Diet Program Prescribed")
        
        self.planner_m_tree.column("ID", width=95, anchor="center")
        self.planner_m_tree.column("Name", width=150)
        self.planner_m_tree.column("WorkoutPlan", width=220)
        self.planner_m_tree.column("DietPlan", width=220)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.planner_m_tree.yview)
        self.planner_m_tree.configure(yscrollcommand=scrollbar.set)
        self.planner_m_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.planner_m_tree.bind("<Double-Button-1>", lambda e: self.on_prescribed_member_select())
        
        btn_action_f = tk.Frame(pres_tab, bg=BG_PRIMARY, pady=10)
        btn_action_f.pack(fill="x")
        btn_assign = tk.Button(btn_action_f, text="📋 Prescribe/Assign Program", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=15, pady=6, cursor="hand2", command=self.prescribe_selected_planner_member)
        btn_assign.pack(side="left", padx=10)
        
        self.load_member_prescriptions_table()
        
        lib_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(lib_tab, text="📚 Templates Library")
        
        templates_split = tk.Frame(lib_tab, bg=BG_PRIMARY, pady=10)
        templates_split.pack(fill="both", expand=True)
        
        w_box = tk.Frame(templates_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=15)
        w_box.pack(side="left", fill="both", expand=True, padx=(0, 5))
        d_box = tk.Frame(templates_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=15)
        d_box.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        tk.Label(w_box, text="Workout Templates Library", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        self.wrk_listbox = tk.Listbox(w_box, bg=BG_PRIMARY, fg=TEXT_MAIN, selectbackground=ACCENT, selectforeground=BG_SECONDARY, font=("Segoe UI", 9), bd=1, highlightbackground=CARD_BORDER)
        self.wrk_listbox.pack(fill="both", expand=True, pady=10)
        
        # Workout actions (Requirement 1)
        w_btn_frame = tk.Frame(w_box, bg=BG_SECONDARY)
        w_btn_frame.pack(fill="x")
        
        btn_w_add = tk.Button(w_btn_frame, text="➕ Add Template", font=("Segoe UI", 8, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=8, pady=4, cursor="hand2", command=self.add_workout_template)
        btn_w_add.pack(side="left", padx=2)
        
        btn_w_edit = tk.Button(w_btn_frame, text="✏️ Edit", font=("Segoe UI", 8, "bold"), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=8, pady=3, cursor="hand2", command=self.edit_workout_template)
        btn_w_edit.pack(side="left", padx=2)
        
        btn_w_del = tk.Button(w_btn_frame, text="❌ Delete", font=("Segoe UI", 8, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, padx=8, pady=4, cursor="hand2", command=self.delete_workout_template)
        btn_w_del.pack(side="left", padx=2)
        
        tk.Label(d_box, text="Diet Templates Library", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        self.diet_listbox = tk.Listbox(d_box, bg=BG_PRIMARY, fg=TEXT_MAIN, selectbackground=ACCENT, selectforeground=BG_SECONDARY, font=("Segoe UI", 9), bd=1, highlightbackground=CARD_BORDER)
        self.diet_listbox.pack(fill="both", expand=True, pady=10)
        
        # Diet actions (Requirement 1)
        d_btn_frame = tk.Frame(d_box, bg=BG_SECONDARY)
        d_btn_frame.pack(fill="x")
        
        btn_d_add = tk.Button(d_btn_frame, text="➕ Add Template", font=("Segoe UI", 8, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=8, pady=4, cursor="hand2", command=self.add_diet_template)
        btn_d_add.pack(side="left", padx=2)
        
        btn_d_edit = tk.Button(d_btn_frame, text="✏️ Edit", font=("Segoe UI", 8, "bold"), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=8, pady=3, cursor="hand2", command=self.edit_diet_template)
        btn_d_edit.pack(side="left", padx=2)
        
        btn_d_del = tk.Button(d_btn_frame, text="❌ Delete", font=("Segoe UI", 8, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, padx=8, pady=4, cursor="hand2", command=self.delete_diet_template)
        btn_d_del.pack(side="left", padx=2)
        
        self.load_libraries_listboxes()
        
    def load_member_prescriptions_table(self):
        for item in self.planner_m_tree.get_children():
            self.planner_m_tree.delete(item)
        m_df = load_dataframe("members.xlsx")
        w_df = load_dataframe("workout_plans.xlsx")
        d_df = load_dataframe("diet_plans.xlsx")
        if m_df.empty: return
        for _, row in m_df.iterrows():
            m_id = row["Member ID"]
            w_pres = w_df[w_df["Member ID"] == m_id]
            w_name = w_pres.iloc[0]["Plan Name"] if not w_pres.empty else "N/A"
            d_pres = d_df[d_df["Member ID"] == m_id]
            d_name = d_pres.iloc[0]["Plan Name"] if not d_pres.empty else "N/A"
            self.planner_m_tree.insert("", "end", values=(m_id, row["Name"], w_name, d_name))
            
    def load_libraries_listboxes(self):
        self.wrk_listbox.delete(0, tk.END)
        self.diet_listbox.delete(0, tk.END)
        for w in get_workout_templates():
            self.wrk_listbox.insert(tk.END, f"{w['Plan Name']} [{w['Target/Goal']}]")
        for d in get_diet_templates():
            self.diet_listbox.insert(tk.END, f"{d['Plan Name']} [{d['Target/Goal']}]")
            
    def add_workout_template(self):
        TemplateFormModal(self, "workout", "add")
        
    def edit_workout_template(self):
        selection = self.wrk_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a workout template from the list to edit.")
            return
        templates = get_workout_templates()
        selected_data = templates[selection[0]]
        TemplateFormModal(self, "workout", "edit", selected_data)
        
    def delete_workout_template(self):
        selection = self.wrk_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a workout template from the list to delete.")
            return
        templates = get_workout_templates()
        selected_data = templates[selection[0]]
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the workout template '{selected_data['Plan Name']}'?"):
            delete_workout_plan(selected_data["Plan ID"])
            messagebox.showinfo("Deleted", "Workout template deleted successfully.")
            self.load_libraries_listboxes()
            
    def add_diet_template(self):
        TemplateFormModal(self, "diet", "add")
        
    def edit_diet_template(self):
        selection = self.diet_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a diet template from the list to edit.")
            return
        templates = get_diet_templates()
        selected_data = templates[selection[0]]
        TemplateFormModal(self, "diet", "edit", selected_data)
        
    def delete_diet_template(self):
        selection = self.diet_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a diet template from the list to delete.")
            return
        templates = get_diet_templates()
        selected_data = templates[selection[0]]
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the diet template '{selected_data['Plan Name']}'?"):
            delete_diet_plan(selected_data["Diet ID"])
            messagebox.showinfo("Deleted", "Diet template deleted successfully.")
            self.load_libraries_listboxes()
            
    def on_prescribed_member_select(self):
        selected = self.planner_m_tree.selection()
        if not selected: return
        m_id = self.planner_m_tree.item(selected[0])["values"][0]
        FitnessTrackerModal(self, member_id=m_id)
        
    def prescribe_selected_planner_member(self):
        selected = self.planner_m_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Select a member.")
            return
        m_id = self.planner_m_tree.item(selected[0])["values"][0]
        AssignPlanModal(self, member_id=m_id)

    # --- VIEW: PAYMENTS & BILLING ---
    def show_payments(self):
        self.clear_content("💳 Payments & Billing")
        
        # View Header
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        tk.Label(header, text="Payments & Billing Center", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        self.add_gym_branding_header(header)
        
        main_split = tk.Frame(self.content_frame, bg=BG_PRIMARY)
        main_split.pack(fill="both", expand=True, padx=25, pady=(5, 10))
        
        left_side = tk.Frame(main_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=15)
        left_side.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left_side.pack_propagate(False)
        left_side.config(width=340)
        
        right_side = tk.Frame(main_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        right_side.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Renewal queue listbox
        tk.Label(left_side, text="⏳ Renewal Billing Queue", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 5))
        tk.Label(left_side, text="Select member to auto-populate fields:", font=("Segoe UI", 8, "italic"), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
        
        self.due_tree = ttk.Treeview(left_side, columns=("ID", "Name", "Status"), show="headings", height=15)
        self.due_tree.heading("ID", text="ID")
        self.due_tree.heading("Name", text="Member Name")
        self.due_tree.heading("Status", text="Status")
        self.due_tree.column("ID", width=65, anchor="center")
        self.due_tree.column("Status", width=75, anchor="center")
        self.due_tree.pack(fill="both", expand=True)
        self.due_tree.bind("<<TreeviewSelect>>", self.on_due_member_select)
        
        # Invoicing billing form console
        tk.Label(right_side, text="💳 Renewal & Billing Ledger", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 15))
        
        form = tk.Frame(right_side, bg=BG_SECONDARY)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        
        # Fields
        tk.Label(form, text="Member ID / Code:", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=0, column=0, sticky="w", pady=6)
        self.ent_bill_mid = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_bill_mid.grid(row=0, column=1, sticky="ew", pady=6, ipady=4)
        
        tk.Label(form, text="Choose Renewal Plan:", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=1, column=0, sticky="w", pady=6)
        self.cb_bill_plan = ttk.Combobox(form, values=["Monthly", "Quarterly", "Half-Yearly", "Annually"], state="readonly")
        self.cb_bill_plan.grid(row=1, column=1, sticky="ew", pady=6)
        self.cb_bill_plan.set("Monthly")
        
        # Date of payment (Requirement 5)
        tk.Label(form, text="Receipt Date (DD-MM-YYYY):", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=2, column=0, sticky="w", pady=6)
        self.ent_bill_pdate = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_bill_pdate.grid(row=2, column=1, sticky="ew", pady=6, ipady=4)
        self.ent_bill_pdate.insert(0, db_to_ui_date(datetime.now().strftime("%Y-%m-%d")))
        
        tk.Label(form, text="Plan Base Fees:", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=3, column=0, sticky="w", pady=6)
        self.ent_bill_gym_fees = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_bill_gym_fees.grid(row=3, column=1, sticky="ew", pady=6, ipady=4)
        self.ent_bill_gym_fees.insert(0, "1500")
        
        tk.Label(form, text="Gym Discount (%):", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=4, column=0, sticky="w", pady=6)
        self.ent_bill_gym_disc = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_bill_gym_disc.grid(row=4, column=1, sticky="ew", pady=6, ipady=4)
        self.ent_bill_gym_disc.insert(0, "0")
        
        self.trainer_options = {}
        self.load_trainers_list()
        
        tk.Label(form, text="Personal Coach Required?", fg=TEXT_MUTED, bg=BG_SECONDARY).grid(row=5, column=0, sticky="w", pady=6)
        self.cb_bill_treq = ttk.Combobox(form, values=["No", "Yes"], state="readonly")
        self.cb_bill_treq.grid(row=5, column=1, sticky="ew", pady=6)
        self.cb_bill_treq.set("No")
        self.cb_bill_treq.bind("<<ComboboxSelected>>", self.toggle_billing_trainer_fields)
        
        self.lbl_t_select = tk.Label(form, text="Choose Coach:", fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.cb_bill_tselect = ttk.Combobox(form, values=list(self.trainer_options.keys()), state="readonly")
        self.cb_bill_tselect.bind("<<ComboboxSelected>>", self.on_billing_coach_select)
        
        self.lbl_t_fees = tk.Label(form, text="Coach Fees:", fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.ent_bill_tfees = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        
        self.lbl_t_disc = tk.Label(form, text="Coach Discount (%):", fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.ent_bill_tdisc = tk.Entry(form, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_bill_tdisc.insert(0, "0")
        
        self.ent_bill_gym_fees.bind("<KeyRelease>", self.recalculate_billing_previews)
        self.ent_bill_gym_disc.bind("<KeyRelease>", self.recalculate_billing_previews)
        self.ent_bill_tfees.bind("<KeyRelease>", self.recalculate_billing_previews)
        self.ent_bill_tdisc.bind("<KeyRelease>", self.recalculate_billing_previews)
        
        # Calculations details card
        self.bill_calc_card = tk.Frame(right_side, bg=BG_PRIMARY, padx=15, pady=12, highlightbackground=CARD_BORDER, highlightthickness=1)
        self.bill_calc_card.pack(fill="x", pady=15)
        
        self.lbl_bill_gym_calc = tk.Label(self.bill_calc_card, text="Gym Charge: Rs.0.00", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_PRIMARY)
        self.lbl_bill_gym_calc.pack(anchor="w")
        self.lbl_bill_coach_calc = tk.Label(self.bill_calc_card, text="Coach Charge: Rs.0.00", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_PRIMARY)
        self.lbl_bill_coach_calc.pack(anchor="w")
        self.lbl_bill_net_calc = tk.Label(self.bill_calc_card, text="Net Amount Due: Rs.0.00", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_PRIMARY)
        self.lbl_bill_net_calc.pack(anchor="w", pady=(5, 0))
        
        btn_renew = tk.Button(right_side, text="⚡ Pay & Renew Plan", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=10, command=self.action_process_renewal_payment)
        btn_renew.pack(fill="x")
        
        self.load_due_members_queue()
        self.toggle_billing_trainer_fields()
        
    def load_trainers_list(self):
        self.trainer_options.clear()
        df = load_dataframe("trainers.xlsx")
        if not df.empty:
            for _, r in df[df["Status"] == "Active"].iterrows():
                self.trainer_options[r["Trainer ID"]] = (r["Name"], float(r["Base Fees"]))
                
    def load_due_members_queue(self):
        for item in self.due_tree.get_children():
            self.due_tree.delete(item)
        df = load_dataframe("members.xlsx")
        if df.empty: return
        for _, row in df.iterrows():
            self.due_tree.insert("", "end", values=(row["Member ID"], row["Name"], row["Status"]))
                
    def on_due_member_select(self, event):
        selected = self.due_tree.selection()
        if not selected: return
        m_id = self.due_tree.item(selected[0])["values"][0]
        self.load_billing_for_member(m_id)
        
    def load_billing_for_member(self, member_id):
        m = get_member_details(member_id)
        if not m: return
        
        self.ent_bill_mid.delete(0, tk.END)
        self.ent_bill_mid.insert(0, member_id)
        self.cb_bill_plan.set(m["Plan Type"])
        self.ent_bill_gym_fees.delete(0, tk.END)
        self.ent_bill_gym_fees.insert(0, str(m["Base Fees"]))
        self.ent_bill_gym_disc.delete(0, tk.END)
        self.ent_bill_gym_disc.insert(0, str(m["Discount (%)"]))
        
        self.cb_bill_treq.set(m["Trainer Required"])
        self.toggle_billing_trainer_fields()
        
        if m["Trainer Required"] == "Yes":
            self.cb_bill_tselect.set(m["Trainer ID"])
            self.ent_bill_tfees.delete(0, tk.END)
            self.ent_bill_tfees.insert(0, str(m["Trainer Fees"]))
            self.ent_bill_tdisc.delete(0, tk.END)
            self.ent_bill_tdisc.insert(0, str(m["Trainer Discount (%)"]))
        self.recalculate_billing_previews()
        
    def toggle_billing_trainer_fields(self, event=None):
        if self.cb_bill_treq.get() == "Yes":
            self.lbl_t_select.grid(row=6, column=0, sticky="w", pady=6)
            self.cb_bill_tselect.grid(row=6, column=1, sticky="ew", pady=6)
            self.lbl_t_fees.grid(row=7, column=0, sticky="w", pady=6)
            self.ent_bill_tfees.grid(row=7, column=1, sticky="ew", pady=6, ipady=4)
            self.lbl_t_disc.grid(row=8, column=0, sticky="w", pady=6)
            self.ent_bill_tdisc.grid(row=8, column=1, sticky="ew", pady=6, ipady=4)
        else:
            self.lbl_t_select.grid_forget()
            self.cb_bill_tselect.grid_forget()
            self.lbl_t_fees.grid_forget()
            self.ent_bill_tfees.grid_forget()
            self.lbl_t_disc.grid_forget()
            self.ent_bill_tdisc.grid_forget()
        self.recalculate_billing_previews()
        
    def on_billing_coach_select(self, event):
        t_id = self.cb_bill_tselect.get()
        if t_id in self.trainer_options:
            name, base_fee = self.trainer_options[t_id]
            self.ent_bill_tfees.delete(0, tk.END)
            self.ent_bill_tfees.insert(0, str(base_fee))
            self.recalculate_billing_previews()
            
    def recalculate_billing_previews(self, event=None):
        try:
            base_g = float(self.ent_bill_gym_fees.get() or 0.0)
            disc_g = float(self.ent_bill_gym_disc.get() or 0.0)
            gym_bill = base_g * (1.0 - disc_g / 100.0)
        except ValueError:
            gym_bill = 0.0
            
        coach_bill = 0.0
        if self.cb_bill_treq.get() == "Yes":
            try:
                base_c = float(self.ent_bill_tfees.get() or 0.0)
                disc_c = float(self.ent_bill_tdisc.get() or 0.0)
                coach_bill = base_c * (1.0 - disc_c / 100.0)
            except ValueError:
                coach_bill = 0.0
                
        currency = self.settings.get("currency", "Rs.")
        self.lbl_bill_gym_calc.config(text=f"Gym Charge: {currency}{gym_bill:,.2f}")
        self.lbl_bill_coach_calc.config(text=f"Coach Charge: {currency}{coach_bill:,.2f}")
        self.lbl_bill_net_calc.config(text=f"Net Amount Due: {currency}{(gym_bill + coach_bill):,.2f}")
        
    def action_process_renewal_payment(self):
        m_id = self.ent_bill_mid.get().strip().upper()
        plan = self.cb_bill_plan.get()
        p_date = self.ent_bill_pdate.get().strip()
        p_date_db = ui_to_db_date(p_date)
        
        if not m_id or not p_date:
            messagebox.showerror("Error", "Required fields missing.")
            return
            
        try:
            datetime.strptime(p_date_db, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid Date format. Use DD-MM-YYYY.")
            return
            
        try:
            g_fees = float(self.ent_bill_gym_fees.get())
            g_disc = float(self.ent_bill_gym_disc.get())
            gym_bill = g_fees * (1.0 - g_disc / 100.0)
        except ValueError:
            messagebox.showerror("Error", "Gym fees must be numeric.")
            return
            
        t_req = self.cb_bill_treq.get()
        t_id, t_fees, t_disc, coach_bill = None, 0.0, 0.0, 0.0
        
        if t_req == "Yes":
            t_id = self.cb_bill_tselect.get()
            if not t_id:
                messagebox.showerror("Error", "Choose coach.")
                return
            try:
                t_fees = float(self.ent_bill_tfees.get())
                t_disc = float(self.ent_bill_tdisc.get())
                coach_bill = t_fees * (1.0 - t_disc / 100.0)
            except ValueError:
                messagebox.showerror("Error", "Coach fees must be numeric.")
                return
                
        net_due = gym_bill + coach_bill
        
        success, msg = record_payment(
            member_id=m_id,
            amount_paid=net_due,
            payment_for="Renewal Package",
            notes=f"Renewed plan: {plan}",
            renew_plan=plan,
            trainer_id=t_id,
            trainer_fees=t_fees,
            discount_pct=g_disc,
            trainer_discount_pct=t_disc,
            payment_date=p_date_db
        )
        
        if success:
            receipt_path = ""
            if "Receipt generated:" in msg:
                receipt_path = msg.split("Receipt generated:")[1].strip()
                
            # Auto-open PDF Receipt immediately (Requirement 2)
            if receipt_path and os.path.exists(receipt_path):
                try:
                    os.startfile(receipt_path)
                except Exception as ex:
                    print(f"Error open pdf: {ex}")
                    
            dialog = tk.Toplevel(self)
            dialog.title("Payment Processed")
            dialog.geometry("500x380")
            dialog.configure(bg=BG_PRIMARY)
            dialog.transient(self)
            dialog.grab_set()
            
            tk.Label(dialog, text="✔ Payment Processed Successfully", font=("Segoe UI", 13, "bold"), fg=SUCCESS, bg=BG_PRIMARY, pady=15).pack()
            
            info = tk.Frame(dialog, bg=BG_SECONDARY, padx=15, pady=15, highlightbackground=CARD_BORDER, highlightthickness=1)
            info.pack(fill="x", padx=30)
            
            tk.Label(info, text=f"Member ID : {m_id}", fg=TEXT_MAIN, bg=BG_SECONDARY, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(info, text=f"Plan Renewed : {plan}", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w")
            tk.Label(info, text=f"Total Paid : {self.settings.get('currency', 'Rs.')}{net_due:,.2f}", fg=ACCENT, bg=BG_SECONDARY, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            
            btn_box = tk.Frame(dialog, bg=BG_PRIMARY, pady=20)
            btn_box.pack(fill="x")
            
            if receipt_path and os.path.exists(receipt_path):
                btn_print = tk.Button(btn_box, text="🖨️ Print Receipt", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=15, pady=8,
                                      command=lambda: os.startfile(receipt_path, "print") if sys.platform == 'win32' else messagebox.showinfo("Print Command Sent", receipt_path))
                btn_print.pack(side="left", padx=(50, 10))
                
            btn_close = tk.Button(btn_box, text="Close", font=("Segoe UI", 10), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=8, command=dialog.destroy)
            btn_close.pack(side="left")
            
            self.load_due_members_queue()
        else:
            messagebox.showerror("Billing Failed", msg)

    # --- VIEW: SYSTEM SETTINGS ---
    def show_settings(self):
        self.clear_content("⚙️ Maintenance")
        
        header = tk.Frame(self.content_frame, bg=BG_PRIMARY, pady=15, padx=25)
        header.pack(fill="x")
        tk.Label(header, text="System Maintenance & Settings", font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=BG_PRIMARY).pack(side="left")
        self.add_gym_branding_header(header)
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        sys_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(sys_tab, text="📦 Database Operations")
        
        scroll_container = tk.Frame(sys_tab, bg=BG_PRIMARY, padx=20, pady=10)
        scroll_container.pack(fill="both", expand=True)
        
        # Reports export
        rep_panel = tk.Frame(scroll_container, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=15)
        rep_panel.pack(fill="x", pady=5)
        tk.Label(rep_panel, text="📊 Export Excel Reports Pack", font=("Segoe UI", 11, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        tk.Button(rep_panel, text="Generate Reports Pack", bg=ACCENT, fg=BG_SECONDARY, font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=6, command=self.export_reports_action).pack(anchor="w", pady=(5, 0))
        
        # Backup panel
        back_panel = tk.Frame(scroll_container, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=15)
        back_panel.pack(fill="x", pady=10)
        tk.Label(back_panel, text="📦 Archive Backups", font=("Segoe UI", 11, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        tk.Button(back_panel, text="🛡️ Back Up All Data", bg=BG_PRIMARY, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold"), bd=1, highlightbackground=CARD_BORDER, padx=15, pady=6, command=self.backup_data_action).pack(side="left", pady=5, padx=(0, 10))
        tk.Button(back_panel, text="⏪ Restore from Backup", bg=BG_PRIMARY, fg=ALERT, font=("Segoe UI", 9, "bold"), bd=1, highlightbackground=ALERT, padx=15, pady=6, command=self.restore_data_action).pack(side="left", pady=5)
        
        # Year splits
        split_panel = tk.Frame(scroll_container, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=15)
        split_panel.pack(fill="x", pady=10)
        tk.Label(split_panel, text="📆 Year-Wise Splitting", font=("Segoe UI", 11, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        row_s = tk.Frame(split_panel, bg=BG_SECONDARY, pady=5)
        row_s.pack(fill="x")
        tk.Label(row_s, text="New Year String (e.g. FY_2027-28):", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left", padx=(0, 10))
        self.ent_new_fy = tk.Entry(row_s, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10), width=15)
        self.ent_new_fy.pack(side="left", padx=5, ipady=4)
        tk.Button(row_s, text="⚡ Split Data Now", bg=ALERT, fg=BG_SECONDARY, font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=5, command=self.split_year_action).pack(side="left", padx=10)
        
        # Account manager
        users_tab = tk.Frame(notebook, bg=BG_PRIMARY)
        notebook.add(users_tab, text="👥 User Accounts Manager")
        
        u_split = tk.Frame(users_tab, bg=BG_PRIMARY, pady=10)
        u_split.pack(fill="both", expand=True)
        
        u_left = tk.Frame(u_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        u_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        u_right = tk.Frame(u_split, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=15, pady=20)
        u_right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        tk.Label(u_left, text="Create Staff Login Accounts", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 15))
        
        tk.Label(u_left, text="Login Username ID:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w")
        self.ent_u_name = tk.Entry(u_left, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_u_name.pack(fill="x", ipady=4, pady=5)
        
        tk.Label(u_left, text="Choose Account Password:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w")
        self.ent_u_pass = tk.Entry(u_left, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_u_pass.pack(fill="x", ipady=4, pady=5)
        
        tk.Label(u_left, text="Assign System Role Permission:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(anchor="w")
        self.cb_u_role = ttk.Combobox(u_left, values=["Desk Manager", "Admin"], state="readonly")
        self.cb_u_role.pack(fill="x", pady=5)
        self.cb_u_role.set("Desk Manager")
        
        btn_u_save = tk.Button(u_left, text="💾 Save Staff Account", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=8, command=self.save_staff_account)
        btn_u_save.pack(fill="x", pady=(15, 0))
        
        # grid list
        self.u_tree = ttk.Treeview(u_right, columns=("Name", "Role"), show="headings")
        self.u_tree.heading("Name", text="Login User ID")
        self.u_tree.heading("Role", text="Role Assigned")
        self.u_tree.pack(fill="both", expand=True)
        
        btn_u_del = tk.Button(u_right, text="Remove Selected Account", font=("Segoe UI", 9, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, pady=6, command=self.delete_staff_account)
        btn_u_del.pack(fill="x", pady=(10, 0))
        
        btn_u_pchange = tk.Button(u_right, text="Modify Password", font=("Segoe UI", 9, "bold"), bg=BG_PRIMARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, pady=6, command=self.open_change_password_modal)
        btn_u_pchange.pack(fill="x", pady=(5, 0))
        
        self.load_users_table()
        
    def save_staff_account(self):
        uname = self.ent_u_name.get().strip()
        upass = self.ent_u_pass.get().strip()
        role = self.cb_u_role.get()
        if not uname or not upass:
            messagebox.showerror("Error", "Fill in all details.")
            return
        success, msg = add_user(uname, upass, role)
        if success:
            messagebox.showinfo("Success", msg)
            self.ent_u_name.delete(0, tk.END)
            self.ent_u_pass.delete(0, tk.END)
            self.load_users_table()
        else:
            messagebox.showerror("Failed", msg)
            
    def delete_staff_account(self):
        selected = self.u_tree.selection()
        if not selected: return
        uname = self.u_tree.item(selected[0])["values"][0]
        confirm = messagebox.askyesno("Confirm Delete", f"Delete account: {uname}?")
        if confirm:
            success, msg = delete_user(uname)
            if success:
                messagebox.showinfo("Deleted", msg)
                self.load_users_table()
                
    def load_users_table(self):
        for item in self.u_tree.get_children():
            self.u_tree.delete(item)
        for u in get_users_list():
            self.u_tree.insert("", "end", values=(u["Username"], u["Role"]))
            
    def open_change_password_modal(self):
        dialog = tk.Toplevel(self)
        dialog.title("Change Account Password")
        dialog.geometry("380x300")
        dialog.configure(bg=BG_PRIMARY)
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="🔑 Reset Account Password", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_PRIMARY, pady=15).pack()
        form = tk.Frame(dialog, bg=BG_PRIMARY, padx=25)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        tk.Label(form, text="Target User ID:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=0, column=0, sticky="w", pady=8)
        if self.current_user["role"] == "Admin":
            cb_user = ttk.Combobox(form, values=[u["Username"] for u in get_users_list()], state="readonly")
            cb_user.grid(row=0, column=1, sticky="ew", pady=8)
            cb_user.set(self.current_user["username"])
        else:
            cb_user = ttk.Combobox(form, values=[self.current_user["username"]], state="disabled")
            cb_user.grid(row=0, column=1, sticky="ew", pady=8)
            cb_user.set(self.current_user["username"])
            
        tk.Label(form, text="New Password:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=1, column=0, sticky="w", pady=8)
        ent_pass = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        ent_pass.grid(row=1, column=1, sticky="ew", pady=8, ipady=4)
        
        def save_pw():
            target = cb_user.get()
            pw = ent_pass.get().strip()
            if not pw:
                messagebox.showerror("Error", "Fill password.")
                return
            if change_password(target, pw):
                messagebox.showinfo("Success", f"Password changed for user: {target}")
                dialog.destroy()
                
        btn_action = tk.Button(dialog, text="Update Password Now", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=10, command=save_pw)
        btn_action.pack(fill="x", side="bottom", padx=25, pady=25)
        
    def export_reports_action(self):
        dest_folder = filedialog.askdirectory(title="Select Folder to Export Reports")
        if not dest_folder: return
        success, file_path = export_all_reports(dest_folder)
        if success:
            messagebox.showinfo("Export Successful", f"Excel reports saved to:\n{file_path}")
            
    def backup_data_action(self):
        success, file_path = create_backup()
        if success:
            messagebox.showinfo("Backup Success", f"ZIP archive created at:\n{file_path}")
            
    def restore_data_action(self):
        confirm = messagebox.askyesno("Restore Warning", "Restoring will overwrite current files. Continue?")
        if not confirm: return
        zip_path = filedialog.askopenfilename(title="Select Backup ZIP Archive", filetypes=[("Zip Archives", "*.zip")])
        if not zip_path: return
        success, msg = restore_backup(zip_path)
        if success:
            messagebox.showinfo("Restore Success", msg)
            self.settings = load_settings()
            self.show_dashboard()
            
    def split_year_action(self):
        new_year = self.ent_new_fy.get().strip()
        if not new_year:
            messagebox.showerror("Error", "Enter year identifier.")
            return
        confirm = messagebox.askyesno("Confirm Split", f"Move to active working year '{new_year}'?")
        if not confirm: return
        success, msg = split_data_for_new_year(new_year)
        if success:
            messagebox.showinfo("Success", msg)
            self.settings = load_settings()
            self.show_settings()


# ================= MODALS & DETAILS POPUPS SECTION =================

class TotalIncomeDetailsModal(tk.Toplevel):
    """Interactive Income Card click detailed log with Date Filter options (Requirement 7)."""
    def __init__(self, parent, start_date, end_date):
        super().__init__(parent)
        self.parent = parent
        self.start_date = start_date
        self.end_date = end_date
        
        self.title("Payments & Income Report")
        self.geometry("750x500")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        
        self.build_ui()
        self.load_payments_history()
        
    def build_ui(self):
        header_f = tk.Frame(self, bg=BG_PRIMARY, pady=10)
        header_f.pack(fill="x")
        
        tk.Label(header_f, text="💰 Interactive Payments Registry Ledger", font=("Segoe UI", 13, "bold"), fg=ACCENT, bg=BG_PRIMARY).pack()
        
        # Date inputs Row
        filter_f = tk.Frame(self, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=8)
        filter_f.pack(fill="x", padx=20, pady=5)
        
        tk.Label(filter_f, text="From Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left")
        self.ent_p_start = tk.Entry(filter_f, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_p_start.pack(side="left", padx=5, ipady=2)
        self.ent_p_start.insert(0, db_to_ui_date(self.start_date))
        
        tk.Label(filter_f, text="To Date:", fg=TEXT_MUTED, bg=BG_SECONDARY).pack(side="left", padx=(10, 0))
        self.ent_p_end = tk.Entry(filter_f, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), width=12, bd=1, highlightbackground=CARD_BORDER)
        self.ent_p_end.pack(side="left", padx=5, ipady=2)
        self.ent_p_end.insert(0, db_to_ui_date(self.end_date))
        
        btn_apply = tk.Button(filter_f, text="Apply Filter", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=12, pady=4, command=self.apply_filter)
        btn_apply.pack(side="left", padx=15)
        
        # Grid View table
        grid_f = tk.Frame(self, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1)
        grid_f.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.pay_history_tree = ttk.Treeview(grid_f, columns=("ID", "MemberID", "Name", "Amount", "Date", "For", "Notes"), show="headings")
        self.pay_history_tree.heading("ID", text="Receipt ID")
        self.pay_history_tree.heading("MemberID", text="Member ID")
        self.pay_history_tree.heading("Name", text="Member Name")
        self.pay_history_tree.heading("Amount", text="Amount Paid")
        self.pay_history_tree.heading("Date", text="Payment Date")
        self.pay_history_tree.heading("For", text="Payment For")
        self.pay_history_tree.heading("Notes", text="Notes")
        
        self.pay_history_tree.column("ID", width=80, anchor="center")
        self.pay_history_tree.column("MemberID", width=80, anchor="center")
        self.pay_history_tree.column("Amount", width=95, anchor="center")
        self.pay_history_tree.column("Date", width=95, anchor="center")
        self.pay_history_tree.pack(fill="both", expand=True)
        
        # Sum card
        self.sum_lbl = tk.Label(self, text="Total Summary: Rs.0.00", font=("Segoe UI", 11, "bold"), fg=SUCCESS, bg=BG_PRIMARY, pady=10)
        self.sum_lbl.pack(anchor="e", padx=20)
        
    def apply_filter(self):
        self.start_date = ui_to_db_date(self.ent_p_start.get().strip())
        self.end_date = ui_to_db_date(self.ent_p_end.get().strip())
        self.load_payments_history()
        
    def load_payments_history(self):
        for item in self.pay_history_tree.get_children():
            self.pay_history_tree.delete(item)
            
        df = load_dataframe("payments.xlsx")
        if df.empty: return
        
        total_sum = 0.0
        try:
            df["Date_Parsed"] = pd.to_datetime(df["Payment Date"], errors="coerce")
            start = pd.to_datetime(self.start_date, errors="coerce")
            end = pd.to_datetime(self.end_date, errors="coerce")
            
            filtered = df[(df["Date_Parsed"] >= start) & (df["Date_Parsed"] <= end)]
                
            for _, r in filtered.iterrows():
                amt = float(r["Amount Paid"])
                self.pay_history_tree.insert("", "end", values=(
                    r["Payment ID"], r["Member ID"], r["Member Name"],
                    f"{self.parent.settings.get('currency', 'Rs.')}{amt:,.2f}",
                    db_to_ui_date(r["Payment Date"]), r["Payment For"], r["Notes"]
                ))
                total_sum += amt
        except Exception as e:
            print(f"Error filtering pay modal: {e}")
            
        self.sum_lbl.config(text=f"Total Revenue Generated in Period: {self.parent.settings.get('currency', 'Rs.')}{total_sum:,.2f}")


class MemberFormModal(tk.Toplevel):
    def __init__(self, parent, mode="add", member_id=None):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode
        self.member_id = member_id
        
        self.title("Add New Gym Member" if mode == "add" else f"Modify Member {member_id}")
        self.geometry("620x680")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        
        self.photo_path = ""
        self.trainer_dict = {}
        self.load_trainers_list()
        self.build_ui()
        if mode == "edit":
            self.load_member_fields()
            
    def load_trainers_list(self):
        df = load_dataframe("trainers.xlsx")
        if not df.empty:
            active_t = df[df["Status"] == "Active"]
            for _, r in active_t.iterrows():
                self.trainer_dict[r["Trainer ID"]] = (r["Name"], float(r["Base Fees"]))
                
    def build_ui(self):
        title_text = "✨ Enroll Gym Member" if self.mode == "add" else f"✏️ Modify Details: {self.member_id}"
        tk.Label(self, text=title_text, font=("Segoe UI", 14, "bold"), fg=ACCENT, bg=BG_PRIMARY, pady=15).pack()
        
        scroll_frame = tk.Frame(self, bg=BG_PRIMARY)
        scroll_frame.pack(fill="both", expand=True, padx=20)
        
        form = tk.Frame(scroll_frame, bg=BG_PRIMARY)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        # Info input rows
        tk.Label(form, text="Full Name:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=0, column=0, sticky="w", pady=5)
        self.ent_name = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_name.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)
        
        tk.Label(form, text="Contact No:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=1, column=0, sticky="w", pady=5)
        self.ent_contact = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_contact.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)
        
        tk.Label(form, text="Membership Plan:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=2, column=0, sticky="w", pady=5)
        self.cb_plan = ttk.Combobox(form, values=["Monthly", "Quarterly", "Half-Yearly", "Annually"], state="readonly")
        self.cb_plan.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        self.cb_plan.set("Monthly")
        
        # Date column to enter the date (Requirement 2)
        tk.Label(form, text="Enrollment Date (DD-MM-YYYY):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=3, column=0, sticky="w", pady=5)
        self.ent_start = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_start.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)
        self.ent_start.insert(0, db_to_ui_date(datetime.now().strftime("%Y-%m-%d")))
        
        tk.Label(form, text="Base Gym Fees:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=4, column=0, sticky="w", pady=5)
        self.ent_base_fees = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_base_fees.grid(row=4, column=1, sticky="ew", pady=5, ipady=4)
        self.ent_base_fees.insert(0, "1500")
        
        tk.Label(form, text="Discount (%):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=5, column=0, sticky="w", pady=5)
        self.ent_discount = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_discount.grid(row=5, column=1, sticky="ew", pady=5, ipady=4)
        self.ent_discount.insert(0, "0")
        
        # Photo Selection
        tk.Label(form, text="Upload Photo (Optional):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=6, column=0, sticky="w", pady=5)
        self.lbl_photo_status = tk.Label(form, text="No File Selected", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 8, "italic"))
        self.lbl_photo_status.grid(row=6, column=1, sticky="w", pady=5)
        
        btn_upload = tk.Button(form, text="Browse", font=("Segoe UI", 8, "bold"), bg=BG_SECONDARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=10, pady=4, command=self.browse_photo)
        btn_upload.grid(row=6, column=2, sticky="e", pady=5)
        
        canvas_line = tk.Canvas(form, height=1, bg=CARD_BORDER, highlightthickness=0)
        canvas_line.grid(row=7, column=0, columnspan=3, sticky="ew", pady=15)
        
        # Trainer Details
        tk.Label(form, text="Trainer Required?", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=8, column=0, sticky="w", pady=5)
        self.cb_trainer_req = ttk.Combobox(form, values=["No", "Yes"], state="readonly")
        self.cb_trainer_req.grid(row=8, column=1, columnspan=2, sticky="ew", pady=5)
        self.cb_trainer_req.set("No")
        self.cb_trainer_req.bind("<<ComboboxSelected>>", self.toggle_trainer_fields)
        
        self.lbl_trainer_lbl = tk.Label(form, text="Select Coach:", fg=TEXT_MUTED, bg=BG_PRIMARY)
        self.cb_trainer_select = ttk.Combobox(form, values=list(self.trainer_dict.keys()), state="readonly")
        self.cb_trainer_select.bind("<<ComboboxSelected>>", self.on_trainer_selected)
        
        self.lbl_trainer_fees_lbl = tk.Label(form, text="Trainer Fees (Monthly):", fg=TEXT_MUTED, bg=BG_PRIMARY)
        self.ent_trainer_fees = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        
        self.lbl_trainer_disc_lbl = tk.Label(form, text="Coach Discount (%):", fg=TEXT_MUTED, bg=BG_PRIMARY)
        self.ent_trainer_disc = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, font=("Segoe UI", 10))
        self.ent_trainer_disc.insert(0, "0")
        
        # Calculations preview frame
        self.calc_frame = tk.Frame(scroll_frame, bg=BG_SECONDARY, padx=15, pady=10)
        self.calc_frame.pack(fill="x", pady=15)
        
        self.lbl_calc_gym = tk.Label(self.calc_frame, text="Gym Billing: Rs.0.00", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.lbl_calc_gym.pack(anchor="w")
        self.lbl_calc_trainer = tk.Label(self.calc_frame, text="Trainer Billing: Rs.0.00", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.lbl_calc_trainer.pack(anchor="w")
        self.lbl_calc_total = tk.Label(self.calc_frame, text="Net Amount: Rs.0.00", font=("Segoe UI", 11, "bold"), fg=ACCENT, bg=BG_SECONDARY)
        self.lbl_calc_total.pack(anchor="w", pady=(5, 0))
        
        self.ent_base_fees.bind("<KeyRelease>", self.update_fee_previews)
        self.ent_discount.bind("<KeyRelease>", self.update_fee_previews)
        self.ent_trainer_fees.bind("<KeyRelease>", self.update_fee_previews)
        self.ent_trainer_disc.bind("<KeyRelease>", self.update_fee_previews)
        
        # Footer Action Button Frame
        btn_frame = tk.Frame(self, bg=BG_PRIMARY, pady=10)
        btn_frame.pack(fill="x", side="bottom", padx=20)
        
        btn_action = tk.Button(btn_frame, text="Save Member Record", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=10, command=self.save_record)
        btn_action.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Admin-only Deletion Button inside edit view (Requirement 6)
        if self.mode == "edit" and self.parent.current_user["role"] == "Admin":
            btn_remove = tk.Button(btn_frame, text="Remove Member", font=("Segoe UI", 11, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, pady=10, command=self.remove_member_record)
            btn_remove.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.toggle_trainer_fields()
        
    def remove_member_record(self):
        confirm = messagebox.askyesno("Confirm Removal", f"Are you sure you want to permanently delete member {self.member_id}?")
        if confirm:
            if delete_member(self.member_id):
                messagebox.showinfo("Removed", f"Member {self.member_id} deleted successfully.")
                self.parent.load_members_table()
                self.destroy()
            else:
                messagebox.showerror("Error", "Could not remove member.")
                
    def browse_photo(self):
        path = filedialog.askopenfilename(title="Select Member Photo", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            self.photo_path = path
            self.lbl_photo_status.config(text=os.path.basename(path), fg=SUCCESS)
            
    def toggle_trainer_fields(self, event=None):
        if self.cb_trainer_req.get() == "Yes":
            self.lbl_trainer_lbl.grid(row=9, column=0, sticky="w", pady=5)
            self.cb_trainer_select.grid(row=9, column=1, columnspan=2, sticky="ew", pady=5)
            self.lbl_trainer_fees_lbl.grid(row=10, column=0, sticky="w", pady=5)
            self.ent_trainer_fees.grid(row=10, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)
            self.lbl_trainer_disc_lbl.grid(row=11, column=0, sticky="w", pady=5)
            self.ent_trainer_disc.grid(row=11, column=1, columnspan=2, sticky="ew", pady=5, ipady=4)
        else:
            self.lbl_trainer_lbl.grid_forget()
            self.cb_trainer_select.grid_forget()
            self.lbl_trainer_fees_lbl.grid_forget()
            self.ent_trainer_fees.grid_forget()
            self.lbl_trainer_disc_lbl.grid_forget()
            self.ent_trainer_disc.grid_forget()
        self.update_fee_previews()
        
    def on_trainer_selected(self, event):
        t_id = self.cb_trainer_select.get()
        if t_id in self.trainer_dict:
            name, base_fee = self.trainer_dict[t_id]
            self.ent_trainer_fees.delete(0, tk.END)
            self.ent_trainer_fees.insert(0, str(base_fee))
            self.update_fee_previews()
            
    def update_fee_previews(self, event=None):
        try:
            base_gym = float(self.ent_base_fees.get() or 0.0)
            disc_gym = float(self.ent_discount.get() or 0.0)
            gym_bill = base_gym * (1.0 - disc_gym / 100.0)
        except ValueError:
            gym_bill = 0.0
            
        trainer_bill = 0.0
        if self.cb_trainer_req.get() == "Yes":
            try:
                base_t = float(self.ent_trainer_fees.get() or 0.0)
                disc_t = float(self.ent_trainer_disc.get() or 0.0)
                trainer_bill = base_t * (1.0 - disc_t / 100.0)
            except ValueError:
                trainer_bill = 0.0
                
        currency = self.parent.settings.get("currency", "Rs.")
        self.lbl_calc_gym.config(text=f"Gym Billing: {currency}{gym_bill:,.2f}")
        self.lbl_calc_trainer.config(text=f"Trainer Billing: {currency}{trainer_bill:,.2f}")
        self.lbl_calc_total.config(text=f"Net Amount: {currency}{(gym_bill + trainer_bill):,.2f}")
        
    def load_member_fields(self):
        m = get_member_details(self.member_id)
        if not m: return
        self.ent_name.insert(0, m["Name"])
        self.ent_contact.insert(0, m["Contact"])
        self.cb_plan.set(m["Plan Type"])
        self.ent_start.delete(0, tk.END)
        self.ent_start.insert(0, db_to_ui_date(m["Start Date"]))
        self.ent_base_fees.delete(0, tk.END)
        self.ent_base_fees.insert(0, str(m["Base Fees"]))
        self.ent_discount.delete(0, tk.END)
        self.ent_discount.insert(0, str(m["Discount (%)"]))
        
        if m["Photo Path"]:
            self.photo_path = os.path.join(get_project_base_dir(), m["Photo Path"])
            self.lbl_photo_status.config(text="Has Photo", fg=SUCCESS)
            
        self.cb_trainer_req.set(m["Trainer Required"])
        self.toggle_trainer_fields()
        
        if m["Trainer Required"] == "Yes":
            self.cb_trainer_select.set(m["Trainer ID"])
            self.ent_trainer_fees.delete(0, tk.END)
            self.ent_trainer_fees.insert(0, str(m["Trainer Fees"]))
            self.ent_trainer_disc.delete(0, tk.END)
            self.ent_trainer_disc.insert(0, str(m["Trainer Discount (%)"]))
        self.update_fee_previews()
        
    def save_record(self):
        name = self.ent_name.get().strip()
        contact = self.ent_contact.get().strip()
        plan = self.cb_plan.get()
        start_date = self.ent_start.get().strip()
        start_date_db = ui_to_db_date(start_date)
        
        if not name or not contact or not start_date:
            messagebox.showerror("Validation Error", "Please fill in all basic fields.")
            return
            
        try:
            datetime.strptime(start_date_db, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid Start Date format. Use DD-MM-YYYY.")
            return
            
        try:
            gym_fees = float(self.ent_base_fees.get())
            gym_disc = float(self.ent_discount.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Gym fees and Discount must be numbers.")
            return
            
        trainer_req = self.cb_trainer_req.get()
        t_id, t_name, t_fees, t_disc = "", "", 0.0, 0.0
        
        if trainer_req == "Yes":
            t_id = self.cb_trainer_select.get()
            if not t_id:
                messagebox.showerror("Validation Error", "Please select a Trainer.")
                return
            t_name = self.trainer_dict[t_id][0]
            try:
                t_fees = float(self.ent_trainer_fees.get())
                t_disc = float(self.ent_trainer_disc.get())
            except ValueError:
                messagebox.showerror("Validation Error", "Trainer Fees and Discount must be numbers.")
                return
                
        if self.mode == "add":
            # Call modified validation blocks (Requirement 4)
            success, result_val = add_member(
                name=name, contact=contact, plan_type=plan, start_date=start_date_db, base_fees=gym_fees, discount_pct=gym_disc,
                trainer_required=trainer_req, trainer_id=t_id, trainer_name=t_name, trainer_fees=t_fees, trainer_discount_pct=t_disc,
                photo_path=self.photo_path
            )
            
            if not success:
                # Flash error warning duplicate matching keys (Requirement 4)
                messagebox.showerror("Duplicate Roster Block", result_val)
                return
                
            m_id = result_val
            final_gym_fees = gym_fees * (1 - gym_disc / 100.0)
            final_t_fees = t_fees * (1 - t_disc / 100.0) if trainer_req == "Yes" else 0.0
            
            # Log initial setup payments ledger
            p_success, p_msg = record_payment(m_id, final_gym_fees + final_t_fees, "Initial Setup", notes=f"Gym plan: {plan} + Trainer: {t_name}", payment_date=start_date_db)
            
            # Extract PDF receipt path and auto display (Requirement 2 & 3)
            receipt_path = ""
            if "Receipt generated:" in p_msg:
                receipt_path = p_msg.split("Receipt generated:")[1].strip()
                
            if receipt_path and os.path.exists(receipt_path):
                try:
                    os.startfile(receipt_path)
                except Exception as ex:
                    print(f"Could not open PDF: {ex}")
                    
            messagebox.showinfo("Success", f"Member created with ID: {m_id}. PDF Receipt compiled.")
            
        else:
            update_kwargs = {
                "Name": name, "Contact": contact, "Plan Type": plan, "Start Date": start_date_db, "Base Fees": gym_fees, "Discount (%)": gym_disc,
                "Trainer Required": trainer_req, "Trainer ID": t_id, "Trainer Name": t_name, "Trainer Fees": t_fees, "Trainer Discount (%)": t_disc
            }
            if self.photo_path and not self.photo_path.startswith("data"):
                settings = load_settings()
                _, ext = os.path.splitext(self.photo_path)
                dest_filename = f"{self.member_id}{ext}"
                copied_photo_path = os.path.join(settings.get("photo_dir", "data/photos"), dest_filename)
                shutil.copy(self.photo_path, os.path.join(get_project_base_dir(), copied_photo_path))
                update_kwargs["Photo Path"] = copied_photo_path
                
            update_member(self.member_id, **update_kwargs)
            messagebox.showinfo("Success", f"Member {self.member_id} details updated.")
            
        self.parent.load_members_table()
        self.destroy() # Closes enroll popup immediately (Requirement 3)


class TrainerFormModal(tk.Toplevel):
    def __init__(self, parent, mode="add", trainer_id=None):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode
        self.trainer_id = trainer_id
        
        self.title("Add Trainer" if mode == "add" else f"Modify Trainer {trainer_id}")
        self.geometry("450x420")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.build_ui()
        if mode == "edit":
            self.load_trainer_fields()
            
    def build_ui(self):
        title_text = "✨ Enroll Fitness Coach" if self.mode == "add" else f"✏️ Edit Coach: {self.trainer_id}"
        tk.Label(self, text=title_text, font=("Segoe UI", 13, "bold"), fg=ACCENT, bg=BG_PRIMARY, pady=15).pack()
        
        form = tk.Frame(self, bg=BG_PRIMARY, padx=25)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        tk.Label(form, text="Full Name:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=0, column=0, sticky="w", pady=8)
        self.ent_name = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER)
        self.ent_name.grid(row=0, column=1, sticky="ew", pady=8, ipady=4)
        
        tk.Label(form, text="Contact No:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=1, column=0, sticky="w", pady=8)
        self.ent_contact = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER)
        self.ent_contact.grid(row=1, column=1, sticky="ew", pady=8, ipady=4)
        
        tk.Label(form, text="Specialty (e.g. HIIT, Yoga):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=2, column=0, sticky="w", pady=8)
        self.ent_specialty = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER)
        self.ent_specialty.grid(row=2, column=1, sticky="ew", pady=8, ipady=4)
        
        tk.Label(form, text="Base Monthly Fees:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=3, column=0, sticky="w", pady=8)
        self.ent_fees = tk.Entry(form, bg=BG_SECONDARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER)
        self.ent_fees.grid(row=3, column=1, sticky="ew", pady=8, ipady=4)
        self.ent_fees.insert(0, "2000")
        
        tk.Label(form, text="Status:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=4, column=0, sticky="w", pady=8)
        self.cb_status = ttk.Combobox(form, values=["Active", "Inactive"], state="readonly")
        self.cb_status.grid(row=4, column=1, sticky="ew", pady=8)
        self.cb_status.set("Active")
        
        btn_action = tk.Button(self, text="Save Coach Record", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=10, command=self.save_record)
        btn_action.pack(fill="x", side="bottom", padx=25, pady=25)
        
    def load_trainer_fields(self):
        df = load_dataframe("trainers.xlsx")
        trainer = df[df["Trainer ID"] == self.trainer_id]
        if not trainer.empty:
            t = trainer.iloc[0]
            self.ent_name.insert(0, t["Name"])
            self.ent_contact.insert(0, t["Contact"])
            self.ent_specialty.insert(0, t["Specialty"])
            self.ent_fees.delete(0, tk.END)
            self.ent_fees.insert(0, str(t["Base Fees"]))
            self.cb_status.set(t["Status"])
            
    def save_record(self):
        name = self.ent_name.get().strip()
        contact = self.ent_contact.get().strip()
        specialty = self.ent_specialty.get().strip()
        
        if not name or not contact or not specialty:
            messagebox.showerror("Validation Error", "Please fill in all details.")
            return
            
        try:
            fees = float(self.ent_fees.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Monthly fees must be a number.")
            return
            
        status = self.cb_status.get()
        if self.mode == "add":
            t_id = add_trainer(name, contact, specialty, fees)
            messagebox.showinfo("Success", f"Coach enrolled with ID: {t_id}")
        else:
            update_trainer(self.trainer_id, Name=name, Contact=contact, Specialty=specialty, Status=status, **{"Base Fees": fees})
            messagebox.showinfo("Success", f"Coach {self.trainer_id} details updated.")
        self.parent.load_trainers_table()
        self.destroy()


class ReallocateTrainerModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Reallocate Members to Coach")
        self.geometry("450x300")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.trainer_ids = []
        self.load_trainers()
        self.build_ui()
        
    def load_trainers(self):
        df = load_dataframe("trainers.xlsx")
        if not df.empty:
            self.trainer_ids = df[df["Status"] == "Active"]["Trainer ID"].tolist()
            
    def build_ui(self):
        tk.Label(self, text="🔄 Transfer Trainees to New Coach", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_PRIMARY, pady=15).pack()
        form = tk.Frame(self, bg=BG_PRIMARY, padx=25)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        tk.Label(form, text="From Coach (Current):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=0, column=0, sticky="w", pady=10)
        self.cb_from = ttk.Combobox(form, values=self.trainer_ids, state="readonly")
        self.cb_from.grid(row=0, column=1, sticky="ew", pady=10)
        
        tk.Label(form, text="To Coach (Target):", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=1, column=0, sticky="w", pady=10)
        self.cb_to = ttk.Combobox(form, values=self.trainer_ids, state="readonly")
        self.cb_to.grid(row=1, column=1, sticky="ew", pady=10)
        
        btn_action = tk.Button(self, text="⚡ Reassign Members Now", font=("Segoe UI", 10, "bold"), bg=ALERT, fg=BG_SECONDARY, bd=0, pady=10, command=self.save_reallocation)
        btn_action.pack(fill="x", side="bottom", padx=25, pady=25)
        
    def save_reallocation(self):
        t_from = self.cb_from.get()
        t_to = self.cb_to.get()
        if not t_from or not t_to:
            messagebox.showerror("Error", "Select coaches.")
            return
        if t_from == t_to:
            messagebox.showerror("Error", "Coaches must be different.")
            return
        success, msg = reassign_members(t_from, t_to)
        if success:
            messagebox.showinfo("Success", msg)
            self.parent.load_trainers_table()
            self.destroy()
        else:
            messagebox.showerror("Failed", msg)


class AssignPlanModal(tk.Toplevel):
    def __init__(self, parent, member_id):
        super().__init__(parent)
        self.parent = parent
        self.member_id = member_id
        
        self.title("Assign Workout & Diet Programs")
        self.geometry("500x420")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.workout_dict = {}
        self.diet_dict = {}
        self.load_options()
        self.build_ui()
        
    def load_options(self):
        for w in get_workout_templates():
            self.workout_dict[w["Plan Name"]] = w["Plan ID"]
        for d in get_diet_templates():
            self.diet_dict[d["Plan Name"]] = d["Diet ID"]
            
    def build_ui(self):
        tk.Label(self, text=f"📋 Prescribe Planners: {self.member_id}", font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_PRIMARY, pady=15).pack()
        form = tk.Frame(self, bg=BG_PRIMARY, padx=25)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        tk.Label(form, text="Prescribe Workout Plan:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=0, column=0, sticky="w", pady=10)
        self.cb_workout = ttk.Combobox(form, values=list(self.workout_dict.keys()), state="readonly")
        self.cb_workout.grid(row=0, column=1, sticky="ew", pady=10)
        
        tk.Label(form, text="Prescribe Diet Plan:", fg=TEXT_MUTED, bg=BG_PRIMARY).grid(row=1, column=0, sticky="w", pady=10)
        self.cb_diet = ttk.Combobox(form, values=list(self.diet_dict.keys()), state="readonly")
        self.cb_diet.grid(row=1, column=1, sticky="ew", pady=10)
        
        btn_action = tk.Button(self, text="💾 Save Assignments", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=10, command=self.save_assignments)
        btn_action.pack(fill="x", side="bottom", padx=25, pady=25)
        
    def save_assignments(self):
        w_selected = self.cb_workout.get()
        d_selected = self.cb_diet.get()
        assigned_any = False
        
        if w_selected:
            w_id = self.workout_dict[w_selected]
            success, msg = assign_plan_to_member(w_id, self.member_id)
            if success: assigned_any = True
        if d_selected:
            d_id = self.diet_dict[d_selected]
            success, msg = assign_diet_to_member(d_id, self.member_id)
            if success: assigned_any = True
            
        if assigned_any:
            messagebox.showinfo("Saved", "Plans prescribed successfully.")
            if hasattr(self.parent, "load_member_prescriptions_table"):
                self.parent.load_member_prescriptions_table()
            self.destroy()
        else:
            messagebox.showerror("Error", "Please select a workout or diet plan template.")


class FitnessTrackerModal(tk.Toplevel):
    def __init__(self, parent, member_id):
        super().__init__(parent)
        self.parent = parent
        self.member_id = member_id
        
        self.title("Fitness & BMI Analytics")
        self.geometry("700x550")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.build_ui()
        self.load_history()
        
    def build_ui(self):
        header_frame = tk.Frame(self, bg=BG_PRIMARY, pady=10)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text=f"💪 BMI & Measurement Log: {self.member_id}", font=("Segoe UI", 13, "bold"), fg=ACCENT, bg=BG_PRIMARY).pack()
        
        main_split = tk.Frame(self, bg=BG_PRIMARY, padx=15)
        main_split.pack(fill="both", expand=True)
        
        left_side = tk.Frame(main_split, bg=BG_SECONDARY, padx=15, pady=15, highlightbackground=CARD_BORDER, highlightthickness=1)
        left_side.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_side = tk.Frame(main_split, bg=BG_SECONDARY, padx=15, pady=15, highlightbackground=CARD_BORDER, highlightthickness=1)
        right_side.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        tk.Label(left_side, text="Add Daily Entry", font=("Segoe UI", 11, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
        
        fields = [
            ("Weight (kg):", "ent_weight", "70"),
            ("Height (cm):", "ent_height", "175"),
            ("Chest (in):", "ent_chest", ""),
            ("Waist (in):", "ent_waist", ""),
            ("Hips (in):", "ent_hips", ""),
            ("Biceps (in):", "ent_biceps", "")
        ]
        
        self.form_entries = {}
        for label, var_name, default in fields:
            row = tk.Frame(left_side, bg=BG_SECONDARY)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, fg=TEXT_MUTED, bg=BG_SECONDARY, width=12, anchor="w").pack(side="left")
            entry = tk.Entry(row, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, bd=1, highlightbackground=CARD_BORDER, width=10)
            entry.pack(side="right", fill="x", expand=True, ipady=2)
            if default: entry.insert(0, default)
            self.form_entries[var_name] = entry
            
        btn_calc = tk.Button(left_side, text="📊 Save & Calculate BMI", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, pady=8, command=self.save_measurement)
        btn_calc.pack(fill="x", pady=(15, 0))
        
        canvas_div = tk.Canvas(left_side, height=1, bg=CARD_BORDER, highlightthickness=0)
        canvas_div.pack(fill="x", pady=10)
        tk.Label(left_side, text="Prescribed Routines:", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w")
        
        self.lbl_workout_pres = tk.Label(left_side, text="Workout: Loading...", fg=TEXT_MAIN, bg=BG_SECONDARY, font=("Segoe UI", 8), justify="left", wraplength=180)
        self.lbl_workout_pres.pack(anchor="w", pady=2)
        self.lbl_diet_pres = tk.Label(left_side, text="Diet: Loading...", fg=TEXT_MAIN, bg=BG_SECONDARY, font=("Segoe UI", 8), justify="left", wraplength=180)
        self.lbl_diet_pres.pack(anchor="w", pady=2)
        self.load_member_prescriptions()
        
        # history list
        tk.Label(right_side, text="Logs History", font=("Segoe UI", 11, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 10))
        
        self.hist_tree = ttk.Treeview(right_side, columns=("Date", "Wt", "Ht", "BMI"), show="headings", height=8)
        self.hist_tree.heading("Date", text="Date")
        self.hist_tree.heading("Wt", text="Wt (kg)")
        self.hist_tree.heading("Ht", text="Ht (cm)")
        self.hist_tree.heading("BMI", text="BMI")
        self.hist_tree.column("Date", width=90, anchor="center")
        self.hist_tree.column("Wt", width=60, anchor="center")
        self.hist_tree.column("Ht", width=60, anchor="center")
        self.hist_tree.column("BMI", width=60, anchor="center")
        self.hist_tree.pack(fill="both", expand=True)
        
        self.lbl_bmi_cat = tk.Label(right_side, text="BMI Index Classification: --", font=("Segoe UI", 9, "bold"), fg=TEXT_MUTED, bg=BG_SECONDARY)
        self.lbl_bmi_cat.pack(anchor="w", pady=(10, 0))
        
    def load_member_prescriptions(self):
        w_df = load_dataframe("workout_plans.xlsx")
        w_p = w_df[w_df["Member ID"] == self.member_id]
        w_text = w_p.iloc[0]["Plan Name"] if not w_p.empty else "None Assigned"
        self.lbl_workout_pres.config(text=f"🏋️ Workout: {w_text}")
        
        d_df = load_dataframe("diet_plans.xlsx")
        d_p = d_df[d_df["Member ID"] == self.member_id]
        d_text = d_p.iloc[0]["Plan Name"] if not d_p.empty else "None Prescribed"
        self.lbl_diet_pres.config(text=f"🍎 Diet: {d_text}")
        
    def load_history(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        history = get_member_measurements(self.member_id)
        for h in history:
            self.hist_tree.insert("", "end", values=(h["Date"], h["Weight (kg)"], h["Height (cm)"], h["BMI"]))
            
        if history:
            bmi = history[-1]["BMI"]
            if bmi < 18.5:
                cat, color = "Underweight", "#2563EB"
            elif bmi < 24.9:
                cat, color = "Healthy Weight", SUCCESS
            elif bmi < 29.9:
                cat, color = "Overweight", "#D97706"
            else:
                cat, color = "Obese", ALERT
            self.lbl_bmi_cat.config(text=f"Latest BMI Category: {cat} ({bmi})", fg=color)
            
    def save_measurement(self):
        try:
            wt = float(self.form_entries["ent_weight"].get())
            ht = float(self.form_entries["ent_height"].get())
        except ValueError:
            messagebox.showerror("Error", "Weight and Height are required inputs.")
            return
            
        chest = self.form_entries["ent_chest"].get()
        waist = self.form_entries["ent_waist"].get()
        hips = self.form_entries["ent_hips"].get()
        biceps = self.form_entries["ent_biceps"].get()
        
        mea_id, bmi = add_measurement(self.member_id, wt, ht, chest, waist, hips, biceps)
        messagebox.showinfo("Success", f"Measurement recorded! BMI: {bmi}")
        self.load_history()


class TemplateFormModal(tk.Toplevel):
    def __init__(self, parent, type_name, mode, template_data=None):
        super().__init__(parent)
        self.parent = parent
        self.type_name = type_name # "workout" or "diet"
        self.mode = mode # "add" or "edit"
        self.template_data = template_data
        
        self.title(f"{'Add' if mode == 'add' else 'Edit/Amend'} {type_name.capitalize()} Template")
        self.geometry("500x380")
        self.configure(bg=BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        
        # Center window
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        extra_w = (self.winfo_screenwidth() - w) // 2
        extra_h = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{extra_w}+{extra_h}")
        
        # UI Setup
        panel = tk.Frame(self, bg=BG_SECONDARY, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=20)
        panel.pack(fill="both", expand=True, padx=15, pady=15)
        
        tk.Label(panel, text=f"{'Create New' if mode == 'add' else 'Edit Existing'} {type_name.capitalize()} Template", 
                 font=("Segoe UI", 12, "bold"), fg=ACCENT, bg=BG_SECONDARY).pack(anchor="w", pady=(0, 15))
        
        # Name Entry
        tk.Label(panel, text="Plan Name:", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w")
        self.ent_name = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_name.pack(fill="x", pady=(2, 10), ipady=5)
        
        # Target/Goal Entry
        tk.Label(panel, text="Target/Goal:", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w")
        self.ent_target = tk.Entry(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER)
        self.ent_target.pack(fill="x", pady=(2, 10), ipady=5)
        
        # Details entry
        tk.Label(panel, text="Details / Instructions:", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w")
        self.txt_details = tk.Text(panel, bg=BG_PRIMARY, fg=TEXT_MAIN, insertbackground=CURSOR_COLOR, insertwidth=3, font=("Segoe UI", 10), bd=1, highlightbackground=CARD_BORDER, height=5)
        self.txt_details.pack(fill="both", expand=True, pady=(2, 15))
        
        # Pre-fill if edit
        if mode == "edit" and template_data:
            self.ent_name.insert(0, template_data.get("Plan Name", ""))
            self.ent_target.insert(0, template_data.get("Target/Goal", ""))
            self.txt_details.insert("1.0", template_data.get("Details", ""))
            
        # Action Buttons
        btn_box = tk.Frame(panel, bg=BG_SECONDARY)
        btn_box.pack(fill="x")
        
        btn_save = tk.Button(btn_box, text="💾 Save Template", font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=BG_SECONDARY, bd=0, padx=15, pady=6, cursor="hand2", command=self.save_template)
        btn_save.pack(side="left")
        
        btn_cancel = tk.Button(btn_box, text="Cancel", font=("Segoe UI", 10, "bold"), bg=BG_PRIMARY, fg=TEXT_MAIN, bd=1, highlightbackground=CARD_BORDER, padx=15, pady=5, cursor="hand2", command=self.destroy)
        btn_cancel.pack(side="right")
        
    def save_template(self):
        name = self.ent_name.get().strip()
        target = self.ent_target.get().strip()
        details = self.txt_details.get("1.0", tk.END).strip()
        
        if not name or not target or not details:
            messagebox.showerror("Error", "All fields are required to save a template.")
            return
            
        if self.type_name == "workout":
            if self.mode == "add":
                add_workout_plan(name, target, details, member_id="")
                messagebox.showinfo("Success", "Workout template created successfully.")
            else:
                plan_id = self.template_data["Plan ID"]
                update_workout_plan(plan_id, name, target, details)
                messagebox.showinfo("Success", "Workout template updated successfully.")
        else: # diet
            if self.mode == "add":
                add_diet_plan(name, target, details, member_id="")
                messagebox.showinfo("Success", "Diet template created successfully.")
            else:
                diet_id = self.template_data["Diet ID"]
                update_diet_plan(diet_id, name, target, details)
                messagebox.showinfo("Success", "Diet template updated successfully.")
                
        self.parent.load_libraries_listboxes()
        self.destroy()


if __name__ == "__main__":
    app = GymProApp()
    app.mainloop()
