import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Master Setup")

st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>👥 MASTER SETUP CENTER</h1>
        <p style='color: #FF851B; margin: 0; font-weight: bold;'>Vendors, Employees & Chart of Accounts</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🤝 VENDORS", "👷 EMPLOYEES", "🏦 CHART OF ACCOUNTS"])

# ================= 1. VENDORS SETUP =================
with tab1:
    st.subheader("Manage Business Vendors")
    with st.form("vendor_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        v_name = c1.text_input("Vendor Name (Company)").strip().upper()
        v_person = c2.text_input("Contact Person")
        v_phone = c1.text_input("Phone Number")
        v_address = c2.text_input("Office Address")
        
        if st.form_submit_button("✅ Save Vendor"):
            if v_name:
                with db_connect() as conn:
                    conn.execute("""INSERT INTO VendorMaster (VendorName, ContactPerson, Phone, Address) 
                                    VALUES (?,?,?,?) ON CONFLICT(VendorName) DO UPDATE SET 
                                    ContactPerson=excluded.ContactPerson, Phone=excluded.Phone, Address=excluded.Address""", 
                                 (v_name, v_person, v_phone, v_address))
                    conn.commit()
                st.success(f"Vendor {v_name} Saved!")
                st.rerun()

    st.divider()
    st.write("### 📜 Registered Vendors History")
    df_v = fetch_df(None, "SELECT * FROM VendorMaster")
    st.dataframe(df_v, use_container_width=True, hide_index=True)
    
    if not df_v.empty:
        v_to_del = st.selectbox("Select Vendor to Delete", df_v['VendorName'].tolist())
        if st.button("🗑️ Delete Vendor", type="primary"):
            with db_connect() as conn:
                conn.execute("DELETE FROM VendorMaster WHERE VendorName=?", (v_to_del,))
                conn.commit()
            st.rerun()

# ================= 2. EMPLOYEES SETUP =================
with tab2:
    st.subheader("Staff & Payroll Setup")
    with st.form("employee_form", clear_on_submit=True):
        e1, e2 = st.columns(2)
        e_name = e1.text_input("Employee Name").strip().upper()
        e_desig = e2.selectbox("Designation", ["Manager", "Supervisor", "Vet", "Labor", "Guard"])
        e_sal = e1.number_input("Monthly Salary", min_value=0)
        e_leave = e2.number_input("Allowed Leaves", min_value=0, value=2)
        
        if st.form_submit_button("📝 Register Employee"):
            if e_name:
                with db_connect() as conn:
                    conn.execute("""INSERT INTO EmployeeMaster (Name, Designation, Salary, LeaveAllowed) 
                                    VALUES (?,?,?,?) ON CONFLICT(Name) DO UPDATE SET 
                                    Designation=excluded.Designation, Salary=excluded.Salary, LeaveAllowed=excluded.LeaveAllowed""", 
                                 (e_name, e_desig, e_sal, e_leave))
                    conn.commit()
                st.rerun()

    st.write("### 📜 Staff List")
    df_e = fetch_df(None, "SELECT * FROM EmployeeMaster")
    st.dataframe(df_e, use_container_width=True)

# ================= 3. CHART OF ACCOUNTS =================
with tab3:
    st.subheader("Financial Accounts (COA)")
    with st.form("coa_form", clear_on_submit=True):
        a1, a2 = st.columns(2)
        acc_name = a1.text_input("Account Name (e.g. HBL Bank, Cash)").strip().upper()
        acc_type = a2.selectbox("Account Type", ["Cash In Hand", "Bank Account", "Expense", "Fixed Asset"])
        acc_bal = a1.number_input("Opening Balance", min_value=0.0)
        
        if st.form_submit_button("🏦 Add Account"):
            if acc_name:
                with db_connect() as conn:
                    conn.execute("INSERT INTO ChartOfAccounts (AccountName, AccountType, Balance) VALUES (?,?,?)", 
                                 (acc_name, acc_type, acc_bal))
                    conn.commit()
                st.rerun()

    st.write("### 📜 Active Accounts")
    df_a = fetch_df(None, "SELECT * FROM ChartOfAccounts")
    st.dataframe(df_a, use_container_width=True)
