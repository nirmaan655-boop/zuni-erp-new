import streamlit as st
from zuni_db import *

# ===============================
# AUTO INIT DB
# ===============================
init_db()

st.title("📦 Master Management (Vendor / Employee / CAO)")

# ===============================
# TYPE SELECTOR
# ===============================
type_selected = st.radio(
    "Select Type",
    ["Vendor", "Employee", "CAO"]
)

# ===============================
# ADD RECORD FORM
# ===============================
st.subheader(f"➕ Add New {type_selected}")

with st.form("master_form"):
    name = st.text_input("Name")
    phone = st.text_input("Phone")
    address = st.text_area("Address")

    submit = st.form_submit_button("Save")

    if submit:
        if name:

            if type_selected == "Vendor":
                add_vendor(name, phone, address)

            elif type_selected == "Employee":
                conn = db_connect()
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS Employee (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone TEXT,
                        address TEXT
                    )
                """)
                conn.execute("INSERT INTO Employee (name, phone, address) VALUES (?, ?, ?)",
                             (name, phone, address))
                conn.commit()
                conn.close()

            elif type_selected == "CAO":
                conn = db_connect()
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS CAO (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone TEXT,
                        address TEXT
                    )
                """)
                conn.execute("INSERT INTO CAO (name, phone, address) VALUES (?, ?, ?)",
                             (name, phone, address))
                conn.commit()
                conn.close()

            st.success(f"{type_selected} Added Successfully ✅")

        else:
            st.error("Name required!")


# ===============================
# SHOW DATA
# ===============================
st.subheader(f"📋 {type_selected} List")

if type_selected == "Vendor":
    df = fetch_df("SELECT * FROM VendorMaster")

elif type_selected == "Employee":
    df = fetch_df("SELECT * FROM Employee")

elif type_selected == "CAO":
    df = fetch_df("SELECT * FROM CAO")

st.dataframe(df, use_container_width=True)
