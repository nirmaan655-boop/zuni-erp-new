import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")

# --- DATA FETCHING (MASTER SYNC) ---
with db_connect() as conn:
    animals_df = fetch_df(conn, "SELECT * FROM AnimalMaster")
    # Status wise filter for dropdowns
    active_tags = animals_df[animals_df['Status'].isin(['Active', 'Sick', 'Lactating', 'Pregnant', 'Dry'])]['TagID'].tolist() if not animals_df.empty else []
    bulls = animals_df[animals_df['Category'] == 'Bull']['TagID'].tolist() if not animals_df.empty else []
    
    # Inventory items
    inventory = fetch_df(conn, "SELECT ItemName, Category, UOM, Cost, Quantity FROM ItemMaster")
    medicines = inventory[inventory['Category'] == 'Medicine']
    semen_straws = inventory[inventory['Category'] == 'Semen Straws']['ItemName'].tolist() if not inventory.empty else []

st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 LIVESTOCK MASTER PRO CENTER</h1>", unsafe_allow_html=True)

tabs = st.tabs([
    "📊 COW CARD (P&L)", "🥛 MILK (3-SHIFT)", "🧬 BREEDING & PD", 
    "🐣 CALVING", "🩺 HOSPITAL", "🔍 ACTIVITY REPORTS"
])

# ================= 1. COW CARD (ANIMAL WISE P/L) =================
with tabs[0]:
    st.subheader("Performance & Profitability Analysis")
    if active_tags:
        sel_tag = st.selectbox("Select Animal", active_tags, key="p_l_tag")
        col1, col2, col3 = st.columns(3)
        
        # Milk Revenue (@ 210/Ltr)
        m_data = fetch_df(None, f"SELECT SUM(Total) as total FROM MilkProduction WHERE TagID='{sel_tag}'")
        total_milk = float(m_data['total'].iloc[0]) if not m_data.empty and m_data['total'].iloc[0] else 0.0
        revenue = total_milk * 210
        
        # Treatment Cost
        t_data = fetch_df(None, f"SELECT SUM(TotalCost) as cost FROM TreatmentLogs WHERE TagID='{sel_tag}'")
        med_cost = float(t_data['cost'].iloc[0]) if not t_data.empty and t_data['cost'].iloc[0] else 0.0
        
        col1.metric("Total Milk (Ltr)", f"{total_milk:,.1f}")
        col2.metric("Net Revenue", f"Rs. {revenue:,.0f}")
        col3.metric("Medical Expense", f"Rs. {med_cost:,.0f}", delta=-med_cost)
        
        st.divider()
        st.dataframe(animals_df[animals_df['TagID'] == sel_tag], use_container_width=True)
    else:
        st.warning("Inventory khali hai. Procurement se janwar add karein.")

# ================= 2. MILK PRODUCTION (3-TIME) =================
with tabs[1]:
    st.subheader("Daily Yield Entry")
    with st.form("milk_form", clear_on_submit=True):
        m1, m2 = st.columns(2)
        tag = m1.selectbox("Animal", active_tags, key="m_tag")
        dt = m2.date_input("Date", date.today())
        c1, c2, c3 = st.columns(3)
        m_m = c1.number_input("Morning", 0.0)
        m_n = c2.number_input("Noon", 0.0)
        m_e = c3.number_input("Evening", 0.0)
        if st.form_submit_button("Save Production"):
            total = m_m + m_n + m_e
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction VALUES (?,?,?,?,?,?)", (str(dt), tag, m_m, m_n, m_e, total))
                conn.commit()
            st.rerun()
    st.write("### Recent Production History")
    st.dataframe(fetch_df(None, "SELECT * FROM MilkProduction ORDER BY Date DESC LIMIT 10"), use_container_width=True)

# ================= 3. BREEDING & PD =================
with tabs[2]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("New Breeding Record")
        with st.form("breed_f"):
            b_tag = st.selectbox("Cow Tag", active_tags, key="br_cow")
            mode = st.radio("Mode", ["AI (Straw)", "Natural (Bull)"], horizontal=True)
            source = st.selectbox("Semen/Bull Name", semen_straws if mode=="AI (Straw)" else bulls)
            if st.form_submit_button("Save Breeding"):
                with db_connect() as conn:
                    conn.execute("INSERT INTO BreedingLogs (Date, TagID, Type, Semen, PD_Status) VALUES (?,?,?,?,?)", (str(date.today()), b_tag, mode, source, "Pending"))
                    if mode == "AI (Straw)":
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - 1 WHERE ItemName=?", (source,))
                    conn.commit()
                st.success("Breeding & Inventory Updated!")
    with col2:
        st.subheader("PD Diagnosis")
        pending = fetch_df(None, "SELECT TagID, Date FROM BreedingLogs WHERE PD_Status='Pending'")
        if not pending.empty:
            with st.form("pd_f"):
                p_tag = st.selectbox("Cow for PD", pending['TagID'].tolist())
                res = st.radio("Result", ["Pregnant", "Open", "Repeat"])
                if st.form_submit_button("Update Status"):
                    exp = str((date.today() + timedelta(days=280))) if res == "Pregnant" else "N/A"
                    with db_connect() as conn:
                        conn.execute("UPDATE BreedingLogs SET PD_Status=?, ExpectedCalving=? WHERE TagID=? AND PD_Status='Pending'", (res, exp, p_tag))
                        new_st = "Pregnant" if res == "Pregnant" else "Active"
                        conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (new_st, p_tag))
                        conn.commit()
                    st.rerun()
        else: st.info("No pending PD.")

# ================= 4. CALVING (PRO) =================
with tabs[3]:
    st.subheader("Calving Registration")
    preg_cows = animals_df[animals_df['Status'] == 'Pregnant']['TagID'].tolist()
    if preg_cows:
        with st.form("calv_f"):
            c_cow = st.selectbox("Mother Tag", preg_cows)
            is_twins = st.checkbox("Twins?")
            g1 = st.selectbox("Gender", ["Female", "Male"])
            w1 = st.number_input("Weight (kg)", 25.0)
            if st.form_submit_button("Register Calf"):
                with db_connect() as conn:
                    conn.execute("UPDATE AnimalMaster SET Status='Lactating' WHERE TagID=?", (c_cow,))
                    conn.execute("INSERT INTO AnimalMaster (TagID, Category, Status, Weight, PurchaseDate) VALUES (?,?,?,?,?)", (f"C-{c_cow}-1", "Calf", "Active", w1, str(date.today())))
                    conn.commit()
                st.balloons()
    else: st.info("No pregnant cows found.")

# ================= 5. HOSPITAL (MULTI-MED) =================
with tabs[4]:
    st.subheader("Hospital & Sick Bay")
    with st.form("hosp_pro"):
        h_tag = st.selectbox("Animal", active_tags, key="h_tag")
        dis = st.text_input("Disease Name")
        med_list = medicines['ItemName'].tolist() if not medicines.empty else ["No Med"]
        t_cost = 0
        for i in range(2):
            m1, q1 = st.columns(2)
            m_n = m1.selectbox(f"Medicine {i+1}", ["None"] + med_list)
            m_q = q1.number_input(f"Qty {i+1}", 0.0)
            if m_n != "None":
                rate = medicines[medicines['ItemName'] == m_n]['Cost'].iloc[0]
                t_cost += (rate * m_q)
                with db_connect() as conn: conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName=?", (m_q, m_n))
        if st.form_submit_button("Post Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Disease, TotalCost, Status) VALUES (?,?,?,?,?)", (str(date.today()), h_tag, dis, t_cost, "Under Treatment"))
                conn.commit()
            st.rerun()

# ================= 6. ACTIVITY REPORTS (DATE-TO-DATE) =================
with tabs[5]:
    st.subheader("🔍 Date-Wise Activity Audit")
    c1, c2 = st.columns(2)
    s_d = c1.date_input("Start", date.today() - timedelta(days=30))
    e_d = c2.date_input("End", date.today())
    if st.button("Search Records"):
        logs = fetch_df(None, f"SELECT Date, TagID, 'Milk' as Activity, Total as Detail FROM MilkProduction WHERE Date BETWEEN '{s_d}' AND '{e_d}'")
        st.dataframe(logs, use_container_width=True)
