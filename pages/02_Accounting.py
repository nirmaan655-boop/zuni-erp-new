import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date
import os

# --- 1. PAGE CONFIG & BRANDING ---
st.set_page_config(page_title="Zuni ERP | Financials", layout="wide")

st.markdown("""
    <style>
    .main-header { background-color: #d32f2f; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: white; display: flex; justify-content: space-between; align-items: center; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .grid-header { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-bottom: 2px solid #d32f2f; font-weight: bold; margin-bottom: 10px; }
    </style>
    <div class="main-header">
        <h2 style='margin: 0;'>💰 ZUNI FINANCIAL CONTROL CENTER</h2>
        <div style='background: white; color: #d32f2f; padding: 5px 15px; border-radius: 5px; font-weight: bold;'>FY 2026</div>
    </div>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE FOR FORMS ---
if 'pmt_rows' not in st.session_state:
    st.session_state.pmt_rows = [{"Account": "", "Amount": 0.0, "Narration": ""}]
if 'jv_rows' not in st.session_state:
    st.session_state.jv_rows = [{"Acc": "", "Dr": 0.0, "Cr": 0.0, "Nar": ""}, {"Acc": "", "Dr": 0.0, "Cr": 0.0, "Nar": ""}]

# --- 3. FETCH DATA ---
with db_connect() as conn:
    acc_df = fetch_df(conn, "SELECT AccountName, AccountType, Balance FROM ChartOfAccounts")
    try: vendors = fetch_df(conn, "SELECT VendorName as Name FROM VendorMaster")['Name'].tolist()
    except: vendors = []
    try: employees = fetch_df(conn, "SELECT Name FROM EmployeeMaster")['Name'].tolist()
    except: employees = []
    all_heads = sorted(list(set(acc_df['AccountName'].tolist() + vendors + employees + ["Milk Sale", "Feed Expense", "General Expense"])))

# --- 4. TABS SYSTEM ---
tab1, tab2, tab3, tab4 = st.tabs(["📝 VOUCHER ENTRY", "📖 PARTY LEDGER", "📊 REPORTS", "📜 HISTORY & EDIT"])

# --- TAB 1: VOUCHER ENTRY ---
with tab1:
    v_cat = st.radio("Select Voucher Type", ["💳 Payment / Receipt", "🔄 Journal Transaction (JV)"], horizontal=True)

    if v_cat == "💳 Payment / Receipt":
        v_mode = st.radio("Action", ["💸 Payment (Outward)", "💰 Receipt (Inward)"], horizontal=True)
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            inv_no = c1.text_input("Invoice No", placeholder="Enter Invoice No")
            pay_methods = acc_df[acc_df['AccountName'].str.contains('Cash|Bank', case=False)]
            pay_options = [f"{r['AccountName']} | Bal: {r['Balance']:,.0f}" for _, r in pay_methods.iterrows()]
            
            if pay_options:
                sel_method_str = c2.selectbox("Payment From / Receive In", pay_options)
                method_name = sel_method_str.split(" | ")[0]
            else:
                st.warning("⚠️ No Cash/Bank Accounts found!")
                method_name = "None"
            t_date = c3.date_input("Transaction Date", date.today(), key="p_dt")

        updated_pmt = []
        for i, row in enumerate(st.session_state.pmt_rows):
            r1, r2, r3, r4 = st.columns([3, 2, 2, 3])
            acc = r1.selectbox(f"p_acc_{i}", [""] + all_heads, key=f"p_acc_{i}", label_visibility="collapsed")
            info = acc_df[acc_df['AccountName'] == acc]
            cur_bal = info['Balance'].iloc[0] if not info.empty else 0
            r2.write(f"**Bal: {cur_bal:,.0f}**")
            amt = r3.number_input(f"Amount", value=row['Amount'], key=f"p_amt_{i}", label_visibility="collapsed")
            nar = r4.text_input(f"Narration", value=row['Narration'], key=f"p_nar_{i}", label_visibility="collapsed")
            updated_pmt.append({"Account": acc, "Amount": amt, "Narration": nar})

        if st.button("➕ Add Row"):
            st.session_state.pmt_rows = updated_pmt + [{"Account": "", "Amount": 0.0, "Narration": ""}]
            st.rerun()

        if st.button("✅ Post Voucher", type="primary", use_container_width=True):
            if method_name != "None" and sum(x['Amount'] for x in updated_pmt) > 0:
                with db_connect() as conn:
                    for r in updated_pmt:
                        if r['Account'] != "" and r['Amount'] > 0:
                            dr, cr = (r['Amount'], 0) if "Payment" in v_mode else (0, r['Amount'])
                            conn.execute("INSERT INTO Transactions (Date, AccountName, PayeeName, Description, Debit, Credit) VALUES (?,?,?,?,?,?)",
                                         (str(t_date), method_name, r['Account'], r['Narration'], dr, cr))
                            conn.execute("UPDATE ChartOfAccounts SET Balance = Balance + ? WHERE AccountName = ?", (cr - dr, method_name))
                    conn.commit()
                st.success("Voucher Saved Successfully!")
                st.session_state.pmt_rows = [{"Account": "", "Amount": 0.0, "Narration": ""}]
                st.rerun()

    else: # --- JV ENTRY ---
        with st.container(border=True):
            jc1, jc2, jc3 = st.columns([1.5, 3, 1.5])
            jv_inv = jc1.text_input("Invoice No", placeholder="e.g. 22917")
            jv_date = jc1.date_input("Date", date.today(), key="jv_dt")
            jv_main_nar = jc2.text_area("Main Narration", height=90)
            if jc3.button("➕ Add Items", use_container_width=True, type="primary"):
                st.session_state.jv_rows.append({"Acc": "", "Dr": 0.0, "Cr": 0.0, "Nar": ""})
                st.rerun()

        updated_jv = []
        for i, row in enumerate(st.session_state.jv_rows):
            r1, r2, r3, r4, r5, r6 = st.columns([2.5, 1.2, 1.2, 1, 1, 2.5])
            acc = r1.selectbox(f"jv_acc_{i}", [""] + all_heads, key=f"jv_sel_{i}", label_visibility="collapsed")
            info = acc_df[acc_df['AccountName'] == acc]
            cur_bal = info['Balance'].iloc[0] if not info.empty else 0
            acc_type = info['AccountType'].iloc[0] if not info.empty else '-'
            r2.write(f"{cur_bal:,.0f}")
            r3.write(f"{acc_type}")
            dr = r4.number_input(f"dr_{i}", value=row['Dr'], key=f"jv_dr_{i}", label_visibility="collapsed")
            cr = r5.number_input(f"cr_{i}", value=row['Cr'], key=f"jv_cr_{i}", label_visibility="collapsed")
            nar = r6.text_input(f"nar_{i}", value=row['Nar'], key=f"jv_nar_{i}", label_visibility="collapsed")
            updated_jv.append({"Acc": acc, "Dr": dr, "Cr": cr, "Nar": nar})

        if st.button("✅ Post JV", type="primary", use_container_width=True):
            tdr, tcr = sum(x['Dr'] for x in updated_jv), sum(x['Cr'] for x in updated_jv)
            if tdr == tcr and tdr > 0:
                with db_connect() as conn:
                    for r in updated_jv:
                        if r['Acc'] != "":
                            conn.execute("INSERT INTO Transactions (Date, AccountName, Description, Debit, Credit) VALUES (?,?,?,?,?)",
                                         (str(jv_date), r['Acc'], r['Nar'] or jv_main_nar, r['Dr'], r['Cr']))
                            conn.execute("UPDATE ChartOfAccounts SET Balance = Balance + ? - ? WHERE AccountName = ?", (r['Dr'], r['Cr'], r['Acc']))
                    conn.commit()
                st.success("JV Posted Successfully!")
                st.session_state.jv_rows = [{"Acc": "", "Dr": 0.0, "Cr": 0.0, "Nar": ""}, {"Acc": "", "Dr": 0.0, "Cr": 0.0, "Nar": ""}]
                st.rerun()

# --- TAB 4: HISTORY (FIXED) ---
with tab4:
    st.subheader("📜 Recent History")
    with db_connect() as conn:
        # 'TransactionID' ko hata kar 'id' kiya gaya hai
        history = fetch_df(conn, "SELECT id, Date, AccountName, Description, Debit, Credit FROM Transactions ORDER BY id DESC LIMIT 30")
        if not history.empty:
            st.dataframe(history, use_container_width=True, hide_index=True)
            if st.button("🗑️ Delete Last Transaction"):
                conn.execute("DELETE FROM Transactions WHERE id = (SELECT MAX(id) FROM Transactions)")
                conn.commit()
                st.rerun()
        else:
            st.info("No Transactions found.")
