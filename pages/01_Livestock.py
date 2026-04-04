import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date

# --- 0. DATABASE & SCHEMA ---
def init_livestock_db():
    with db_connect() as conn:
        # Master Table
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY, Breed TEXT, Category TEXT, CurrentPen TEXT, 
            Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT, Sire1 TEXT, Sire2 TEXT)""")
        
        # All Logs Tables
        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Weight REAL, LactNo INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, CurrentWeight REAL, PreviousWeight REAL, Gain REAL, DaysGap INTEGER, AvgDailyGain REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)")
        conn.commit()

init_livestock_db()

# --- BRANDING ---
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK PRO v3.0</h1>", unsafe_allow_html=True)

# --- DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    try:
        meds = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster")
        med_dict = dict(zip(meds['ItemName'], meds['UOM']))
        med_list = ["None"] + list(med_dict.keys())
    except: med_list, med_dict = ["None"], {}

# --- HELPER: HISTORY TABLE ---
def show_history(table_name, filter_id=None):
    st.markdown(f"**📋 Recent {table_name} Records**")
    query = f"SELECT rowid as ID, * FROM {table_name}"
    if filter_id: query += f" WHERE TagID = '{filter_id}'"
    query += " ORDER BY rowid DESC LIMIT 10"
    with db_connect() as conn:
        df = fetch_df(conn, query)
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("No records found.")

# --- 10 TABS ---
tabs = st.tabs(["🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"])

# 1. 360 VIEW
with tabs[0]:
    st.dataframe(animal_data, use_container_width=True)

# 2. COW CARD (The "History Hub")
with tabs[1]:
    search_id = st.selectbox("Select Animal for Full Card", [""] + tag_list)
    if search_id:
        row = animal_data[animal_data['TagID'] == search_id].iloc[0]
        st.markdown(f"## 🐄 COW CARD: {search_id}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Breed", row['Breed'])
        c2.metric("Lactation", row['LactationNo'])
        c3.metric("Current Pen", row['CurrentPen'])
        
        st.divider()
        st.subheader("📊 Life History")
        sub1, sub2 = st.tabs(["Breeding/Calving", "Medical/Milk"])
        with sub1:
            show_history("BreedingLogs", search_id)
            show_history("CalvingLogs", search_id) # Show as Dam
        with sub2:
            show_history("TreatmentLogs", search_id)
            show_history("MilkLogs", search_id)

# 3. MILK
with tabs[2]:
    with st.form("milk_f"):
        t = st.selectbox("Tag", tag_list); d = st.date_input("Date")
        c1, c2, c3 = st.columns(3); m = c1.number_input("Morn"); n = c2.number_input("Noon"); e = c3.number_input("Eve")
        if st.form_submit_button("Save"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), t, m, n, e, m+n+e))
                conn.commit(); st.rerun()
    show_history("MilkLogs")

# 4. TREATMENT
with tabs[3]:
    with st.form("treat_f"):
        t = st.selectbox("Patient", tag_list)
        cols = st.columns(4); inputs = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Inj {i+1}", med_list, key=f"t_m{i}")
                q = st.number_input(f"Qty {i+1}", key=f"t_q{i}")
                u = med_dict.get(m, "-"); st.caption(f"UOM: {u}")
                inputs.extend([m, q, u])
        rem = st.text_area("Symptoms")
        if st.form_submit_button("Log Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), t, *inputs, rem))
                conn.commit(); st.rerun()
    show_history("TreatmentLogs")

# 5. BREEDING
with tabs[4]:
    with st.form("breed_f"):
        t = st.selectbox("Cow", tag_list)
        act = st.selectbox("Action", ["AI", "PD Check", "Natural", "Dry"])
        heat = st.selectbox("Heat", ["Natural", "Ovsynch", "G6G", "Pre-synch"])
        pd = st.selectbox("PD Result", ["N/A", "Pregnant (+)", "Empty (-)", "Abortion"])
        if st.form_submit_button("Save Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), t, act, heat, "Straw", 1, pd, "Vet"))
                conn.commit(); st.rerun()
    show_history("BreedingLogs")

# 6. CALVING (Twins Logic Fixed)
with tabs[5]:
    with st.form("calv_f"):
        d_id = st.selectbox("Mother Tag", tag_list)
        c_type = st.radio("Type", ["Single", "Twins"], horizontal=True)
        res = st.selectbox("Result", ["Live Birth", "Stillborn", "Abortion"])
        
        # Dynamic Columns for Twins
        col1, col2 = st.columns(2)
        with col1:
            st.info("Calf 1 Details")
            c1_t = st.text_input("Tag 1"); c1_s = st.selectbox("Sex 1", ["Heifer", "Bull", "Freemartin"]); c1_w = st.number_input("Weight 1")
        with col2:
            if c_type == "Twins":
                st.info("Calf 2 Details")
                c2_t = st.text_input("Tag 2"); c2_s = st.selectbox("Sex 2", ["Heifer", "Bull", "Freemartin"]); c2_w = st.number_input("Weight 2")
            else: c2_t, c2_s, c2_w = "N/A", "N/A", 0

        if st.form_submit_button("Register Birth"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?)", (str(date.today()), d_id, res, c_type, c1_t, c1_s, c2_t, c2_s, c1_w, 1))
                conn.execute("INSERT INTO AnimalMaster (TagID, BirthDate, Weight) VALUES (?,?,?)", (c1_t, str(date.today()), c1_w))
                if c_type == "Twins": conn.execute("INSERT INTO AnimalMaster (TagID, BirthDate, Weight) VALUES (?,?,?)", (c2_t, str(date.today()), c2_w))
                conn.commit(); st.rerun()
    show_history("CalvingLogs")

# 7. WEIGHT
with tabs[6]:
    with st.form("weight_f"):
        t = st.selectbox("Animal", tag_list); cur_w = st.number_input("Current Weight")
        if st.form_submit_button("Log Weight"):
            with db_connect() as conn:
                conn.execute("INSERT INTO WeightLogs (Date, TagID, CurrentWeight) VALUES (?,?,?)", (str(date.today()), t, cur_w))
                conn.commit(); st.rerun()
    show_history("WeightLogs")

# 8. VACCINATION
with tabs[7]:
    with st.form("vac_f"):
        ts = st.multiselect("Select Animals", tag_list)
        v_name = st.text_input("Vaccine Name"); dose = st.number_input("Dose (ml)")
        if st.form_submit_button("Bulk Vaccinate"):
            with db_connect() as conn:
                conn.execute("INSERT INTO VacLogs VALUES (?,?,?,?,?)", (str(date.today()), str(ts), v_name, dose, "Batch123"))
                conn.commit(); st.rerun()
    show_history("VacLogs")

# 9. MOVE (PEN TRANSFER)
with tabs[8]:
    with st.form("move_f"):
        t = st.selectbox("Animal", tag_list); to_p = st.selectbox("To Pen", ["PEN-A", "PEN-B", "DRY", "QUARANTINE"])
        if st.form_submit_button("Transfer"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET CurrentPen = ? WHERE TagID = ?", (to_p, t))
                conn.commit(); st.success("Moved!")
    show_history("MoveLogs")

# 10. REGISTRATION
with tabs[9]:
    with st.form("reg_f"):
        t = st.text_input("New Tag ID"); b = st.selectbox("Breed", ["HF", "Jersey", "Sahiwal"])
        bd = st.date_input("Birth Date"); s1 = st.text_input("Sire 1"); s2 = st.text_input("Sire 2")
        if st.form_submit_button("Register"):
            with db_connect() as conn:
                conn.execute("INSERT INTO AnimalMaster VALUES (?,?,?,?,?,?,?,?,?,?)", (t, b, "Adult", "PEN-A", 0, "Active", 0, str(bd), s1, s2))
                conn.commit(); st.success("Added!")
