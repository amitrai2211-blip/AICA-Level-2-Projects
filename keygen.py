import sys
from datetime import datetime
from modules.license import generate_signature

def main():
    print("==================================================")
    print("     GYM PRO+ ACTIVATION KEY GENERATOR TOOL       ")
    print("           Developed by CA Amit Rai               ")
    print("==================================================")
    
    mid = input("Enter Client Machine ID: ").strip().upper()
    if not mid:
        print("Error: Machine ID cannot be blank.")
        sys.exit(1)
        
    date_str = input("Enter Expiry Date (DD-MM-YYYY): ").strip()
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        expiry_db = dt.strftime("%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Use DD-MM-YYYY (e.g. 31-12-2027).")
        sys.exit(1)
        
    sig = generate_signature(mid, expiry_db)
    license_key = f"{mid}-{expiry_db}-{sig}"
    
    print("\n--------------------------------------------------")
    print("GENERATED ACTIVATION KEY:")
    print(license_key)
    print("--------------------------------------------------")
    print("Provide the above key to the client to activate their subscription.")

if __name__ == "__main__":
    main()
