import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date

# --- 0. DATABASE CONNECTION & AUTO-REPAIR ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Tables and Columns Ensure karna (Repair Logic)
    queries = [
        "CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, RFID TEXT, Breed TEXT, Category TEXT, CurrentPen TEXT, Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0, BirthDate TEXT, Sire1 TEXT, Sire2 TEXT)",
        "CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)",
        "CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT)",
        "CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL, LactNo INTEGER)",
        "CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)",
        "CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, CurrentWeight REAL, PreviousWeight REAL, Gain REAL, DaysGap INTEGER, AvgDailyGain REAL)",
        "CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)",
        "CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)"
    ]
    for q in queries:
        conn.execute(q)
    conn.commit()
    return conn

conn = get_connection()

# --- 1. BRANDING ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Master")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; text-align: center; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK <span style='color: #FF851B;'>PRO v8.5</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete 10-Tab Master System | Twins & AI Logic</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
animal_data = pd.read_sql("SELECT * FROM AnimalMaster", conn)
tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
bull_list = animal_data[animal_data['Category'] == 'Bull']['TagID'].tolist()

try:
    items_df = pd.read_sql("SELECT ItemName, UOM, Category FROM ItemMaster", conn)
    med_dict = dict(zip(items_df['ItemName'], items_df['UOM']))
    semen_items = items_df[items_df['Category'] == 'Semen Straws']['ItemName'].tolist()
except:
    med_dict, semen_items = {}, ["Imported", "Local"]

def show_history(table, tag=None):
    st.markdown(f"**📋 Recent {table} Records**")
    query = f"SELECT * FROM {table}"
    if tag: query += f" WHERE TagID='{tag}' OR DamID='{tag}'"
    query += " ORDER BY rowid DESC LIMIT 5"
    df = pd.read_sql(query, conn)
    if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# TAB 1: 360 VIEW
with t1:
    st.subheader("Herd Status")
    st.dataframe(animal_data, use_container_width=True)

# TAB 2: COW CARD
with t2:
    sid = st.selectbox("Select Animal ID", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.markdown(f"### 🐄 Tag: {sid} | Breed: {row['Breed']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight", f"{row['Weight']} kg"); c2.metric("Lactation", row['LactationNo']); c3.metric("Status", row['Status'])
        show_history("MilkLogs", sid); show_history("TreatmentLogs", sid)

# TAB 3: MILK
with t3:
    with st.form("milk_f"):
        tag = st.selectbox("Tag ID", tag_list); d = st.date_input("Date", date.today())
        c1, c2, c3 = st.columns(3); m = c1.number_input("Morning"); n = c2.number_input("Noon"); e = c3.number_input("Evening")
        if st.form_submit_button("Save Milk"):
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
            conn.commit(); st.rerun()
    show_history("MilkLogs")

# TAB 4: TREATMENT
with t4:
    with st.form("treat_f"):
        tag = st.selectbox("Patient", tag_list); t_ins = []
        cols = st.columns(4)
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Med {i+1}", ["None"] + list(med_dict.keys()), key=f"t{i}")
                q = st.number_input(f"Qty {i+1}", key=f"q{i}")
                u = med_dict.get(m, "-"); t_ins.extend([m, q, u])
        if st.form_submit_button("Log Treatment"):
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *t_ins, "Routine"))
            conn.commit(); st.rerun()

# TAB 5: BREEDING (DYNAMIC)
with t5:
    with st.form("breed_f"):
        tag = st.selectbox("Cow Tag", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service", "Dry Off"])
        heat, sem, qty, pdr, bull = "N/A", "N/A", 0, "N/A", "N/A"
        if act == "Insemination (AI)":
            c1, c2 = st.columns(2); sem = c1.selectbox("Semen", semen_items); qty = c2.number_input("Dose", 1)
        elif act == "PD Check": pdr = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        elif act == "Natural Service": bull = st.selectbox("Select Bull", bull_list if bull_list else ["No Bull Registered"])
        if st.form_submit_button("Save Breeding"):
            conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), tag, act, "Natural", sem, qty, pdr, "Dr. Zuni"))
            conn.commit(); st.rerun()

# TAB 6: CALVING (TWINS)
with t6:
    with st.form("calv_f"):
        dam = st.selectbox("Dam ID", tag_list); ctype = st.radio("Type", ["Single", "Twins"], horizontal=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            c1t = st.text_input("Calf 1 Tag"); c1s = st.selectbox("Sex 1", ["Heifer", "Bull"]); c1w = st.number_input("Weight 1", 30.0)
        c2t, c2s, c2w = "N/A", "N/A", 0
        if ctype == "Twins":
            with col2:
                c2t = st.text_input("Calf 2 Tag"); c2s = st.selectbox("Sex 2", ["Heifer", "Bull"]); c2w = st.number_input("Weight 2", 28.0)
        if st.form_submit_button("Register Birth"):
            conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), dam, "Live", ctype, c1t, c1s, c2t, c2s, c1w, c2w, 1))
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Weight, Status) VALUES (?,?,'Calf','Active')", (c1t, c1w))
            if ctype == "Twins": conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Weight, Status) VALUES (?,?,'Calf','Active')", (c2t, c2w))
            conn.commit(); st.rerun()

# TAB 7-9 (WEIGHT, VAC, MOVE)
with t7:
    w_tag = st.selectbox("Animal", [""] + tag_list, key="wt")
    if w_tag:
        cur_w = st.number_input("New Weight")
        if st.button("Update Weight"):
            conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (cur_w, w_tag)); conn.commit(); st.rerun()

# TAB 10: REGISTRATION
with t10:
    with st.form("reg"):
        rtag = st.text_input("New Tag ID").upper()
        rcat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        rbrd = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        if st.form_submit_button("Register Animal"):
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Breed, Category, Status) VALUES (?,?,?,?)", (rtag, rbrd, rcat, 'Active'))
            conn.commit(); st.rerun()
