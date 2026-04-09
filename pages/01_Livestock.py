import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date, timedelta

# --- 0. DATABASE INITIALIZATION ---
def init_livestock_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY, RFID TEXT, Breed TEXT, Category TEXT, CurrentPen TEXT, 
            Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT, Sire1 TEXT, Sire2 TEXT, LastWeight REAL DEFAULT 0)""")
        
        # Tables Ensure Karna
        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT, ExpCalving TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL, LactNo INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, Weight REAL, PrevWeight REAL, DateLogged TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)")
        conn.commit()

init_livestock_db()

# --- 1. BRANDING ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK PRO <span style='color: #FF851B;'>v11.0</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete Farm & Inventory Management System</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    bull_list = animal_data[animal_data['Category'] == 'Bull']['TagID'].tolist()

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# --- TAB 1: 360° VIEW ---
with t1:
    st.subheader("Herd Summary")
    st.dataframe(animal_data, use_container_width=True)

# --- TAB 2: COW CARD (FULL HISTORY) ---
with t2:
    sid = st.selectbox("Select Animal to View Card", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.markdown(f"### 🐄 {sid} | {row['Status']} | {row['Breed']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Weight", f"{row['Weight']} kg")
        c2.metric("Birth Date", row['BirthDate'])
        c3.metric("Lactation", row['LactationNo'])
        c4.metric("Category", row['Category'])
        
        st.divider()
        st.subheader("📋 Detailed History")
        h1, h2, h3, h4 = st.tabs(["Medical/Vaccine", "Breeding", "Weight Logs", "Milk Production"])
        with h1:
            with db_connect() as conn:
                st.dataframe(fetch_df(conn, f"SELECT * FROM TreatmentLogs WHERE TagID='{sid}'"), use_container_width=True)
                st.dataframe(fetch_df(conn, f"SELECT * FROM VacLogs WHERE TagIDs LIKE '%{sid}%'"), use_container_width=True)
        with h2:
            with db_connect() as conn:
                st.dataframe(fetch_df(conn, f"SELECT * FROM BreedingLogs WHERE TagID='{sid}'"), use_container_width=True)
        with h3:
            with db_connect() as conn:
                st.dataframe(fetch_df(conn, f"SELECT Date, Weight, PrevWeight FROM WeightLogs WHERE TagID='{sid}'"), use_container_width=True)
        with h4:
            with db_connect() as conn:
                st.dataframe(fetch_df(conn, f"SELECT Date, Total FROM MilkLogs WHERE TagID='{sid}'"), use_container_width=True)

# --- TAB 5: BREEDING (WITH EXPECTED CALVING) ---
with t5:
    with st.form("breed_f"):
        tag = st.selectbox("Select Cow", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service"])
        pdr = st.radio("PD Result", ["N/A", "Pregnant (+)", "Empty (-)"], horizontal=True)
        
        # Logic for Exp Calving Date (9 months approx 280 days)
        exp_date = (date.today() + timedelta(days=280)).strftime('%Y-%m-%d') if pdr == "Pregnant (+)" else "N/A"
        
        if st.form_submit_button("🧬 Save Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Action, PD_Result, ExpCalving) VALUES (?,?,?,?,?)", 
                             (str(date.today()), tag, act, pdr, exp_date))
                if pdr == "Pregnant (+)":
                    conn.execute("UPDATE AnimalMaster SET Status = 'Pregnant' WHERE TagID = ?", (tag,))
                conn.commit()
                st.success(f"Saved! Expected Calving: {exp_date}")
                st.rerun()

# --- TAB 10: ADVANCED REGISTRATION ---
with t10:
    st.subheader("📝 Complete Animal Registration")
    with st.form("reg_final"):
        c1, c2, c3 = st.columns(3)
        rtag = c1.text_input("Tag ID").upper()
        rcat = c2.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        rbrd = c3.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross", "Friesian"])
        
        c4, c5, c6 = st.columns(3)
        rbirth = c4.date_input("Date of Birth", date(2022, 1, 1))
        rw = c5.number_input("Current Weight", value=0.0)
        rstat = c6.selectbox("Current Status", ["Milking", "Dry", "Pregnant", "Young Stock"])
        
        if st.form_submit_button("✅ Register Animal"):
            if rtag:
                with db_connect() as conn:
                    conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Breed, Category, BirthDate, Weight, Status) VALUES (?,?,?,?,?,?)", 
                                 (rtag, rbrd, rcat, str(rbirth), rw, rstat))
                    conn.commit()
                st.success(f"{rtag} registered successfully!")
                st.rerun()

# --- SAB TABS MEIN HISTORY DIKHANA ---
def show_bottom_history(table):
    st.divider()
    st.write(f"**Recent {table} Entries**")
    with db_connect() as conn:
        st.dataframe(fetch_df(conn, f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 5"), use_container_width=True)

# Milk, Treat, Weight wagera mein purana logic use karein aur end mein show_bottom_history call karein.
