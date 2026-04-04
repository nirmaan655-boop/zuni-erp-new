import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date

# --- 0. DATABASE INITIALIZATION ---
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

# --- VIP BRANDING ---
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK PRO v5.0</h1>", unsafe_allow_html=True)

# --- GLOBAL DATA FETCH ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    try:
        meds = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster")
        med_dict = dict(zip(meds['ItemName'], meds['UOM']))
        med_list = ["None"] + list(med_dict.keys())
    except: med_list, med_dict = ["None"], {}

def show_history(table, tag=None):
    st.markdown(f"**📋 Recent {table}**")
    query = f"SELECT rowid as ID, * FROM {table}"
    if tag: query += f" WHERE TagID='{tag}' OR DamID='{tag}'"
    query += " ORDER BY rowid DESC LIMIT 5"
    with db_connect() as conn:
        df = fetch_df(conn, query)
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# --- 10 TABS SYSTEM ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# 1. 360 VIEW
with t1:
    st.dataframe(animal_data, use_container_width=True)

# 2. COW CARD (Full History)
with t2:
    sid = st.selectbox("Search Animal ID", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.subheader(f"🐄 {sid} | RFID: {row['RFID']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Breed", row['Breed']); c2.metric("Lactation", row['LactationNo']); c3.metric("Pen", row['CurrentPen'])
        st.divider()
        h1, h2, h3 = st.tabs(["Breeding & Calving", "Medical", "Milk Production"])
        with h1: show_history("BreedingLogs", sid); show_history("CalvingLogs", sid)
        with h2: show_history("TreatmentLogs", sid); show_history("VacLogs", sid)
        with h3: show_history("MilkLogs", sid)

# 3. MILK
with t3:
    with st.form("mf"):
        tag = st.selectbox("Tag", tag_list); d = st.date_input("Date")
        c1, c2, c3 = st.columns(3); m = c1.number_input("M"); n = c2.number_input("N"); e = c3.number_input("E")
        if st.form_submit_button("Save"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
                conn.commit(); st.rerun()
    show_history("MilkLogs")

# 4. TREATMENT
with t4:
    with st.form("tf"):
        tag = st.selectbox("Patient", tag_list); cols = st.columns(4); ins = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Inj {i+1}", med_list, key=f"m{i}")
                q = st.number_input(f"Qty {i+1}", key=f"q{i}")
                u = med_dict.get(m, "-"); st.caption(f"UOM: {u}"); ins.extend([m, q, u])
        rem = st.text_area("Symptoms")
        if st.form_submit_button("Log"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *ins, rem))
                conn.commit(); st.rerun()
    show_history("TreatmentLogs")

# 5. BREEDING
with t5:
    with st.form("bf"):
        tag = st.selectbox("Cow", tag_list); act = st.selectbox("Action", ["AI", "PD", "Natural", "Dry Off"])
        heat = st.selectbox("Heat Status", ["Natural", "Ovsynch", "G6G", "Pre-synch"])
        pd_r = st.selectbox("PD Result", ["N/A", "Pregnant (+)", "Empty (-)", "Abortion"])
        if st.form_submit_button("Save"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), tag, act, heat, "Straw", 1, pd_r, "Vet"))
                conn.commit(); st.rerun()
    show_history("BreedingLogs")

# 6. CALVING (Twins Option Fixed)
with t6:
    with st.form("cf"):
        dam = st.selectbox("Dam ID", tag_list); ctype = st.radio("Type", ["Single", "Twins"], horizontal=True)
        res = st.selectbox("Result", ["Live Birth", "Stillborn", "Abortion"])
        col1, col2 = st.columns(2)
        with col1:
            st.info("Calf 1"); c1t = st.text_input("Tag 1"); c1s = st.selectbox("Sex 1", ["Heifer", "Bull", "Freemartin"]); c1w = st.number_input("Weight 1")
        with col2:
            if ctype == "Twins":
                st.info("Calf 2"); c2t = st.text_input("Tag 2"); c2s = st.selectbox("Sex 2", ["Heifer", "Bull", "Freemartin"]); c2w = st.number_input("Weight 2")
            else: c2t, c2s, c2w = "N/A", "N/A", 0
        if st.form_submit_button("Register Calving"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), dam, res, ctype, c1t, c1s, c2t, c2s, c1w, c2w, 1))
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, BirthDate, Weight) VALUES (?,?,?,?)", (c1t, "Young", str(date.today()), c1w))
                if ctype == "Twins": conn.execute("INSERT INTO AnimalMaster (TagID, Category, BirthDate, Weight) VALUES (?,?,?,?)", (c2t, "Young", str(date.today()), c2w))
                conn.commit(); st.rerun()
    show_history("CalvingLogs")

# 7. WEIGHT (Last Weight Logic)
with t7:
    with st.form("wf"):
        tag = st.selectbox("Animal", tag_list)
        last_w = animal_data[animal_data['TagID']==tag]['Weight'].values[0] if tag else 0.0
        st.warning(f"Last Recorded Weight: {last_w} kg")
        cur_w = st.number_input("Current Weight", min_value=0.0)
        if st.form_submit_button("Update"):
            gain = cur_w - last_w
            with db_connect() as conn:
                conn.execute("INSERT INTO WeightLogs (Date, TagID, CurrentWeight, PreviousWeight, Gain) VALUES (?,?,?,?,?)", (str(date.today()), tag, cur_w, last_w, gain))
                conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (cur_w, tag))
                conn.commit(); st.rerun()
    show_history("WeightLogs")

# 8. VAC
with t8:
    with st.form("vf"):
        tags = st.multiselect("Select Animals", tag_list); vname = st.text_input("Vaccine"); dose = st.number_input("Dose")
        if st.form_submit_button("Log Vac"):
            with db_connect() as conn:
                conn.execute("INSERT INTO VacLogs VALUES (?,?,?,?,?)", (str(date.today()), str(tags), vname, dose, "Batch-A"))
                conn.commit(); st.rerun()
    show_history("VacLogs")

# 9. MOVE
with t9:
    with st.form("mvf"):
        tag = st.selectbox("Animal", tag_list); to_p = st.selectbox("To Pen", ["PEN-A", "DRY", "QUARANTINE"])
        if st.form_submit_button("Move"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET CurrentPen=? WHERE TagID=?", (to_p, tag))
                conn.commit(); st.rerun()

# 10. REGISTRATION (RFID + Sires)
with t10:
    with st.form("rf"):
        c1, c2 = st.columns(2); rtag = c1.text_input("Visual Tag"); rrfid = c2.text_input("RFID Number")
        breed = st.selectbox("Breed", ["HF", "Jersey", "Sahiwal", "Cross"]); bday = st.date_input("DOB")
        s1 = st.text_input("Sire (Father)"); s2 = st.text_input("G-Sire")
        if st.form_submit_button("Register"):
            with db_connect() as conn:
                conn.execute("INSERT INTO AnimalMaster (TagID, RFID, Breed, Category, Status, BirthDate, Sire1, Sire2) VALUES (?,?,?,?,?,?,?,?,?)",
                             (rtag, rrfid, breed, "Adult", "Active", str(bday), s1, s2))
                conn.commit(); st.success("Registered!"); st.rerun()
