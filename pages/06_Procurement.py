import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime

# ===============================
# 0. SAFE DATABASE INIT (NO DATA LOSS)
# ===============================
def init_db():
    with db_connect() as conn:

        # ANIMAL MASTER
        conn.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY)")
        cols = [i[1] for i in conn.execute("PRAGMA table_info(AnimalMaster)")]

        if "Breed" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN Breed TEXT")
        if "Category" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN Category TEXT")
        if "Status" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN Status TEXT DEFAULT 'Open'")
        if "PurchasePrice" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN PurchasePrice REAL")
        if "PurchaseDate" not in cols:
            conn.execute("ALTER TABLE AnimalMaster ADD COLUMN PurchaseDate TEXT")

        # LIVESTOCK AUTO SYNC TABLE
        conn.execute("""CREATE TABLE IF NOT EXISTS LivestockMaster (
            TagID TEXT PRIMARY KEY,
            Breed TEXT,
            Category TEXT,
            Status TEXT,
            EntryDate TEXT
        )""")

        # ITEM MASTER
        conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
            ItemName TEXT PRIMARY KEY,
            Category TEXT,
            UOM TEXT,
            Quantity REAL DEFAULT 0,
            Cost REAL DEFAULT 0
        )""")

        # VENDOR MASTER
        conn.execute("""CREATE TABLE IF NOT EXISTS VendorMaster (
            VendorName TEXT PRIMARY KEY
        )""")

        # LEDGER
        conn.execute("""CREATE TABLE IF NOT EXISTS VendorLedger (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VendorName TEXT,
            Date TEXT,
            Description TEXT,
            Credit REAL
        )""")

        conn.commit()

init_db()

# ===============================
# HEADER
# ===============================
st.markdown("## 🛒 ZUNI PROCUREMENT SYSTEM")

# ===============================
# FETCH DATA SAFE
# ===============================
with db_connect() as conn:
    try:
        vendors_df = fetch_df(conn, "SELECT VendorName FROM VendorMaster")
        vendors = vendors_df['VendorName'].tolist() if not vendors_df.empty else []
    except:
        vendors = []

    try:
        items_df = fetch_df(conn, "SELECT * FROM ItemMaster")
    except:
        items_df = pd.DataFrame()

# ===============================
# TABS
# ===============================
t1, t2, t3 = st.tabs(["🐄 Animal Purchase", "📦 Store Purchase", "📜 History"])

# =========================================================
# 🐄 TAB 1: ANIMAL PURCHASE
# =========================================================
with t1:
    st.subheader("🐄 Purchase Animal")

    with st.form("animal_form"):
        c1, c2, c3 = st.columns(3)
        vendor = c1.selectbox("Vendor", [""] + vendors)
        tag = c2.text_input("Tag ID").strip().upper()
        date = c3.date_input("Date", datetime.now())

        c4, c5, c6 = st.columns(3)
        breed = c4.selectbox("Breed", ["HF", "Jersey", "Sahiwal", "Cross"])
        category = c5.selectbox("Category", ["Cow", "Bull", "Heifer", "Calf"])
        price = c6.number_input("Price", min_value=0.0)

        # 🔥 STATUS LOGIC
        if category == "Cow":
            status = st.selectbox("Status", ["Open", "Pregnant"])
        elif category == "Heifer":
            status = "Open"
            st.info("Heifer default status = Open")
        elif category == "Bull":
            status = "Active"
        else:
            status = "Young"

        submit = st.form_submit_button("✅ Purchase Animal")

        if submit:
            if vendor and tag:
                try:
                    with db_connect() as conn:

                        # DUPLICATE CHECK
                        exists = conn.execute(
                            "SELECT 1 FROM AnimalMaster WHERE TagID=?",
                            (tag,)
                        ).fetchone()

                        if exists:
                            st.error("❌ Tag already exists!")
                        else:
                            # INSERT ANIMAL
                            conn.execute("""
                                INSERT INTO AnimalMaster
                                (TagID, Breed, Category, Status, PurchasePrice, PurchaseDate)
                                VALUES (?,?,?,?,?,?)
                            """, (tag, breed, category, status, price, date))

                            # 🔥 LIVESTOCK AUTO SYNC
                            conn.execute("""
                                INSERT INTO LivestockMaster
                                (TagID, Breed, Category, Status, EntryDate)
                                VALUES (?,?,?,?,?)
                            """, (tag, breed, category, status, date))

                            # LEDGER
                            conn.execute("""
                                INSERT INTO VendorLedger
                                (VendorName, Date, Description, Credit)
                                VALUES (?,?,?,?)
                            """, (vendor, date, f"Animal Purchase {tag}", price))

                            conn.commit()

                    st.success(f"✅ Animal {tag} added + synced")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Vendor & Tag required")

# =========================================================
# 📦 TAB 2: STORE PURCHASE (MULTI ITEM)
# =========================================================
with t2:
    st.subheader("📦 Store Purchase")

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

    df_cart = pd.DataFrame(st.session_state.cart)

    if not df_cart.empty:
        st.dataframe(df_cart)

        total = df_cart["total"].sum()
        st.success(f"💰 Total = {total}")

        if st.button("✅ Complete Purchase"):
            if vendor:
                with db_connect() as conn:
                    for row in st.session_state.cart:

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

                    # LEDGER ENTRY
                    conn.execute("""
                        INSERT INTO VendorLedger
                        (VendorName, Date, Description, Credit)
                        VALUES (?,?,?,?)
                    """, (vendor, date, "Store Purchase", total))

                    conn.commit()

                st.session_state.cart = []
                st.success("✅ Purchase Completed")
                st.rerun()
            else:
                st.warning("Vendor required")

# =========================================================
# 📜 TAB 3: HISTORY + STATUS COUNT
# =========================================================
with t3:
    st.subheader("📜 Purchase History")

    with db_connect() as conn:
        df = fetch_df(conn, "SELECT * FROM VendorLedger ORDER BY ID DESC")

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No history")

    st.divider()

    # 🔥 STATUS COUNT
    st.subheader("🐄 Animal Status Summary")

    with db_connect() as conn:
        df_status = fetch_df(conn, """
            SELECT Status, COUNT(*) as Total
            FROM AnimalMaster
            GROUP BY Status
        """)

    if not df_status.empty:
        st.dataframe(df_status, use_container_width=True)
