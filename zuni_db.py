import sqlite3
import os
import pandas as pd
import streamlit as st

# Standard Database Path
DB_PATH = os.path.join(os.getcwd(), "zuni.db")

# ================= AUTO-FIX & SYNC ENGINE =================
def auto_repair_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # 7 Modules ke liye exact tables aur columns ka map
    tables = {
        # 1. Livestock & Procurement
        "AnimalMaster": "TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Status TEXT, Weight REAL, PurchasePrice REAL, PurchaseDate TEXT",
        "BreedingLogs": "Date TEXT, TagID TEXT, Type TEXT, Semen TEXT, Vet TEXT, PD_Status TEXT, ExpectedCalving TEXT",
        "VaccineLogs": "Date TEXT, TagID TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT",
        "TreatmentLogs": "Date TEXT, TagID TEXT, Disease TEXT, Medicine TEXT, Status TEXT, Vet TEXT",
        "CalvingLogs": "Date TEXT, TagID TEXT, CalfGender TEXT, CalfWeight REAL, Sire TEXT",
        
        # 2. Master Setup & Vendors
        "VendorMaster": "VendorName TEXT PRIMARY KEY, ContactPerson TEXT, Phone TEXT, Address TEXT, Balance REAL DEFAULT 0",
        "EmployeeMaster": "Name TEXT PRIMARY KEY, CNIC TEXT, Phone TEXT, Designation TEXT, Salary REAL, LeaveAllowed INTEGER DEFAULT 2",
        
        # 3. Inventory & Feed
        "ItemMaster": "ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0, Store TEXT",
        "FeedRecipes": "PenID TEXT PRIMARY KEY, ItemName TEXT, QtyPerAnimal REAL, TotalAnimals INTEGER",
        
        # 4. Accounting & Sales
        "ChartOfAccounts": "AccountName TEXT PRIMARY KEY, AccountType TEXT, Balance REAL DEFAULT 0",
        "Transactions": "id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, AccountName TEXT, PayeeName TEXT, Description TEXT, Debit REAL, Credit REAL",
        "Sales": "SaleID INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, CustomerName TEXT, Category TEXT, ItemName TEXT, Qty REAL, UOM TEXT, Rate REAL, Total REAL, PaymentMode TEXT",
        
        # 5. Payroll
        "StaffLeaves": "id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, LeaveDate TEXT, Reason TEXT, Type TEXT",
        "SalaryHistory": "id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Month TEXT, Basic REAL, Bonus REAL, Deduction REAL, NetPaid REAL"
    }

    for table_name, columns in tables.items():
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
    
    conn.commit()
    conn.close()

# ================= SMART ACCESS FUNCTIONS =================
def db_connect():
    auto_repair_db() # Har connection se pehle check
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def fetch_df(conn_unused, query, params=()):
    """Aapki files 'conn' pass karti hain, hum yahan handle karte hain"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        auto_repair_db()
        return pd.DataFrame()

def exec_q(query, params=()):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e:
        auto_repair_db()
        st.error(f"Repairing Database... Please refresh. Error: {e}")

# Database initialization
auto_repair_db()
