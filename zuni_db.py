import sqlite3, os, pandas as pd

DB_PATH = os.path.join(os.getcwd(), "zuni.db")

def db_connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db_connect() as conn:
        # Livestock & Records
        conn.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Status TEXT, Weight REAL, PurchasePrice REAL, PurchaseDate TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS MilkProduction (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Type TEXT, Semen TEXT, Vet TEXT, PD_Status TEXT, ExpectedCalving TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Disease TEXT, Medicine TEXT, Vet TEXT, Status TEXT, TotalCost REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS VaccineLogs (Date TEXT, TagID TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS MovementLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")
        
        # Master Setup (Vendors & Employees)
        conn.execute("CREATE TABLE IF NOT EXISTS VendorMaster (VendorName TEXT PRIMARY KEY, ContactPerson TEXT, Phone TEXT, Address TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS EmployeeMaster (Name TEXT PRIMARY KEY, CNIC TEXT, Phone TEXT, Designation TEXT, Salary REAL, LeaveAllowed INTEGER DEFAULT 2)")
        
        # Inventory & Financials
        conn.execute("CREATE TABLE IF NOT EXISTS ItemMaster (ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0, Store TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS ChartOfAccounts (AccountName TEXT PRIMARY KEY, AccountType TEXT, Balance REAL DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS Transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, AccountName TEXT, PayeeName TEXT, Description TEXT, Debit REAL, Credit REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS Sales (SaleID INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, CustomerName TEXT, Category TEXT, ItemName TEXT, Qty REAL, Total REAL, PaymentMode TEXT)")
        
        # Payroll
        conn.execute("CREATE TABLE IF NOT EXISTS StaffLeaves (id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, LeaveDate TEXT, Reason TEXT, Type TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS SalaryHistory (id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Month TEXT, Basic REAL, Bonus REAL, Deduction REAL, NetPaid REAL)")
        conn.commit()

init_db()

def fetch_df(conn_unused, query, params=()):
    with db_connect() as conn:
        return pd.read_sql_query(query, conn, params=params)
