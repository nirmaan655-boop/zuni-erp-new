import os
import sqlite3
import pandas as pd
from contextlib import contextmanager
from typing import Iterator, Optional

def get_db_path() -> str:
    # Live aur Local dono ke liye rasta
    project_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ["Zuni.db", "zuni.db"]:
        full_path = os.path.join(project_dir, name)
        if os.path.exists(full_path):
            return full_path
    return os.path.join(project_dir, "Zuni.db")

@contextmanager
def db_connect() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn) # Missing tables khud banayega
        yield conn
    finally:
        conn.close()

def fetch_df(conn: sqlite3.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, conn, params=params)

def init_db(conn: sqlite3.Connection) -> None:
    # Aapke purane 350 rows ka logic yahan mehfooz hai
    tables = [
        "CREATE TABLE IF NOT EXISTS Staff (StaffID INTEGER PRIMARY KEY AUTOINCREMENT, StaffName TEXT, MonthlySalary REAL, Status TEXT DEFAULT 'Active');",
        "CREATE TABLE IF NOT EXISTS AnimalMaster (ID INTEGER PRIMARY KEY AUTOINCREMENT, Category TEXT, Breed TEXT, Status TEXT);",
        "CREATE TABLE IF NOT EXISTS ChartOfAccounts (AccountID INTEGER PRIMARY KEY AUTOINCREMENT, AccountName TEXT, AccountType TEXT, Balance REAL DEFAULT 0);",
        "CREATE TABLE IF NOT EXISTS Transactions (TransactionID INTEGER PRIMARY KEY AUTOINCREMENT, Date DATE, AccountName TEXT, PayeeName TEXT, Description TEXT, Debit REAL DEFAULT 0, Credit REAL DEFAULT 0);",
        "CREATE TABLE IF NOT EXISTS VendorMaster (VendorID INTEGER PRIMARY KEY AUTOINCREMENT, VendorName TEXT, ContactNo TEXT);",
        "CREATE TABLE IF NOT EXISTS MilkSales (MilkSaleID INTEGER PRIMARY KEY AUTOINCREMENT, SaleDate DATE, Liters REAL, Amount REAL);"
    ]
    for q in tables:
        conn.execute(q)
    conn.commit()
