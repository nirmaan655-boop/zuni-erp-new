import streamlit as st
from zuni_db import db_connect, fetch_df
from datetime import date

st.title("🛒 PROCUREMENT & STOCK IN")

with db_connect() as conn:
    vendors = fetch_df(None, "SELECT VendorName FROM VendorMaster")['VendorName'].tolist()

with st.form("p_form"):
    cat = st.selectbox("Category", ["Animal", "Feed", "Medicine", "Semen Straws"])
    item = st.text_input("Item Name / Tag ID").upper()
    prc = st.number_input("Purchase Rate")
    qty = st.number_input("Quantity", value=1.0)
    vend = st.selectbox("Vendor", ["CASH PURCHASE"] + vendors)
    
    if st.form_submit_button("Confirm Purchase"):
        with db_connect() as conn:
            if cat == "Animal":
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, Status, PurchasePrice, PurchaseDate) VALUES (?,?,?,?,?)", (item, "Cow", "Active", prc, str(date.today())))
            else:
                conn.execute("INSERT INTO ItemMaster (ItemName, Category, Quantity, Cost) VALUES (?,?,?,?) ON CONFLICT(ItemName) DO UPDATE SET Quantity=Quantity+excluded.Quantity", (item, cat, qty, prc))
            
            # Accounting Entry
            conn.execute("INSERT INTO Transactions (Date, AccountName, PayeeName, Description, Debit, Credit) VALUES (?,?,?,?,?,?)", (str(date.today()), "CASH", vend, f"Purchase: {item}", prc * qty, 0))
            conn.commit()
        st.success("Inventory & Financials Updated!")
