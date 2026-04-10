import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df

# =========================
# PAGE SETUP
# =========================
st.set_page_config(page_title="Master Setup", layout="wide")

# =========================
# SESSION STATE
# =========================
if "edit_v" not in st.session_state:
    st.session_state.edit_v = None
if "edit_e" not in st.session_state:
    st.session_state.edit_e = None
if "edit_a" not in st.session_state:
    st.session_state.edit_a = None


# =========================
# TABS
# =========================
tab_v, tab_e, tab_a = st.tabs(["🤝 VENDORS", "👷 EMPLOYEES", "💰 ACCOUNTS"])


# =========================
# VENDORS
# =========================
with tab_v:
    st.subheader("Vendor Management")

    with st.form("vendor_form", clear_on_submit=True):
        ev = st.session_state.edit_v

        c1, c2 = st.columns(2)

        name = c1.text_input("Vendor Name", value=ev["VendorName"] if ev else "")
        contact = c2.text_input("Contact Person", value=ev["ContactPerson"] if ev else "")
        phone = c1.text_input("Phone", value=ev["Phone"] if ev else "")
        address = c2.text_input("Address", value=ev["Address"] if ev else "")

        if st.form_submit_button("Save Vendor"):
            with db_connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO VendorMaster
                    (VendorName, ContactPerson, Phone, Address)
                    VALUES (?, ?, ?, ?)
                """, (name.upper(), contact, phone, address))
                conn.commit()

            st.session_state.edit_v = None
            st.rerun()

    df_v = fetch_df(db_connect(), "SELECT * FROM VendorMaster")

    st.dataframe(df_v, use_container_width=True)

    if not df_v.empty:
        sel = st.selectbox("Select Vendor", df_v["VendorName"].tolist())

        if st.button("Edit Vendor"):
            st.session_state.edit_v = df_v[df_v["VendorName"] == sel].iloc[0]
            st.rerun()

        if st.button("Delete Vendor"):
            with db_connect() as conn:
                conn.execute("DELETE FROM VendorMaster WHERE VendorName=?", (sel,))
                conn.commit()
            st.rerun()


# =========================
# EMPLOYEES
# =========================
with tab_e:
    st.subheader("Employee Register")

    with st.form("emp_form", clear_on_submit=True):
        ee = st.session_state.edit_e

        c1, c2, c3 = st.columns(3)

        name = c1.text_input("Name", value=ee["Name"] if ee else "")
        cnic = c2.text_input("CNIC", value=ee["CNIC"] if ee else "")
        phone = c3.text_input("Phone", value=ee["Phone"] if ee else "")

        desig = c1.selectbox("Designation", ["Manager", "Supervisor", "Doctor", "Worker", "Guard"])
        salary = c2.number_input("Salary", value=float(ee["Salary"]) if ee else 0.0)
        leave = c3.number_input("Leaves Allowed", value=int(ee["LeaveAllowed"]) if ee else 2)

        if st.form_submit_button("Save Employee"):
            with db_connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO EmployeeMaster
                    (Name, CNIC, Phone, Designation, Salary, LeaveAllowed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, cnic, phone, desig, salary, leave))
                conn.commit()

            st.session_state.edit_e = None
            st.rerun()

    df_e = fetch_df(db_connect(), "SELECT * FROM EmployeeMaster")

    st.dataframe(df_e, use_container_width=True)

    if not df_e.empty:
        sel = st.selectbox("Select Employee", df_e["Name"].tolist())

        if st.button("Edit Employee"):
            st.session_state.edit_e = df_e[df_e["Name"] == sel].iloc[0]
            st.rerun()

        if st.button("Delete Employee"):
            with db_connect() as conn:
                conn.execute("DELETE FROM EmployeeMaster WHERE Name=?", (sel,))
                conn.commit()
            st.rerun()


# =========================
# CHART OF ACCOUNTS
# =========================
with tab_a:
    st.subheader("Chart of Accounts")

    with st.form("coa_form", clear_on_submit=True):
        ea = st.session_state.edit_a

        c1, c2, c3 = st.columns(3)

        acc = c1.text_input("Account Name", value=ea["AccountName"] if ea else "")
        typ = c2.selectbox("Type", ["Cash", "Bank", "Expense", "Income", "Asset"])
        bal = c3.number_input("Opening Balance", value=float(ea["Balance"]) if ea else 0.0)

        if st.form_submit_button("Save Account"):
            with db_connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ChartOfAccounts
                    (AccountName, AccountType, Balance)
                    VALUES (?, ?, ?)
                """, (acc.upper(), typ, bal))
                conn.commit()

            st.session_state.edit_a = None
            st.rerun()

    df_a = fetch_df(db_connect(), "SELECT * FROM ChartOfAccounts")

    st.dataframe(df_a, use_container_width=True)

    if not df_a.empty:
        sel = st.selectbox("Select Account", df_a["AccountName"].tolist())

        if st.button("Edit Account"):
            st.session_state.edit_a = df_a[df_a["AccountName"] == sel].iloc[0]
            st.rerun()

        if st.button("Delete Account"):
            with db_connect() as conn:
                conn.execute("DELETE FROM ChartOfAccounts WHERE AccountName=?", (sel,))
                conn.commit()
            st.rerun()
