import streamlit as st
import pandas as pd
from datetime import datetime
from zuni_db import db_connect, fetch_df

# ---------------- SAFE TAG HANDLER ----------------
def get_tag_column(conn):
    cols = [i[1] for i in conn.execute("PRAGMA table_info(AnimalMaster)")]

    if "TagID" in cols:
        return "TagID"
    if "Tag" in cols:
        return "Tag"

    conn.execute("ALTER TABLE AnimalMaster ADD COLUMN TagID TEXT")
    return "TagID"


# ---------------- INIT ----------------
def init_db():
    with db_connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS VendorLedger(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VendorName TEXT,
            Date TEXT,
            Description TEXT,
            Credit REAL
        )
        """)
        conn.commit()

init_db()

# ---------------- UI ----------------
st.title("🛒 PROCUREMENT SYSTEM")

tab1, tab2, tab3 = st.tabs(["🐄 Animal Purchase", "📦 Store Purchase", "📜 History"])

# =========================
# 🐄 ANIMAL PURCHASE
# =========================
with tab1:
    st.subheader("Animal Purchase")

    with st.form("animal"):
        col1, col2 = st.columns(2)

        tag = col1.text_input("Tag ID").strip().upper()
        breed = col1.selectbox("Breed", ["HF","Jersey","Sahiwal","Cross"])
        category = col2.selectbox("Category", ["Cow","Heifer","Bull","Calf"])
        status = col2.selectbox("Status", ["Open","Pregnant","Active"])

        price = st.number_input("Price", 0.0)
        vendor = st.text_input("Vendor")
        date = st.date_input("Date", datetime.now())

        ok = st.form_submit_button("Save Animal")

        if ok:
            with db_connect() as conn:

                tag_col = get_tag_column(conn)

                exists = conn.execute(
                    f"SELECT 1 FROM AnimalMaster WHERE {tag_col}=?",
                    (tag,)
                ).fetchone()

                if exists:
                    st.error("❌ Animal already exists")
                else:
                    conn.execute(f"""
                        INSERT INTO AnimalMaster
                        ({tag_col}, Breed, Category, Status, PurchasePrice, PurchaseDate)
                        VALUES (?,?,?,?,?,?)
                    """, (tag, breed, category, status, price, date))

                    conn.execute("""
                        INSERT INTO VendorLedger
                        (VendorName, Date, Description, Credit)
                        VALUES (?,?,?,?)
                    """, (vendor, date, f"Animal Purchase {tag}", price))

                    conn.commit()
                    st.success("✅ Animal Added Successfully")


# =========================
# 📦 STORE PURCHASE
# =========================
with tab2:
    st.subheader("Store Purchase")

    store = st.selectbox("Store", ["Feed","Medicine","Vaccine","Semen","Fuel","General"])
    item = st.text_input("Item Name")

    qty = st.number_input("Qty", 0.0)
    rate = st.number_input("Rate", 0.0)
    total = qty * rate

    vendor = st.text_input("Vendor")
    date = st.date_input("Date", datetime.now())

    st.info(f"Total = {total}")

    if st.button("Save Purchase"):

        with db_connect() as conn:

            exists = conn.execute(
                "SELECT Quantity FROM ItemMaster WHERE ItemName=?",
                (item,)
            ).fetchone()

            if exists:
                conn.execute("""
                    UPDATE ItemMaster
                    SET Quantity = Quantity + ?, Cost = ?, Store = ?
                    WHERE ItemName = ?
                """, (qty, rate, store, item))
            else:
                conn.execute("""
                    INSERT INTO ItemMaster
                    (ItemName, Category, Store, UOM, Quantity, Cost)
                    VALUES (?,?,?,?,?,?)
                """, (item, store, store, "Unit", qty, rate))

            conn.execute("""
                INSERT INTO VendorLedger
                (VendorName, Date, Description, Credit)
                VALUES (?,?,?,?)
            """, (vendor, date, f"{item} Purchase", total))

            conn.commit()

            st.success("✅ Inventory Updated")


# =========================
# 📜 HISTORY
# =========================
with tab3:
    st.subheader("Purchase History")

    with db_connect() as conn:
        ledger = fetch_df(conn, "SELECT * FROM VendorLedger ORDER BY ID DESC")

    st.dataframe(ledger, use_container_width=True)

    st.divider()
    st.subheader("🐄 Animals")

    with db_connect() as conn:
        tag_col = get_tag_column(conn)
        animals = fetch_df(conn, f"SELECT {tag_col}, Breed, Category, Status FROM AnimalMaster")

    st.dataframe(animals, use_container_width=True)

    st.subheader("📦 Inventory")

    with db_connect() as conn:
        items = fetch_df(conn, "SELECT * FROM ItemMaster")

    st.dataframe(items, use_container_width=True)
