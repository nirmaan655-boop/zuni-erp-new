def auto_fix_database():
    with db_connect() as conn:

        # ---- AnimalMaster Fix ----
        cols = [i[1] for i in conn.execute("PRAGMA table_info(AnimalMaster)")]

        if "Tag" in cols and "TagID" not in cols:
            try:
                conn.execute("ALTER TABLE AnimalMaster RENAME COLUMN Tag TO TagID")
            except:
                pass

        if "Status" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN Status TEXT DEFAULT 'Open'")

        # ---- ItemMaster Fix ----
        cols = [i[1] for i in conn.execute("PRAGMA table_info(ItemMaster)")]

        if "Store" not in cols:
            conn.execute("ALTER TABLE ItemMaster ADD COLUMN Store TEXT DEFAULT 'General'")

        if "Quantity" not in cols:
            conn.execute("ALTER TABLE ItemMaster ADD COLUMN Quantity REAL DEFAULT 0")

        if "Cost" not in cols:
            conn.execute("ALTER TABLE ItemMaster ADD COLUMN Cost REAL DEFAULT 0")

        # ---- PurchaseLog Fix ----
        conn.execute('''CREATE TABLE IF NOT EXISTS PurchaseLog(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Type TEXT,
            Ref TEXT,
            Item TEXT,
            Qty REAL,
            Rate REAL,
            Total REAL,
            Vendor TEXT,
            Store TEXT,
            Date TEXT
        )''')

        conn.commit()
