import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta

# --- 1. DATABASE INITIALIZATION (AUTO-RECOVERY) ---
def init_db():
    with db_connect() as conn:
        cursor = conn.cursor()
        # Tables create karne ka logic
        cursor.execute("CREATE TABLE IF NOT EXISTS PensMaster (PenName TEXT PRIMARY KEY, Capacity INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, Category TEXT, Status TEXT, Weight REAL, PurchaseDate TEXT, Pen TEXT DEFAULT 'General', Remarks TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS MilkProduction (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Issue TEXT, Medicine TEXT, TotalCost REAL, Vet TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Type TEXT, Semen TEXT, PD_Status TEXT, ExpectedCalving TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS ItemMaster (ItemName TEXT PRIMARY KEY, Category TEXT, Quantity REAL, UOM TEXT, Cost REAL)")
        conn.commit()

init_db()

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")

# --- DATA SYNC ---
with db_connect() as conn:
    animals_df = fetch_df(conn, "SELECT * FROM AnimalMaster")
    active_tags = animals_df[animals_df['Status'].isin(['Active', 'Sick', 'Lactating', 'Pregnant', 'Dry'])]['TagID'].tolist() if not animals_df.empty else []
    inventory = fetch_df(conn, "SELECT * FROM ItemMaster")
    meds_info = inventory[inventory['Category'] == 'Medicine']
    pens_df = fetch_df(conn, "SELECT * FROM PensMaster")
    pens_list = pens_df['PenName'].tolist() if not pens_df.empty else ["General"]

st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK CONTROL</h1>", unsafe_allow_html=True)

tabs = st.tabs(["📊 COW CARD", "🥛 MILK", "🧬 BREEDING", "🩺 HOSPITAL", "🏠 PENS", "🐣 CALVING", "📉 REMOVAL"])

# ================= 1. COW CARD (P&L) =================
with tabs[0]:
    st.subheader("Performance & Profitability")
    if active_tags:
        sel_tag = st.selectbox("Select Animal", active_tags, key="p_l_tag")
        m_data = fetch_df(None, f"SELECT SUM(Total) as total FROM MilkProduction WHERE TagID='{sel_tag}'")
        total_milk = float(m_data['total'].iloc[0]) if not m_data.empty and m_data['total'].iloc[0] is not None else 0.0
        t_data = fetch_df(None, f"SELECT SUM(TotalCost) as cost FROM TreatmentLogs WHERE TagID='{sel_tag}'")
        med_cost = float(t_data['cost'].iloc[0]) if not t_data.empty and t_data['cost'].iloc[0] is not None else 0.0

        rev = total_milk * 210 
        profit = rev - med_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Milk (Ltr)", f"{total_milk:,.1f}")
        c2.metric("Med Expense", f"Rs. {med_cost:,.0f}")
        c3.metric("Net Profit", f"Rs. {profit:,.0f}", delta=float(profit))
        st.dataframe(animals_df[animals_df['TagID'] == sel_tag], use_container_width=True)
    else: st.warning("Animal record khali hai.")

# ================= 2. MILK =================
with tabs[1]:
    st.subheader("Milk Entry")
    with st.form("milk_f", clear_on_submit=True):
        m1, m2 = st.columns(2); tag = m1.selectbox("Animal", active_tags); dt = m2.date_input("Date", date.today())
        s1, s2, s3 = st.columns(3); m_v = s1.number_input("Morning", 0.0); n_v = s2.number_input("Noon", 0.0); e_v = s3.number_input("Evening", 0.0)
        if st.form_submit_button("Save"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction VALUES (?,?,?,?,?,?)", (str(dt), tag, m_v, n_v, e_v, m_v+n_v+e_v))
                conn.commit()
            st.rerun()

# ================= 3. BREEDING =================
with tabs[2]:
    st.subheader("🧬 Breeding Bank")
    with st.form("br_form"):
        b1, b2, b3 = st.columns(3)
        b_tag = b1.selectbox("Animal", active_tags)
        b_mode = b2.radio("Mode", ["AI (Straw)", "Natural"])
        straw = b3.text_input("Semen/Bull Name")
        b_pd = b2.selectbox("PD Status", ["Pending", "Pregnant", "Open"])
        if st.form_submit_button("Record Breeding"):
            exp = str(date.today() + timedelta(days=280)) if b_pd == "Pregnant" else "N/A"
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)", (str(date.today()), b_tag, b_mode, straw, b_pd, exp))
                if b_pd == "Pregnant": conn.execute("UPDATE AnimalMaster SET Status='Pregnant' WHERE TagID=?", (b_tag,))
                conn.commit()
            st.rerun()

# ================= 4. HOSPITAL (MULTI-MED & AUTO COST) =================
with tabs[3]:
    st.subheader("🩺 Hospital (4-Medicine Entry)")
    diseases = ["Mastitis", "Fever", "FMD", "Lumpy Skin", "Indigestion", "Injury"]
    with st.form("hosp_multi"):
        h1, h2 = st.columns(2)
        h_tag = h1.selectbox("Animal", active_tags); h_dis = h2.selectbox("Diagnosis", diseases)
        
        st.write("---")
        med_entries = []
        for i in range(4):
            c = st.columns([3, 2, 2])
            m_name = c[0].selectbox(f"Medicine {i+1}", ["None"] + meds_info['ItemName'].tolist(), key=f"med_{i}")
            # Auto fetch UOM and Cost
            uom = meds_info[meds_info['ItemName'] == m_name]['UOM'].iloc[0] if m_name != "None" else "Qty"
            m_qty = c[1].number_input(f"Qty ({uom})", min_value=0.0, key=f"qty_{i}")
            if m_name != "None" and m_qty > 0:
                cost = meds_info[meds_info['ItemName'] == m_name]['Cost'].iloc[0]
                med_entries.append({'name': m_name, 'qty': m_qty, 'total': m_qty * cost})
        
        h_vet = st.text_input("Vet Name"); h_status = st.selectbox("Current Status", ["Sick", "Active"])
        if st.form_submit_button("Save Treatment"):
            if med_entries:
                total_c = sum(m['total'] for m in med_entries)
                med_str = ", ".join([f"{m['name']}({m['qty']})" for m in med_entries])
                with db_connect() as conn:
                    conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?)", (str(date.today()), h_tag, h_dis, med_str, total_c, h_vet))
                    for m in med_entries: conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (m['qty'], m['name']))
                    conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (h_status, h_tag))
                    conn.commit()
                st.success(f"Cost: Rs. {total_c}"); st.rerun()

# ================= 5. PENS (NEW SYSTEM) =================
with tabs[4]:
    st.subheader("🏠 Pens & Sheds")
    p1, p2 = st.columns(2)
    with p1:
        with st.form("p_f"):
            pn = st.text_input("New Pen Name"); pc = st.number_input("Capacity", 1)
            if st.form_submit_button("Create Pen"):
                with db_connect() as conn:
                    conn.execute("INSERT OR IGNORE INTO PensMaster VALUES (?,?)", (pn, pc)); conn.commit()
                st.rerun()
    with p2:
        with st.form("m_f"):
            mt = st.selectbox("Animal", active_tags); mto = st.selectbox("Move to", pens_list)
            if st.form_submit_button("Transfer"):
                with db_connect() as conn:
                    conn.execute("UPDATE AnimalMaster SET Pen=? WHERE TagID=?", (mto, mt)); conn.commit()
                st.rerun()

# ================= 6. CALVING =================
with tabs[5]:
    st.subheader("🐣 Birth Registration")
    p_cows = animals_df[animals_df['Status'] == 'Pregnant']['TagID'].tolist()
    with st.form("c_f"):
        mother = st.selectbox("Mother", p_cows if p_cows else ["None"])
        calf = st.text_input("Calf Tag ID")
        if st.form_submit_button("Register Calf"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status='Lactating' WHERE TagID=?", (mother,))
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, Status, PurchaseDate) VALUES (?,?,?,?)", (calf, "Calf", "Active", str(date.today())))
                conn.commit()
            st.rerun()

# ================= 7. REMOVAL =================
with tabs[6]:
    st.subheader("📉 Removal")
    with st.form("r_f"):
        rt = st.selectbox("Animal", active_tags); reas = st.radio("Reason", ["Sold", "Death"])
        if st.form_submit_button("Confirm"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (reas, rt)); conn.commit()
            st.rerun()
