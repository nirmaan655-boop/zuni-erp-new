import sqlite3
import os
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.getcwd(), "zuni.db")

# ================= AUTO-FIX ENGINE =================
def auto_repair_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # Sab tables ki list jo humein chahiye
    tables = {
        "AnimalMaster": "TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Status TEXT, Weight REAL, PurchasePrice REAL",
        "VendorMaster": "id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Phone TEXT, Address TEXT, Balance REAL DEFAULT 0",
        "BreedingLogs": "Date TEXT, TagID TEXT, Type TEXT, Semen TEXT, Vet TEXT, PD_Status TEXT, ExpectedCalving TEXT",
        "VaccineLogs": "Date TEXT, TagID TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT",
        "TreatmentLogs": "Date TEXT, TagID TEXT, Disease TEXT, Medicine TEXT, Status TEXT, Vet TEXT",
        "CalvingLogs": "Date TEXT, TagID TEXT, CalfGender TEXT, CalfWeight REAL, Sire TEXT",
        "MovementLogs": "Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT",
        "Staff": "id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Role TEXT, Salary REAL",
        "SalaryLogs": "Date TEXT, StaffName TEXT, AmountPaid REAL, Status TEXT",
        "Inventory": "ItemID INTEGER PRIMARY KEY AUTOINCREMENT, ItemName TEXT, Category TEXT, StockQty REAL, Unit TEXT",
        "SalesLogs": "id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, Item TEXT, Qty REAL, Amount REAL, Customer TEXT",
        "Transactions": "id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, Title TEXT, Type TEXT, Amount REAL"
    }

    for table_name, columns in tables.items():
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
    
    conn.commit()
    conn.close()

# ================= SMART DATABASE ACCESS =================
def db_connect():
    # Har baar connect hone se pehle check karega
    auto_repair_db() 
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def fetch_df(query, params=None):
    try:
        conn = db_connect()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        # Agar query fail ho (e.g. column missing), repair run karo aur empty DF do
        auto_repair_db()
        return pd.DataFrame()

def exec_q(query, params=()):
    try:
        conn = db_connect()
        conn.execute(query, params)
        conn.commit()
        conn.close()
    except Exception as e:
        auto_repair_db()
        st.error(f"Auto-Repair Triggered! Error: {e}")

# Database ko foran initialize karein
auto_repair_db()
