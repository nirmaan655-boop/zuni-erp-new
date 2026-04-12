import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta

st.set_page_config(layout="wide")
st.title("🐄 LIVESTOCK MANAGEMENT PRO")

# FETCH DATA FOR DROPDOWNS
with db_connect() as conn:
    all_animals = fetch_df(None, "SELECT * FROM AnimalMaster")
    active_tags = all_animals[all_animals['Status'].isin(['Active', 'Sick', 'Lactating'])]['TagID'].tolist()
    inv_items = fetch_df(None, "SELECT ItemName, Category, Cost FROM ItemMaster")
    semen = inv_items[inv_items['Category'] == 'Semen Straws']['ItemName'].tolist()
    meds = inv_items[inv_items['Category'] == 'Medicine']

tabs = st.tabs(["📋 INVENTORY", "🥛 MILK (3-SHIFT)", "🧬 BREEDING", "🩺 HOSPITAL", "📉 REMOVAL"])

with tabs[0]: # INVENTORY
    st.dataframe(all_animals, use_container_width=True)

with tabs[1]: # MILK PRODUCTION
    with st.form("milk_f"):
        c1, c2 = st.columns(2)
        m_tag = c1.selectbox("Select Animal", active_tags)
        m_date = c2.date_input("Date", date.today())
        s1, s2, s3 = st.columns(3)
        morning = s1.number_input("Morning")
        noon = s2.number_input("Noon")
        evening = s3.number_input("Evening")
        if st.form_submit_button("Save Milk"):
            total = morning + noon + evening
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction VALUES (?,?,?,?,?,?)", (str(m_date), m_tag, morning, noon, evening, total))
                conn.commit()
            st.rerun()
    st.dataframe(fetch_df(None, "SELECT * FROM MilkProduction ORDER BY Date DESC"), use_container_width=True)

with tabs[2]: # BREEDING
    with st.form("breed_f"):
        b_tag = st.selectbox("Cow Tag", active_tags)
        b_mode = st.radio("Mode", ["AI", "Natural"], horizontal=True)
        s_source = st.selectbox("Semen/Bull Name", semen if b_mode == "AI" else active_tags)
        if st.form_submit_button("Record Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Type, Semen, PD_Status) VALUES (?,?,?,?,?)", 
                             (str(date.today()), b_tag, b_mode, s_source, "Pending"))
                if b_mode == "AI":
                    conn.execute("UPDATE ItemMaster SET Quantity = Quantity - 1 WHERE ItemName=?", (s_source,))
                conn.commit()
            st.success("Breeding & Inventory Updated!")

with tabs[3]: # HOSPITAL (MULTI-MED)
    with st.form("hosp_f"):
        h_tag = st.selectbox("Sick Animal", active_tags)
        dis = st.text_input("Disease")
        total_cost = 0
        for i in range(2): # 2 Medicines for demo
            m_col, q_col = st.columns(2)
            m_name = m_col.selectbox(f"Medicine {i+1}", ["None"] + meds['ItemName'].tolist())
            m_qty = q_col.number_input(f"Qty {i+1}")
            if m_name != "None":
                rate = meds[meds['ItemName'] == m_name]['Cost'].iloc[0]
                total_cost += (rate * m_qty)
        if st.form_submit_button("Post Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Disease, TotalCost, Status) VALUES (?,?,?,?,?)", (str(date.today()), h_tag, dis, total_cost, "Under Treatment"))
                conn.commit()
            st.rerun()
