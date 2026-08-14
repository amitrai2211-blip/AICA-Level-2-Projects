import os
import pandas as pd
from datetime import datetime, timedelta
from modules.config import get_data_dir, load_settings, save_settings
from modules.database import initialize_database, save_dataframe

def seed_sample_data():
    # 1. Ensure databases exist
    initialize_database()
    
    settings = load_settings()
    current_year = settings.get("current_year", "FY_2026-27")
    
    # 2. Add Trainers
    trainers_data = [
        {"Trainer ID": "TRN1001", "Name": "Coach John Doe", "Contact": "9876543210", "Specialty": "Strength & Conditioning", "Base Fees": 2000.0, "Status": "Active"},
        {"Trainer ID": "TRN1002", "Name": "Coach Jane Smith", "Contact": "9876543211", "Specialty": "Yoga & Flexibility", "Base Fees": 1800.0, "Status": "Active"},
        {"Trainer ID": "TRN1003", "Name": "Coach Mike Tyson", "Contact": "9876543212", "Specialty": "Boxing & HIIT", "Base Fees": 2500.0, "Status": "Active"}
    ]
    df_trainers = pd.DataFrame(trainers_data)
    save_dataframe(df_trainers, "trainers.xlsx")
    
    # 3. Add Members
    today = datetime.now()
    members_data = [
        {
            "Member ID": "MEM1001",
            "Name": "Alice Johnson",
            "Contact": "9988776655",
            "Plan Type": "Monthly",
            "Start Date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
            "Expiry Date": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
            "Base Fees": 1500.0,
            "Discount (%)": 10.0,
            "Final Gym Fees": 1350.0,
            "Trainer Required": "No",
            "Trainer ID": "",
            "Trainer Fees": 0.0,
            "Trainer Discount (%)": 0.0,
            "Final Trainer Fees": 0.0,
            "Photo Path": "",
            "Status": "Active",
            "Date Added": (today - timedelta(days=5)).strftime("%Y-%m-%d")
        },
        {
            "Member ID": "MEM1002",
            "Name": "Bob Smith",
            "Contact": "9988776656",
            "Plan Type": "Quarterly",
            "Start Date": (today - timedelta(days=15)).strftime("%Y-%m-%d"),
            "Expiry Date": (today + timedelta(days=75)).strftime("%Y-%m-%d"),
            "Base Fees": 4000.0,
            "Discount (%)": 0.0,
            "Final Gym Fees": 4000.0,
            "Trainer Required": "Yes",
            "Trainer ID": "TRN1001",
            "Trainer Name": "Coach John Doe",
            "Trainer Fees": 2000.0,
            "Trainer Discount (%)": 5.0,
            "Final Trainer Fees": 1900.0,
            "Photo Path": "",
            "Status": "Active",
            "Date Added": (today - timedelta(days=15)).strftime("%Y-%m-%d")
        },
        {
            "Member ID": "MEM1003",
            "Name": "Diana Prince",
            "Contact": "9988776657",
            "Plan Type": "Monthly",
            "Start Date": (today - timedelta(days=28)).strftime("%Y-%m-%d"),
            "Expiry Date": (today + timedelta(days=2)).strftime("%Y-%m-%d"), # Expiring soon!
            "Base Fees": 1500.0,
            "Discount (%)": 0.0,
            "Final Gym Fees": 1500.0,
            "Trainer Required": "No",
            "Trainer ID": "",
            "Trainer Fees": 0.0,
            "Trainer Discount (%)": 0.0,
            "Final Trainer Fees": 0.0,
            "Photo Path": "",
            "Status": "Active",
            "Date Added": (today - timedelta(days=28)).strftime("%Y-%m-%d")
        }
    ]
    df_members = pd.DataFrame(members_data)
    save_dataframe(df_members, "members.xlsx")
    
    # 4. Add Payments
    payments_data = [
        {"Payment ID": "PAY1001", "Member ID": "MEM1001", "Member Name": "Alice Johnson", "Amount Paid": 1350.0, "Payment Date": (today - timedelta(days=5)).strftime("%Y-%m-%d"), "Payment For": "Gym Fees", "Year/FY": current_year, "Notes": "Initial payment"},
        {"Payment ID": "PAY1002", "Member ID": "MEM1002", "Member Name": "Bob Smith", "Amount Paid": 4000.0, "Payment Date": (today - timedelta(days=15)).strftime("%Y-%m-%d"), "Payment For": "Gym Fees", "Year/FY": current_year, "Notes": "Quarterly Plan Gym Fees"},
        {"Payment ID": "PAY1003", "Member ID": "MEM1002", "Member Name": "Bob Smith", "Amount Paid": 1900.0, "Payment Date": (today - timedelta(days=15)).strftime("%Y-%m-%d"), "Payment For": "Trainer Fees", "Year/FY": current_year, "Notes": "Coach John Doe Fees"},
        {"Payment ID": "PAY1004", "Member ID": "MEM1003", "Member Name": "Diana Prince", "Amount Paid": 1500.0, "Payment Date": (today - timedelta(days=28)).strftime("%Y-%m-%d"), "Payment For": "Gym Fees", "Year/FY": current_year, "Notes": "Monthly payment"}
    ]
    df_payments = pd.DataFrame(payments_data)
    save_dataframe(df_payments, "payments.xlsx")
    
    # 5. Add Attendance
    attendance_data = [
        {"Attendance ID": "ATT1001", "Member ID": "MEM1001", "Name": "Alice Johnson", "Check-in Date": today.strftime("%Y-%m-%d"), "Check-in Time": "08:15:30"},
        {"Attendance ID": "ATT1002", "Member ID": "MEM1002", "Name": "Bob Smith", "Check-in Date": today.strftime("%Y-%m-%d"), "Check-in Time": "09:02:11"},
        {"Attendance ID": "ATT1003", "Member ID": "MEM1001", "Name": "Alice Johnson", "Check-in Date": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "Check-in Time": "08:12:45"},
        {"Attendance ID": "ATT1004", "Member ID": "MEM1003", "Name": "Diana Prince", "Check-in Date": (today - timedelta(days=1)).strftime("%Y-%m-%d"), "Check-in Time": "18:30:00"}
    ]
    df_attendance = pd.DataFrame(attendance_data)
    save_dataframe(df_attendance, "attendance.xlsx")
    
    print("Sample data seeded successfully into active dataset.")

if __name__ == "__main__":
    seed_sample_data()
