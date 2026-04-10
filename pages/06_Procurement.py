def auto_fix_animalmaster():
    with db_connect() as conn:

        # Table create if not exists (minimum structure)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY
        )
        """)

        # Get existing columns
        cols = [i[1] for i in conn.execute("PRAGMA table_info(AnimalMaster)")]

        # 🔥 FIX 1: Rename old column "Tag" → "TagID"
        if "Tag" in cols and "TagID" not in cols:
            try:
                conn.execute("ALTER TABLE AnimalMaster RENAME COLUMN Tag TO TagID")
            except:
                pass

        # Refresh column list
        cols = [i[1] for i in conn.execute("PRAGMA table_info(AnimalMaster)")]

        # 🔥 FIX 2: Ensure required columns exist
        required_cols = {
            "TagID": "TEXT",
            "Breed": "TEXT",
            "Category": "TEXT",
            "Status": "TEXT DEFAULT 'Open'",
            "PurchasePrice": "REAL DEFAULT 0",
            "PurchaseDate": "TEXT"
        }

        for col, dtype in required_cols.items():
            if col not in cols:
                try:
                    conn.execute(f"ALTER TABLE AnimalMaster ADD COLUMN {col} {dtype}")
                except:
                    pass

        conn.commit()
