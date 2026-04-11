import sqlite3
import os
import pandas as pd

# ===============================
# DATABASE CONNECTION
# ===============================
def db_connect():
    db_path = os.path.join(os.getcwd(), "zuni.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


# ===============================
# AUTO CREATE TABLES (VERY IMPORTANT)
# ===============================
def init_db():
    conn = db_connect()
    cursor = conn.cursor()

    # Vendor Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS VendorMaster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT
    )
    """)

    # Purchase Table (LINKED)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Purchase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        date TEXT,
        amount REAL,
        FOREIGN KEY (vendor_id) REFERENCES VendorMaster(id)
    )
    """)

    # Payment Table (LINKED)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Payment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        date TEXT,
        amount REAL,
        FOREIGN KEY (vendor_id) REFERENCES VendorMaster(id)
    )
    """)

    conn.commit()
    conn.close()


# ===============================
# FETCH FUNCTION
# ===============================
def fetch_df(query, params=None):
    conn = db_connect()
    return pd.read_sql_query(query, conn, params=params)


# ===============================
# INSERT FUNCTIONS
# ===============================
def add_vendor(name, phone):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO VendorMaster (name, phone) VALUES (?, ?)", (name, phone))
    conn.commit()
    conn.close()


def add_purchase(vendor_id, date, amount):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Purchase (vendor_id, date, amount) VALUES (?, ?, ?)", (vendor_id, date, amount))
    conn.commit()
    conn.close()


def add_payment(vendor_id, date, amount):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Payment (vendor_id, date, amount) VALUES (?, ?, ?)", (vendor_id, date, amount))
    conn.commit()
    conn.close()


# ===============================
# REPORT (JOINED DATA)
# ===============================
def vendor_report():
    query = """
    SELECT 
        v.name,
        IFNULL(SUM(pu.amount),0) AS total_purchase,
        IFNULL(SUM(py.amount),0) AS total_payment,
        IFNULL(SUM(pu.amount),0) - IFNULL(SUM(py.amount),0) AS balance
    FROM VendorMaster v
    LEFT JOIN Purchase pu ON v.id = pu.vendor_id
    LEFT JOIN Payment py ON v.id = py.vendor_id
    GROUP BY v.id
    """
    return fetch_df(query)
