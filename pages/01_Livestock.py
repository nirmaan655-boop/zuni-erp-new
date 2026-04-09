import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date

# --- 0. DATABASE INITIALIZATION (SAB TABLES MUKAMMAL) ---
def init_livestock_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY, RFID TEXT, Breed TEXT, Category TEXT, CurrentPen TEXT, 
            Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT, Sire1 TEXT, Sire2 TEXT)""")
        
        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL, LactNo INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, CurrentWeight REAL, PreviousWeight REAL, Gain REAL, DaysGap INTEGER, AvgDailyGain REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)")
        conn.commit()

init_livestock_db()

# --- 1. BRANDING ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK PRO <span style='color: #FF851B;'>v7.0</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete Farm Management System</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    bull_list = animal_data[animal_data['Category'] == 'Bull']['TagID'].tolist()
    try:
        items = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster")
        med_dict = dict(zip(items['ItemName'], items['UOM']))
    except: med_dict = {}
    med_list = ["None"] + list(med_dict.keys())

def show_history(table, tag=None):
    st.markdown(f"**📋 Recent {table} Records**")
    query = f"SELECT * FROM {table}"
    if tag: query += f" WHERE TagID='{tag}' OR DamID='{tag}'"
    query += " ORDER BY rowid DESC LIMIT 5"
    with db_connect() as conn:
        df = fetch_df(conn, query)
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

with t1:
    st.subheader("All Animals Overview")
    st.dataframe(animal_data, use_container_width=True)

with t3: # Milk
    with st.form("milk_f"):
        tag = st.selectbox("Tag ID", tag_list); d = st.date_input("Date", date.today())
        c1, c2, c3 = st.columns(3); m = c1.number_input("Morning"); n = c2.number_input("Noon"); e = c3.number_input("Evening")
        if st.form_submit_button("✅ Save Milk Data"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
                conn.commit(); st.rerun()
    show_history("MilkLogs")

with t4: # Treatment
    with st.form("treat_f"):
        tag = st.selectbox("Select Patient", tag_list)
        cols = st.columns(4); t_ins = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Injection {i+1}", med_list, key=f"tm{i}")
                q = st.number_input(f"Qty {i+1}", key=f"tq{i}")
                u = med_dict.get(m, "-"); st.caption(f"UOM: {u}"); t_ins.extend([m, q, u])
        if st.form_submit_button("💉 Log Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Med1, Qty1, UOM1, Med2, Qty2, UOM2, Med3, Qty3, UOM3, Med4, Qty4, UOM4, Symptoms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *t_ins, "Standard"))
                conn.commit(); st.rerun()
    show_history("TreatmentLogs")

# --- TAB 5: UPDATED BREEDING LOGIC ---
with t5:
    st.subheader("🧬 Breeding & PD Control")
    with st.form("breed_f"):
        tag = st.selectbox("Cow Tag", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service", "Dry Off"])
        
        # Dynamic Options
        heat, semen, pdr, bull = "N/A", "N/A", "N/A", "N/A"
        
        if act == "Insemination (AI)":
            c1, c2 = st.columns(2)
            heat = c1.selectbox("Heat Status", ["Natural", "Ovsynch", "Silent Heat"])
            semen = c2.text_input("Semen Name/Batch")
        elif act == "PD Check":
            pdr = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        elif act == "Natural Service":
            bull = st.selectbox("Select Bull (from Farm)", bull_list if bull_list else ["No Bull Found"])
            
        vet = st.text_input("Vet Name", "Dr. Zuni")
        
        if st.form_submit_button("🧬 Save Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), tag, act, heat, semen, 1, pdr, vet))
                if pdr == "Pregnant (+)":
                    conn.execute("UPDATE AnimalMaster SET Status = 'Pregnant' WHERE TagID = ?", (tag,))
                conn.commit(); st.rerun()
    show_history("BreedingLogs")

# --- TAB 6: UPDATED CALVING (TWINS) ---
with t6:
    st.subheader("🍼 Calving Registration")
    with st.form("calv_f"):
        dam = st.selectbox("Dam ID", tag_list)
        ctype = st.radio("Birth Type", ["Single", "Twins"], horizontal=True)
        res = st.selectbox("Result", ["Live Birth", "Stillborn"])
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Calf 1**")
            c1t = st.text_input("Tag 1"); c1s = st.selectbox("Sex 1", ["Heifer", "Bull"]); c1w = st.number_input("Weight 1")
        c2t, c2s, c2w = "N/A", "N/A", 0
        if ctype == "Twins":
            with col2:
                st.markdown("**Calf 2**")
                c2t = st.text_input("Tag 2"); c2s = st.selectbox("Sex 2", ["Heifer", "Bull"]); c2w = st.number_input("Weight 2")
        
        if st.form_submit_button("🍼 Register Birth"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), dam, res, ctype, c1t, c1s, c2t, c2s, c1w, c2w, 1))
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?, 'Calf', 'Active')", (c1t,))
                if ctype == "Twins":
                    conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?, 'Calf', 'Active')", (c2t,))
                conn.commit(); st.success("Calving Registered!"); st.rerun()
    show_history("CalvingLogs")

with t10: # Registration
    with st.form("reg_animal"):
        new_tag = st.text_input("Tag ID").upper()
        breed = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        cat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        if st.form_submit_button("✅ Register Animal"):
            with db_connect() as conn:
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Breed, Category, Status) VALUES (?,?,?,?)", (new_tag, breed, cat, "Active"))
                conn.commit(); st.rerun()
