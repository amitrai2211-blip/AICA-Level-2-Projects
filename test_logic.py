import os
from modules.database import initialize_database, load_dataframe
from modules.members import get_reminders
from modules.backup import create_backup

def run_tests():
    print("Starting logical verification tests...")
    
    # 1. Initialize DB
    initialize_database()
    
    # 2. Check Member Loading
    df_m = load_dataframe("members.xlsx")
    print(f"Loaded {len(df_m)} members.")
    assert len(df_m) > 0, "Members list should not be empty after seeding."
    
    # 3. Check Reminders
    rems = get_reminders(7)
    print(f"Found {len(rems)} expiring memberships:")
    for r in rems:
        print(f" - {r['Name']} expiring in {r['Days Remaining']} days.")
        
    # 4. Check Backup
    success, zip_path = create_backup()
    print(f"Backup test: Success={success}, Path={zip_path}")
    assert success, "Backup archiving failed."
    assert os.path.exists(zip_path), "Backup archive ZIP file was not created physically."
    
    print("\nAll logical checks passed successfully!")

if __name__ == "__main__":
    run_tests()
