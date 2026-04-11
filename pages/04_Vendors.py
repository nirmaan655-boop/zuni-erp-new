import sqlite3
import os
import pandas as pd

# =========================
# DB CONNECTION
# =========================
def db_connect():
    db_path = os.path.join(os.getcwd(), "zuni.db")
    return sqlite3.connect(db_path, check_same_thread=False)


# =========================
# INIT DATABASE (FULL ERP)
# =========================
def init_db():
    conn = db_connect()
    cursor = conn.cursor()

    # ================= COA =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS COA (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        parent_id INTEGER,
        is_group INTEGER DEFAULT 0
    )
    """)

    # ================= VENDOR =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Vendor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        coa_id INTEGER,
        opening_balance REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_DATE,
        FOREIGN KEY (coa_id) REFERENCES COA(id)
    )
    """)

    # ================= EMPLOYEE =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Employee (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        salary REAL DEFAULT 0,
        coa_id INTEGER,
        opening_balance REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_DATE,
        FOREIGN KEY (coa_id) REFERENCES COA(id)
    )
    """)

    # ================= CAO =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CAO (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        role TEXT DEFAULT 'Account Officer'
    )
    """)

    # ================= LEDGER =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coa_id INTEGER,
        date TEXT,
        description TEXT,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0
    )
    """)

    # ================= DEFAULT COA ACCOUNTS =================
    default_accounts = [
        ("Cash in Hand", "Asset"),
        ("Bank", "Asset"),
        ("Fixed Assets", "Asset"),
        ("Accounts Receivable", "Asset"),
        ("Accounts Payable", "Liability"),
        ("Capital", "Capital"),
        ("Expenses", "Expense"),
        ("Income", "Income")
    ]

    for name, type_ in default_accounts:
        cursor.execute("""
        INSERT OR IGNORE INTO COA (name, type)
        VALUES (?, ?)
        """, (name, type_))

    conn.commit()
    conn.close()


# =========================
# FETCH DATA
# =========================
def fetch_df(query, params=None):
    conn = db_connect()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# =========================
# VENDOR FUNCTIONS
# =========================
def add_vendor(name, phone, address, opening_balance=0):
    conn = db_connect()
    cursor = conn.cursor()

    # link vendor to Accounts Payable COA automatically
    cursor.execute("SELECT id FROM COA WHERE name='Accounts Payable'")
    coa = cursor.fetchone()

    coa_id = coa[0] if coa else None

    cursor.execute("""
    INSERT INTO Vendor (name, phone, address, coa_id, opening_balance)
    VALUES (?, ?, ?, ?, ?)
    """, (name, phone, address, coa_id, opening_balance))

    conn.commit()
    conn.close()


# =========================
# EMPLOYEE FUNCTIONS
# =========================
def add_employee(name, phone, address, salary=0, opening_balance=0):
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM COA WHERE name='Expenses'")
    coa = cursor.fetchone()

    coa_id = coa[0] if coa else None

    cursor.execute("""
    INSERT INTO Employee (name, phone, address, salary, coa_id, opening_balance)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, phone, address, salary, coa_id, opening_balance))

    conn.commit()
    conn.close()


# =========================
# CAO FUNCTIONS
# =========================
def add_cao(name, phone, role="Account Officer"):
    conn = db_connect()
    conn.execute("INSERT INTO CAO (name, phone, role) VALUES (?, ?, ?)",
                 (name, phone, role))
    conn.commit()
    conn.close()


# =========================
# REPORTS
# =========================
def vendor_report():
    query = """
    SELECT 
        v.name,
        v.phone,
        v.opening_balance,
        IFNULL(SUM(l.debit),0) AS debit,
        IFNULL(SUM(l.credit),0) AS credit
    FROM Vendor v
    LEFT JOIN Ledger l ON v.coa_id = l.coa_id
    GROUP BY v.id
    """
    return fetch_df(query)


def employee_report():
    query = """
    SELECT 
        name,
        salary,
        opening_balance
    FROM Employee
    """
    return fetch_df(query)
