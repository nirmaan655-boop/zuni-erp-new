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

# --- 1. BRANDING & UI ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK PRO <span style='color: #FF851B;'>v7.0</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete 10-Tab Farm Management System</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    try:
        items = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster")
        med_dict = dict(zip(items['ItemName'], items['UOM']))
    except: med_dict = {}
    med_list = ["None"] + list(med_dict.keys())

def show_history(table, tag=None):
    st.markdown(f"**📋 Recent {table} Records**")
    query = f"SELECT rowid as ID, * FROM {table}"
    if tag: query += f" WHERE TagID='{tag}' OR DamID='{tag}'"
    query += " ORDER BY rowid DESC LIMIT 5"
    with db_connect() as conn:
        df = fetch_df(conn, query)
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# TAB 1: 360° VIEW
with t1:
    st.subheader("All Animals Overview")
    st.dataframe(animal_data, use_container_width=True)

# TAB 2: COW CARD (Full History Search)
with t2:
    sid = st.selectbox("Search Animal ID for Card", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc
        st.markdown(f"### 🐄 COW CARD: {sid} | RFID: {row['RFID']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Breed", row['Breed']); c2.metric("Lactation", row['LactationNo'])
        c3.metric("Current Weight", f"{row['Weight']} kg"); c4.metric("Status", row['Status'])
        st.divider()
        sub_t1, sub_t2, sub_t3 = st.tabs(["Breeding/Calving", "Medical History", "Production"])
        with sub_t1: show_history("BreedingLogs", sid); show_history("CalvingLogs", sid)
        with sub_t2: show_history("TreatmentLogs", sid); show_history("VacLogs", sid)
        with sub_t3: show_history("MilkLogs", sid)

# TAB 3: MILK LOGS
with t3:
    with st.form("milk_f"):
        tag = st.selectbox("Tag ID", tag_list); d = st.date_input("Date", date.today())
        c1, c2, c3 = st.columns(3); m = c1.number_input("Morning"); n = c2.number_input("Noon"); e = c3.number_input("Evening")
        if st.form_submit_button("✅ Save Milk Data"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
                conn.commit(); st.rerun()
    show_history("MilkLogs")

# TAB 4: TREATMENT (4 Injections + UOM)
with t4:
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
                conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *t_ins, "Standard Treatment"))
                conn.commit(); st.rerun()
    show_history("TreatmentLogs")

# TAB 5: BREEDING (Heat & PD)
with t5:
    with st.form("breed_f"):
        tag = st.selectbox("Cow Tag", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service", "Dry Off"])
        heat = st.selectbox("Heat Status", ["Natural", "Ovsynch", "G6G", "Pre-synch", "Silent Heat"])
        pd_r = st.selectbox("PD Result", ["N/A", "Pregnant (+)", "Empty (-)", "Abortion"])
        if st.form_submit_button("🧬 Save Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), tag, act, heat, "Semen", 1, pd_r, "Vet"))
                conn.commit(); st.rerun()
    show_history("BreedingLogs")

# TAB 6: CALVING (Twins Logic Fixed)
with t6:
    with st.form("calv_f"):
        dam = st.selectbox("Dam ID (Mother)", tag_list)
        ctype = st.radio("Birth Type", ["Single", "Twins"], horizontal=True)
        res = st.selectbox("Birth Result", ["Live Birth", "Stillborn", "Abortion"])
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Calf 1 Details**")
            c1t = st.text_input("Tag 1"); c1s = st.selectbox("Sex 1", ["Heifer", "Bull", "Freemartin"]); c1w = st.number_input("Birth Weight 1")
        c2t, c2s, c2w = "N/A", "N/A", 0
        if ctype == "Twins":
            with col2:
                st.markdown("**Calf 2 Details**")
                c2t = st.text_input("Tag 2"); c2s = st.selectbox("Sex 2", ["Heifer", "Bull", "Freemartin"]); c2w = st.number_input("Birth Weight 2")
        if st.form_submit_button("🍼 Register Birth"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), dam, res, ctype, c1t, c1s, c2t, c2s, c1w, c2w, 1))
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, BirthDate, Weight) VALUES (?,?,?,?)", (c1t, "Young", str(date.today()), c1w))
                if ctype == "Twins":
                    conn.execute("INSERT INTO AnimalMaster (TagID, Category, BirthDate, Weight) VALUES (?,?,?,?)", (c2t, "Young", str(date.today()), c2w))
                conn.commit(); st.success("Calving Success!"); st.rerun()
    show_history("CalvingLogs")

# TAB 7: WEIGHT (Last Weight Recovery Fixed)
with t7:
    st.subheader("Weight Monitoring")
    w_tag = st.selectbox("Select Animal for Weight", [""] + tag_list, key="w_tag_main")
    last_weight = 0.0
    if w_tag:
        with db_connect() as conn:
            res_w = fetch_df(conn, f"SELECT Weight FROM AnimalMaster WHERE TagID='{w_tag}'")
            if not res_w.empty: last_weight = float(res_w['Weight'].iloc)
    
    st.info(f"📊 **Last Recorded Weight: {last_weight} kg**")
    
    with st.form("weight_form"):
        cur_w = st.number_input("Enter New Weight", min_value=0.0)
        if st.form_submit_button("⚖️ Update Weight"):
            gain = cur_w - last_weight
            with db_connect() as conn:
                conn.execute("INSERT INTO WeightLogs (Date, TagID, CurrentWeight, PreviousWeight, Gain) VALUES (?,?,?,?,?)", (str(date.today()), w_tag, cur_w, last_weight, gain))
                conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (cur_w, w_tag))
                conn.commit(); st.success(f"Updated! Gain: {gain}kg"); st.rerun()
    show_history("WeightLogs")

# TAB 8: VACCINATION (Bulk)
with t8:
    with st.form("vac_f"):
        v_tags = st.multiselect("Select Animals", tag_list)
        v_name = st.text_input("Vaccine Name"); v_dose = st.number_input("Dose (ml)")
        if st.form_submit_button("💉 Bulk Log Vaccination"):
            with db_connect() as conn:
                conn.execute("INSERT INTO VacLogs VALUES (?,?,?,?,?)", (str(date.today()), str(v_tags), v_name, v_dose, "Batch-001"))
                conn.commit(); st.success("Vaccination Recorded!"); st.rerun()
    show_history("VacLogs")

# TAB 9: MOVEMENT (Pen Transfer)
with t9:
    with st.form("move_f"):
        m_tag = st.selectbox("Select Animal to Move", tag_list)
        to_pen = st.selectbox("New Pen Location", ["PEN-A", "PEN-B", "DRY-PEN", "CALF-PEN", "QUARANTINE"])
        if st.form_submit_button("🏠 Transfer Pen"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET CurrentPen=? WHERE TagID=?", (to_pen, m_tag))
                conn.commit(); st.success("Moved Successfully!"); st.rerun()

# TAB 10: REGISTRATION (RFID & Pedigree)
with t10:
    with st.form("reg_f"):
        col1, col2 = st.columns(2)
        r_tag = col1.text_input("New Visual Tag ID")
        r_rfid = col2.text_input("RFID Chip Number")
        r_breed = st.selectbox("Select Breed", ["HF", "Jersey", "Sahiwal", "Cross", "Cholistani"])
        r_bday = st.date_input("Date of Birth", date.today())
        s1 = st.text_input("Sire ID (Father)"); s2 = st.text_input("Sire 2 ID (G-Father)")
        if st.form_submit_button("💾 Complete Registration"):
            with db_connect() as conn:
                conn.execute("INSERT INTO AnimalMaster (TagID, RFID, Breed, Category, Status, BirthDate, Sire1, Sire2) VALUES (?,?,?,?,?,?,?,?)",
                             (r_tag, r_rfid, r_breed, "Adult", "Active", str(r_bday), s1, s2))
                conn.commit(); st.success(f"Animal {r_tag} Registered!"); st.rerun()
