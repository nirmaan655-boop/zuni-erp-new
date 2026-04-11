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
# INIT DATABASE (AUTO CREATE ALL)
# ===============================
def init_db():
    conn = db_connect()
    cursor = conn.cursor()

    # ================= Vendors =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS VendorMaster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT
    )
    """)

    # ================= Animals =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Animals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT UNIQUE,
        breed TEXT,
        dob TEXT,
        status TEXT
    )
    """)

    # ================= Milk =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS MilkProduction (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER,
        date TEXT,
        milk_qty REAL,
        FOREIGN KEY (animal_id) REFERENCES Animals(id)
    )
    """)

    # ================= Feed =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Feed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        item TEXT,
        qty REAL,
        cost REAL
    )
    """)

    # ================= Purchase =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Purchase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        date TEXT,
        item TEXT,
        amount REAL,
        FOREIGN KEY (vendor_id) REFERENCES VendorMaster(id)
    )
    """)

    # ================= Payment =================
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
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# ===============================
# INSERT FUNCTIONS
# ===============================

def add_vendor(name, phone, address):
    conn = db_connect()
    conn.execute("INSERT INTO VendorMaster (name, phone, address) VALUES (?, ?, ?)", (name, phone, address))
    conn.commit()
    conn.close()


def add_animal(tag, breed, dob, status):
    conn = db_connect()
    conn.execute("INSERT INTO Animals (tag, breed, dob, status) VALUES (?, ?, ?, ?)", (tag, breed, dob, status))
    conn.commit()
    conn.close()


def add_milk(animal_id, date, milk_qty):
    conn = db_connect()
    conn.execute("INSERT INTO MilkProduction (animal_id, date, milk_qty) VALUES (?, ?, ?)", (animal_id, date, milk_qty))
    conn.commit()
    conn.close()


def add_feed(date, item, qty, cost):
    conn = db_connect()
    conn.execute("INSERT INTO Feed (date, item, qty, cost) VALUES (?, ?, ?, ?)", (date, item, qty, cost))
    conn.commit()
    conn.close()


def add_purchase(vendor_id, date, item, amount):
    conn = db_connect()
    conn.execute("INSERT INTO Purchase (vendor_id, date, item, amount) VALUES (?, ?, ?, ?)", (vendor_id, date, item, amount))
    conn.commit()
    conn.close()


def add_payment(vendor_id, date, amount):
    conn = db_connect()
    conn.execute("INSERT INTO Payment (vendor_id, date, amount) VALUES (?, ?, ?)", (vendor_id, date, amount))
    conn.commit()
    conn.close()


# ===============================
# REPORTS (NO EMPTY DATA ISSUE)
# ===============================

def vendor_report():
    query = """
    SELECT 
        v.name,
        IFNULL(SUM(pu.amount),0) AS purchase,
        IFNULL(SUM(py.amount),0) AS payment,
        IFNULL(SUM(pu.amount),0) - IFNULL(SUM(py.amount),0) AS balance
    FROM VendorMaster v
    LEFT JOIN Purchase pu ON v.id = pu.vendor_id
    LEFT JOIN Payment py ON v.id = py.vendor_id
    GROUP BY v.id
    """
    return fetch_df(query)


def milk_report():
    query = """
    SELECT 
        a.tag,
        SUM(m.milk_qty) AS total_milk
    FROM Animals a
    LEFT JOIN MilkProduction m ON a.id = m.animal_id
    GROUP BY a.id
    """
    return fetch_df(query)


def cash_in_hand():
    query = """
    SELECT 
        IFNULL((SELECT SUM(amount) FROM MilkProduction),0)
        - IFNULL((SELECT SUM(cost) FROM Feed),0)
        - IFNULL((SELECT SUM(amount) FROM Payment),0)
        AS cash
    """
    return fetch_df(query)
