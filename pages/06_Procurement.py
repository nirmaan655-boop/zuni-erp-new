import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime

# ===============================
# 0. DATABASE INIT (FULL SAFE)
# ===============================
def init_db():
    with db_connect() as conn:

        # ANIMAL MASTER (PROCUREMENT + LIVESTOCK SYNC)
        conn.execute('''CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY,
            Breed TEXT,
            Category TEXT,
            Status TEXT DEFAULT 'Active',
            CurrentPen TEXT DEFAULT 'GENERAL',
            Weight REAL DEFAULT 0,
            PurchasePrice REAL DEFAULT 0,
            PurchaseDate TEXT
        )''')

        # LIVESTOCK MASTER (AUTO SYNC TABLE)
        conn.execute('''CREATE TABLE IF NOT EXISTS LivestockMaster (
            TagID TEXT PRIMARY KEY,
            Breed TEXT,
            Category TEXT,
            Status TEXT,
            EntryDate TEXT
        )''')

        # ITEM MASTER
        conn.execute('''CREATE TABLE IF NOT EXISTS ItemMaster (
            ItemName TEXT PRIMARY KEY,
            Category TEXT,
            UOM TEXT,
            Quantity REAL DEFAULT 0,
            Cost REAL DEFAULT 0
        )''')

        # VENDOR MASTER
        conn.execute('''CREATE TABLE IF NOT EXISTS VendorMaster (
            VendorName TEXT PRIMARY KEY
        )''')

        # LEDGER
        conn.execute('''CREATE TABLE IF NOT EXISTS VendorLedger (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VendorName TEXT,
            Date TEXT,
            Description TEXT,
            Credit REAL
        )''')

        conn.commit()

init_db()

# ===============================
# 1. HEADER
# ===============================
st.markdown("## 🛒 ZUNI PROCUREMENT SYSTEM")

# ===============================
# 2. FETCH DATA SAFE
# ===============================
with db_connect() as conn:
    vendors_df = fetch_df(conn, "SELECT VendorName FROM VendorMaster")
    vendors = vendors_df['VendorName'].tolist() if not vendors_df.empty else []

    items_df = fetch_df(conn, "SELECT * FROM ItemMaster")

# ===============================
# TABS
# ===============================
t1, t2, t3 = st.tabs(["🐄 Animal Purchase", "📦 Store Purchase", "📜 History"])

# =========================================================
# 🐄 TAB 1: ANIMAL PURCHASE + AUTO LIVESTOCK SYNC
# =========================================================
with t1:
    st.subheader("🐄 Purchase Animal")

    with st.form("animal_form"):
        c1, c2, c3 = st.columns(3)
        vendor = c1.selectbox("Vendor", [""] + vendors)
        tag = c2.text_input("Tag ID").upper()
        date = c3.date_input("Date", datetime.now())

        c4, c5, c6 = st.columns(3)
        breed = c4.selectbox("Breed", ["HF", "Jersey", "Sahiwal", "Cross"])
        category = c5.selectbox("Category", ["Cow", "Bull", "Heifer", "Calf"])
        price = c6.number_input("Price", min_value=0.0)

        submitted = st.form_submit_button("✅ Purchase Animal")

        if submitted:
            if vendor and tag:

                with db_connect() as conn:

                    # CHECK DUPLICATE
                    exists = conn.execute(
                        "SELECT TagID FROM AnimalMaster WHERE TagID=?",
                        (tag,)
                    ).fetchone()

                    if exists:
                        st.error("❌ Tag already exists!")
                    else:
                        # INSERT IN ANIMAL MASTER
                        conn.execute("""
                            INSERT INTO AnimalMaster 
                            (TagID, Breed, Category, Status, PurchasePrice, PurchaseDate)
                            VALUES (?,?,?,?,?,?)
                        """, (tag, breed, category, "Active", price, date))

                        # 🔥 AUTO LIVESTOCK SYNC
                        conn.execute("""
                            INSERT INTO LivestockMaster
                            (TagID, Breed, Category, Status, EntryDate)
                            VALUES (?,?,?,?,?)
                        """, (tag, breed, category, "Active", date))

                        # LEDGER ENTRY
                        conn.execute("""
                            INSERT INTO VendorLedger 
                            (VendorName, Date, Description, Credit)
                            VALUES (?,?,?,?)
                        """, (vendor, date, f"Animal Purchase {tag}", price))

                        conn.commit()

                st.success(f"✅ Animal {tag} added + synced to Livestock")
                st.rerun()
            else:
                st.warning("Fill all required fields")

# =========================================================
# 📦 TAB 2: STORE PURCHASE (MULTI ITEM + INVENTORY)
# =========================================================
with t2:
    st.subheader("📦 Store Purchase (Multi Item)")

    vendor = st.selectbox("Vendor", [""] + vendors, key="store_vendor")
    date = st.date_input("Date", datetime.now(), key="store_date")

    category = st.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen", "Fuel"])

    if "cart" not in st.session_state:
        st.session_state.cart = []

    col1, col2, col3 = st.columns(3)
    item = col1.text_input("Item Name")
    qty = col2.number_input("Qty", min_value=0.0)
    rate = col3.number_input("Rate", min_value=0.0)

    if st.button("➕ Add Item"):
        if item and qty > 0:
            st.session_state.cart.append({
                "item": item,
                "qty": qty,
                "rate": rate,
                "total": qty * rate
            })

    # SHOW CART
    df_cart = pd.DataFrame(st.session_state.cart)
    if not df_cart.empty:
        st.dataframe(df_cart)

        grand_total = df_cart["total"].sum()
        st.success(f"💰 Total = {grand_total}")

        if st.button("✅ Complete Purchase"):
            with db_connect() as conn:
                for row in st.session_state.cart:

                    # UPSERT ITEM
                    exist = conn.execute(
                        "SELECT Quantity FROM ItemMaster WHERE ItemName=?",
                        (row["item"],)
                    ).fetchone()

                    if exist:
                        conn.execute("""
                            UPDATE ItemMaster
                            SET Quantity = Quantity + ?, Cost = ?
                            WHERE ItemName = ?
                        """, (row["qty"], row["rate"], row["item"]))
                    else:
                        conn.execute("""
                            INSERT INTO ItemMaster
                            (ItemName, Category, UOM, Quantity, Cost)
                            VALUES (?,?,?,?,?)
                        """, (row["item"], category, "Unit", row["qty"], row["rate"]))

                # LEDGER
                conn.execute("""
                    INSERT INTO VendorLedger
                    (VendorName, Date, Description, Credit)
                    VALUES (?,?,?,?)
                """, (vendor, date, "Store Purchase", grand_total))

                conn.commit()

            st.session_state.cart = []
            st.success("✅ Purchase Completed")
            st.rerun()

# =========================================================
# 📜 TAB 3: HISTORY
# =========================================================
with t3:
    st.subheader("📜 Purchase History")

    with db_connect() as conn:
        df = fetch_df(conn, "SELECT * FROM VendorLedger ORDER BY ID DESC")

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No data found")
