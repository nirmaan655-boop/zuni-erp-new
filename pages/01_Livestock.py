import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")

# --- DATA FETCHING (SYNCED) ---
def get_herd_data():
    with db_connect() as conn:
        all_animals = fetch_df(conn, "SELECT * FROM AnimalMaster")
        # Sirf Active janwar dropdowns ke liye
        active_tags = all_animals[all_animals['Status'].isin(['Active', 'Sick', 'Lactating', 'Pregnant', 'Dry'])]['TagID'].tolist()
        return all_animals, active_tags

animals_df, active_tags = get_herd_data()

# --- BRANDING ---
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 LIVESTOCK MASTER CONTROL CENTER</h1>", unsafe_allow_html=True)

# --- TABS SYSTEM ---
tabs = st.tabs([
    "📋 INVENTORY", "🥛 MILK (3-TIME)", "🧬 BREEDING & PD", 
    "🩺 HOSPITAL", "📉 REMOVAL", "🚚 MOVEMENT", "📊 DASHBOARD"
])

# ================= 1. INVENTORY =================
with tabs[0]:
    st.subheader("Current Active Herd")
    st.dataframe(animals_df[animals_df['Status'] != 'Sold'], use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("📝 Quick Edit Animal")
    if active_tags:
        e1, e2, e3 = st.columns(3)
        e_tag = e1.selectbox("Select Tag", active_tags, key="inv_edit")
        e_wt = e2.number_input("New Weight (kg)", min_value=0.0)
        e_st = e3.selectbox("New Status", ["Active", "Lactating", "Dry", "Sick"])
        if st.button("Update Master"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Weight=?, Status=? WHERE TagID=?", (e_wt, e_st, e_tag))
                conn.commit()
            st.rerun()

# ================= 2. MILK PRODUCTION (3-TIME) =================
with tabs[1]:
    st.subheader("🥛 Animal-Wise Milk Entry (Morning/Noon/Evening)")
    with st.form("milk_form"):
        m1, m2, m3 = st.columns(3)
        m_tag = m1.selectbox("Select Animal", active_tags, key="milk_tag")
        m_date = m2.date_input("Date", date.today())
        
        c1, c2, c3 = st.columns(3)
        m_morn = c1.number_input("Morning (Ltr)", min_value=0.0)
        m_noon = c2.number_input("Noon (Ltr)", min_value=0.0)
        m_even = c3.number_input("Evening (Ltr)", min_value=0.0)
        
        if st.form_submit_button("Save Milk Record"):
            total = m_morn + m_noon + m_even
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction (Date, TagID, Morning, Noon, Evening, Total) VALUES (?,?,?,?,?,?)",
                             (str(m_date), m_tag, m_morn, m_noon, m_even, total))
                conn.commit()
            st.rerun()

    st.write("### 📜 Milk History")
    m_hist = fetch_df(None, "SELECT rowid as ID, * FROM MilkProduction ORDER BY Date DESC")
    st.dataframe(m_hist, use_container_width=True)
    if not m_hist.empty:
        if st.button("Delete Last Record"):
            with db_connect() as conn:
                conn.execute("DELETE FROM MilkProduction WHERE rowid=(SELECT MAX(rowid) FROM MilkProduction)")
                conn.commit()
            st.rerun()

# ================= 3. BREEDING & PD =================
with tabs[2]:
    st.subheader("🧬 Reproduction Records")
    with st.form("br_form"):
        b1, b2, b3 = st.columns(3)
        b_tag = b1.selectbox("Cow Tag", active_tags, key="br_tag")
        b_type = b2.selectbox("Type", ["AI", "Natural"])
        b_pd = b3.selectbox("PD Result", ["Pending", "Pregnant", "Open"])
        b_vet = b1.text_input("Vet Name")
        if st.form_submit_button("Save Breeding"):
            exp = str(date.today() + timedelta(days=280)) if b_pd == "Pregnant" else "N/A"
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Type, Vet, PD_Status, ExpectedCalving) VALUES (?,?,?,?,?,?)",
                             (str(date.today()), b_tag, b_type, b_vet, b_pd, exp))
                conn.commit()
            st.rerun()
    
    st.dataframe(fetch_df(None, "SELECT * FROM BreedingLogs ORDER BY Date DESC"), use_container_width=True)

# ================= 4. HOSPITAL (SICK BAY) =================
with tabs[3]:
    st.subheader("🩺 Hospital & Sick Recovery")
    with st.form("hosp_form"):
        h1, h2 = st.columns(2)
        h_tag = h1.selectbox("Animal", active_tags, key="hosp_tag")
        h_dis = h2.text_input("Disease")
        h_stat = h1.selectbox("Status", ["Sick", "Recovered"])
        if st.form_submit_button("Update Health"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Disease, Status) VALUES (?,?,?,?)",
                             (str(date.today()), h_tag, h_dis, h_stat))
                new_st = "Active" if h_stat == "Recovered" else "Sick"
                conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (new_st, h_tag))
                conn.commit()
            st.rerun()
    
    st.write("### 🏥 Current Patients")
    st.dataframe(fetch_df(None, "SELECT * FROM TreatmentLogs WHERE Status != 'Recovered'"), use_container_width=True)

# ================= 5. REMOVAL (DEATH/SOLD) =================
with tabs[4]:
    st.subheader("📉 Permanent Removal")
    with st.form("rem_form"):
        r1, r2 = st.columns(2)
        r_tag = r1.selectbox("Select Animal", active_tags, key="rem_tag")
        r_type = r2.selectbox("Reason", ["Sold", "Death", "Culled"])
        r_price = r1.number_input("Price (if Sold)", min_value=0)
        if st.form_submit_button("Confirm Removal"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (r_type, r_tag))
                conn.commit()
            st.rerun()
    
    st.write("### 📜 Removal History")
    st.dataframe(animals_df[animals_df['Status'].isin(['Sold', 'Death', 'Culled'])], use_container_width=True)

# ================= 6. MOVEMENT =================
with tabs[5]:
    st.subheader("🚚 Pen Movement")
    with st.form("mov_form"):
        m1, m2 = st.columns(2)
        m_tag = m1.selectbox("Animal", active_tags, key="m_tag")
        m_pen = m2.text_input("Target Pen/Shed")
        if st.form_submit_button("Move Animal"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MovementLogs (Date, TagID, ToPen) VALUES (?,?,?)", (str(date.today()), m_tag, m_pen))
                conn.commit()
            st.rerun()
    st.dataframe(fetch_df(None, "SELECT * FROM MovementLogs"), use_container_width=True)

# ================= 7. DASHBOARD =================
with tabs[6]:
    if not animals_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Herd", len(animals_df))
        c2.metric("Active Milkable", len(animals_df[animals_df['Status'] == 'Lactating']))
        c3.metric("Sick Animals", len(animals_df[animals_df['Status'] == 'Sick']))
        
        fig = px.pie(animals_df, names='Status', title="Herd Composition")
        st.plotly_chart(fig, use_container_width=True)
