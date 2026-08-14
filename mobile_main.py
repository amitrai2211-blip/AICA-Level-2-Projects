import os
import sys

# Ensure Kivy does not crash on older systems by configuration
os.environ['KIVY_NO_ARGS'] = '1'

import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from datetime import datetime

# Import modules
from modules.config import load_settings, save_settings, get_current_year_string
from modules.database import initialize_database, load_dataframe
from modules.members import add_member, get_member_details, get_reminders, check_and_update_statuses
from modules.trainers import add_trainer, get_trainer_members
from modules.attendance import check_in_member, get_today_checkins
from modules.payments import record_payment, get_financial_summary

class ModernScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.07, 0.07, 0.08, 1)  # Dark Background: #121214
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_rect, pos=self.update_rect)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def add_top_bar(self, layout, title_text, go_back=True):
        top_bar = BoxLayout(size_hint_y=None, height=60)
        with top_bar.canvas.before:
            Color(0.09, 0.09, 0.11, 1)  # #18181b
            self.bar_rect = Rectangle(size=top_bar.size, pos=top_bar.pos)
        top_bar.bind(size=self.update_bar_rect, pos=self.update_bar_rect)
        
        if go_back:
            btn_back = Button(text="< Back", size_hint_x=None, width=80, 
                              background_normal='', background_color=(0.12, 0.12, 0.14, 1),
                              color=(0.02, 0.71, 0.83, 1), font_name="Roboto")
            btn_back.bind(on_release=lambda x: self.go_to_dashboard())
            top_bar.add_widget(btn_back)
            
        title_lbl = Label(text=title_text, font_size=20, bold=True, color=(0.9, 0.9, 0.9, 1), halign="center")
        top_bar.add_widget(title_lbl)
        
        # Spacer for centering title if back button is present
        if go_back:
            top_bar.add_widget(Label(size_hint_x=None, width=80))
            
        layout.add_widget(top_bar)

    def update_bar_rect(self, instance, value):
        self.bar_rect.pos = instance.pos
        self.bar_rect.size = instance.size

    def go_to_dashboard(self):
        self.manager.current = "dashboard"


class DashboardScreen(ModernScreen):
    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        self.add_top_bar(layout, "💪 GYM PRO+ Mobile", go_back=False)
        
        # Load Stats
        initialize_database()
        check_and_update_statuses()
        
        m_df = load_dataframe("members.xlsx")
        t_df = load_dataframe("trainers.xlsx")
        att_today = get_today_checkins()
        
        total_m = len(m_df)
        active_m = len(m_df[m_df["Status"] == "Active"]) if total_m > 0 else 0
        active_t = len(t_df[t_df["Status"] == "Active"]) if len(t_df) > 0 else 0
        today_att = len(att_today)
        
        # Stats Display Panel
        stats_grid = GridLayout(cols=2, size_hint_y=None, height=180, padding=10, spacing=10)
        
        stats = [
            ("Active Members", f"{active_m} / {total_m}", (0.02, 0.71, 0.83, 1)),
            ("Check-Ins Today", str(today_att), (0.06, 0.72, 0.50, 1)),
            ("Active Coaches", str(active_t), (0.66, 0.33, 0.97, 1)),
            ("Reminders", str(len(get_reminders(7))), (0.93, 0.27, 0.27, 1))
        ]
        
        for title, val, color in stats:
            box = BoxLayout(orientation="vertical", padding=10)
            with box.canvas.before:
                Color(0.12, 0.12, 0.14, 1)  # Card BG: #1e1e24
                box.rect = Rectangle(size=box.size, pos=box.pos)
            box.bind(size=self.update_card_rect, pos=self.update_card_rect)
            
            box.add_widget(Label(text=title, font_size=12, color=(0.6, 0.6, 0.6, 1)))
            box.add_widget(Label(text=val, font_size=20, bold=True, color=color))
            stats_grid.add_widget(box)
            
        layout.add_widget(stats_grid)
        
        # Navigation Menu List
        menu_scroll = ScrollView()
        menu_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
        menu_layout.bind(minimum_height=menu_layout.setter('height'))
        
        menu_buttons = [
            ("👥 Member Management", "members"),
            ("🤝 Trainer Directory", "trainers"),
            ("📅 Attendance Console", "attendance"),
            ("💳 Bills & Payments", "payments")
        ]
        
        for label, screen_name in menu_buttons:
            btn = Button(text=label, size_hint_y=None, height=60, font_size=16,
                         background_normal='', background_color=(0.12, 0.12, 0.14, 1),
                         color=(0.9, 0.9, 0.9, 1))
            btn.bind(on_release=lambda x, sn=screen_name: self.change_screen(sn))
            menu_layout.add_widget(btn)
            
        menu_scroll.add_widget(menu_layout)
        layout.add_widget(menu_scroll)
        self.add_widget(layout)

    def update_card_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

    def change_screen(self, screen_name):
        self.manager.current = screen_name


class MembersScreen(ModernScreen):
    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        self.add_top_bar(layout, "Members Directory")
        
        # Add Member Button
        btn_add = Button(text="+ Enroll New Member", size_hint_y=None, height=50, bold=True,
                         background_normal='', background_color=(0.02, 0.71, 0.83, 1), color=(0.07, 0.07, 0.08, 1))
        btn_add.bind(on_release=self.show_enroll_popup)
        layout.add_widget(btn_add)
        
        # Members Scroll View
        scroll = ScrollView()
        list_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        df = load_dataframe("members.xlsx")
        if df.empty:
            list_layout.add_widget(Label(text="No gym members registered yet.", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=50))
        else:
            for _, row in df.iterrows():
                row_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=70, padding=10)
                with row_box.canvas.before:
                    Color(0.12, 0.12, 0.14, 1)
                    row_box.rect = Rectangle(size=row_box.size, pos=row_box.pos)
                row_box.bind(size=self.update_card_rect, pos=self.update_card_rect)
                
                details = BoxLayout(orientation="vertical")
                status_color = "[color=10b981]Active[/color]" if row["Status"] == "Active" else "[color=ef4444]Expired[/color]"
                details.add_widget(Label(text=f"{row['Name']} ({row['Member ID']})", markup=True, bold=True, halign="left", size_hint_x=1))
                details.add_widget(Label(text=f"Plan: {row['Plan Type']} | Status: {status_color}", markup=True, font_size=12))
                row_box.add_widget(details)
                
                # Check-in Quick Action
                btn_ci = Button(text="Check-In", size_hint_x=None, width=80,
                                background_normal='', background_color=(0.06, 0.72, 0.50, 1), color=(1, 1, 1, 1))
                btn_ci.bind(on_release=lambda x, mid=row["Member ID"]: self.quick_checkin(mid))
                row_box.add_widget(btn_ci)
                
                list_layout.add_widget(row_box)
                
        scroll.add_widget(list_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def update_card_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

    def quick_checkin(self, member_id):
        success, msg = check_in_member(member_id)
        popup = Popup(title="Check-In Result", size_hint=(0.85, 0.3))
        popup.content = Label(text=msg, halign="center")
        popup.open()

    def show_enroll_popup(self, instance):
        # Create full screen height scroll form for enrolling member
        content = BoxLayout(orientation="vertical", padding=15, spacing=10)
        
        name_in = TextInput(hint_text="Full Name", multiline=False, size_hint_y=None, height=45)
        contact_in = TextInput(hint_text="Contact Number", multiline=False, size_hint_y=None, height=45)
        
        # Simple inputs for numerical values
        base_fees_in = TextInput(hint_text="Base Gym Fees", text="1500", multiline=False, size_hint_y=None, height=45)
        
        content.add_widget(Label(text="Enroll New Gym Member", bold=True, size_hint_y=None, height=30))
        content.add_widget(name_in)
        content.add_widget(contact_in)
        content.add_widget(base_fees_in)
        
        popup = Popup(title="New Registration", content=content, size_hint=(0.9, 0.8))
        
        def register_member(btn):
            name = name_in.text.strip()
            contact = contact_in.text.strip()
            base_f = base_fees_in.text.strip()
            if not name or not contact or not base_f:
                return
            try:
                fees_val = float(base_f)
            except ValueError:
                return
                
            m_id = add_member(
                name=name, contact=contact, plan_type="Monthly", start_date=datetime.now().strftime("%Y-%m-%d"),
                base_fees=fees_val, discount_pct=0, trainer_required="No", trainer_id="", trainer_name="",
                trainer_fees=0, trainer_discount_pct=0, photo_path=""
            )
            # Log payment
            record_payment(m_id, fees_val, "Gym Fees", notes="Initial Payment")
            
            popup.dismiss()
            self.rebuild_ui()
            
        btn_submit = Button(text="Register Member", size_hint_y=None, height=50, background_color=(0.02, 0.71, 0.83, 1))
        btn_submit.bind(on_release=register_member)
        content.add_widget(btn_submit)
        
        popup.open()


class TrainersScreen(ModernScreen):
    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        self.add_top_bar(layout, "Coaches & Trainers")
        
        scroll = ScrollView()
        list_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        df = load_dataframe("trainers.xlsx")
        if df.empty:
            list_layout.add_widget(Label(text="No gym trainers registered yet.", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=50))
        else:
            for _, row in df.iterrows():
                row_box = BoxLayout(orientation="vertical", size_hint_y=None, height=80, padding=10)
                with row_box.canvas.before:
                    Color(0.12, 0.12, 0.14, 1)
                    row_box.rect = Rectangle(size=row_box.size, pos=row_box.pos)
                row_box.bind(size=self.update_card_rect, pos=self.update_card_rect)
                
                row_box.add_widget(Label(text=f"{row['Name']} ({row['Trainer ID']})", bold=True, size_hint_y=None, height=25))
                row_box.add_widget(Label(text=f"Specialty: {row['Specialty']} | Fees: Rs.{float(row['Base Fees']):.0f}", font_size=12, color=(0.6, 0.6, 0.6, 1)))
                list_layout.add_widget(row_box)
                
        scroll.add_widget(list_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def update_card_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size


class AttendanceScreen(ModernScreen):
    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        self.add_top_bar(layout, "Attendance Console")
        
        # Check-in Form Form
        input_frame = BoxLayout(orientation="vertical", size_hint_y=None, height=130, padding=15, spacing=10)
        self.m_id_input = TextInput(hint_text="Input Member ID (e.g. MEM1001)", multiline=False, size_hint_y=None, height=45)
        btn_ci = Button(text="Check-In", size_hint_y=None, height=45, bold=True,
                        background_normal='', background_color=(0.02, 0.71, 0.83, 1), color=(0.07, 0.07, 0.08, 1))
        btn_ci.bind(on_release=self.checkin_action)
        
        input_frame.add_widget(self.m_id_input)
        input_frame.add_widget(btn_ci)
        layout.add_widget(input_frame)
        
        # Today's Checkins List
        layout.add_widget(Label(text="Today's Logs", bold=True, size_hint_y=None, height=30))
        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=8)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)
        
        self.load_checkins()
        self.add_widget(layout)

    def load_checkins(self):
        self.list_layout.clear_widgets()
        checkins = get_today_checkins()
        if not checkins:
            self.list_layout.add_widget(Label(text="No check-ins today yet.", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=40))
        else:
            for c in checkins:
                lbl = Label(text=f"{c['Check-in Time']} - {c['Name']} ({c['Member ID']})", size_hint_y=None, height=35, color=(0.9, 0.9, 0.9, 1))
                self.list_layout.add_widget(lbl)

    def checkin_action(self, btn):
        m_id = self.m_id_input.text.strip().upper()
        if not m_id:
            return
            
        success, msg = check_in_member(m_id)
        popup = Popup(title="Check-In Status", size_hint=(0.8, 0.25))
        popup.content = Label(text=msg, halign="center")
        popup.open()
        
        self.m_id_input.text = ""
        self.load_checkins()


class PaymentsScreen(ModernScreen):
    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation="vertical")
        self.add_top_bar(layout, "Payments History")
        
        scroll = ScrollView()
        list_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10, spacing=10)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        
        df = load_dataframe("payments.xlsx")
        if df.empty:
            list_layout.add_widget(Label(text="No transactions recorded.", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=50))
        else:
            for _, row in df.iterrows():
                row_box = BoxLayout(orientation="vertical", size_hint_y=None, height=70, padding=8)
                with row_box.canvas.before:
                    Color(0.12, 0.12, 0.14, 1)
                    row_box.rect = Rectangle(size=row_box.size, pos=row_box.pos)
                row_box.bind(size=self.update_card_rect, pos=self.update_card_rect)
                
                row_box.add_widget(Label(text=f"{row['Member Name']} ({row['Member ID']}) - Rs.{float(row['Amount Paid']):.2f}", bold=True, size_hint_y=None, height=25))
                row_box.add_widget(Label(text=f"Date: {row['Payment Date']} | For: {row['Payment For']}", font_size=12, color=(0.6, 0.6, 0.6, 1)))
                list_layout.add_widget(row_box)
                
        scroll.add_widget(list_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def update_card_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size


class GymProMobileApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(MembersScreen(name="members"))
        sm.add_widget(TrainersScreen(name="trainers"))
        sm.add_widget(AttendanceScreen(name="attendance"))
        sm.add_widget(PaymentsScreen(name="payments"))
        return sm

if __name__ == "__main__":
    GymProMobileApp().run()
