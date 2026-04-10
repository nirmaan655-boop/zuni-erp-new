import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Vendors", layout="wide")

# =========================
# VENDOR FUNCTIONS
# =========================
def get_vendors():
    with db_connect() as conn:
        df = fetch_df(conn, "SELECT VendorName, ContactPerson, Phone, Address FROM VendorMaster ORDER BY VendorName")
        if df is None or df.empty:
            return pd.DataFrame(columns=["VendorName", "ContactPerson", "Phone", "Address"])
        return df


# =========================
# SESSION STATE
# =========================
if "edit_vendor" not in st.session_state:
    st.session_state.edit_vendor = None


# =========================
# HEADER
# =========================
st.markdown("## 🏢 Vendor Management System")


# =========================
# FORM SECTION
# =========================
with st.form("vendor_form", clear_on_submit=True):
    ev = st.session_state.edit_vendor

    col1, col2 = st.columns(2)

    name = col1.text_input("Vendor Name", value=ev["VendorName"] if ev is not None else "")
    contact = col2.text_input("Contact Person", value=ev["ContactPerson"] if ev is not None else "")

    phone = col1.text_input("Phone", value=ev["Phone"] if ev is not None else "")
    address = col2.text_input("Address", value=ev["Address"] if ev is not None else "")

    save = st.form_submit_button("💾 Save Vendor")

    if save:
        if name.strip() == "":
            st.error("Vendor Name required")
        else:
            with db_connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO VendorMaster
                    (VendorName, ContactPerson, Phone, Address)
                    VALUES (?, ?, ?, ?)
                """, (name.strip().upper(), contact, phone, address))
                conn.commit()

            st.success("Vendor Saved Successfully")
            st.session_state.edit_vendor = None
            st.rerun()


# =========================
# DATA DISPLAY
# =========================
df = get_vendors()

st.markdown("### 📋 Vendor List")

if not df.empty:
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)

    selected = col1.selectbox("Select Vendor", df["VendorName"].tolist())

    if col2.button("📝 Edit Vendor"):
        st.session_state.edit_vendor = df[df["VendorName"] == selected].iloc[0]
        st.rerun()

    if col2.button("🗑️ Delete Vendor"):
        with db_connect() as conn:
            conn.execute("DELETE FROM VendorMaster WHERE VendorName = ?", (selected,))
            conn.commit()
        st.success("Deleted Successfully")
        st.rerun()

else:
    st.info("No vendors found. Add new vendor above.")
