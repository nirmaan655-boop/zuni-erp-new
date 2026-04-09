import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date

# --- 0. DATABASE CONNECTION & FORCE REPAIR ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Saari tables ko naye siray se ensure karna
    conn.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, RFID TEXT, Breed TEXT, Category TEXT, Weight REAL, Status TEXT, LactationNo INTEGER, BirthDate TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL, LactNo INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, CurrentWeight REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)")
    conn.commit()
    return conn

conn = get_connection()

# --- 1. BRANDING ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Master")
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK MASTER PRO v9.0</h1>", unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
animal_data = pd.read_sql("SELECT * FROM AnimalMaster", conn)
tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
bull_list = animal_data[animal_data['Category'] == 'Bull']['TagID'].tolist()

# --- 3. ALL 10 TABS (DEFINED CLEARLY) ---
tabs = st.tabs(["🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"])

# TAB 1: 360 VIEW
with tabs[0]:
    st.subheader("Herd Inventory")
    st.dataframe(animal_data, use_container_width=True)

# TAB 2: COW CARD
with tabs[1]:
    sid = st.selectbox("Select ID", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.write(f"### Tag: {sid} | Breed: {row['Breed']} | Status: {row['Status']}")
        st.dataframe(pd.read_sql(f"SELECT * FROM MilkLogs WHERE TagID='{sid}' LIMIT 5", conn))

# TAB 3: MILK
with tabs[2]:
    with st.form("milk_form"):
        c1, c2 = st.columns(2)
        m_tag = c1.selectbox("Tag", tag_list)
        m_date = c2.date_input("Date", date.today())
        v1, v2, v3 = st.columns(3)
        morning = v1.number_input("Morning")
        noon = v2.number_input("Noon")
        evening = v3.number_input("Evening")
        if st.form_submit_button("Save Milk"):
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(m_date), m_tag, morning, noon, evening, morning+noon+evening))
            conn.commit(); st.rerun()

# TAB 4: TREATMENT
with tabs[3]:
    with st.form("treat_form"):
        t_tag = st.selectbox("Select Animal", tag_list)
        med = st.text_input("Medicine Name")
        qty = st.number_input("Quantity")
        if st.form_submit_button("Log Treatment"):
            conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Med1, Qty1) VALUES (?,?,?,?)", (str(date.today()), t_tag, med, qty))
            conn.commit(); st.rerun()

# TAB 5: BREEDING (PD WORKING)
with tabs[4]:
    st.subheader("Breeding & PD Check")
    with st.form("breed_form"):
        b_tag = st.selectbox("Cow ID", tag_list)
        b_act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service"])
        
        # PD aur AI ki dynamic logic
        pdr, sem = "N/A", "N/A"
        if b_act == "PD Check":
            pdr = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        elif b_act == "Insemination (AI)":
            sem = st.text_input("Semen Name")
            
        if st.form_submit_button("Save Breeding Record"):
            conn.execute("INSERT INTO BreedingLogs (Date, TagID, Action, SemenName, PD_Result) VALUES (?,?,?,?,?)", (str(date.today()), b_tag, b_act, sem, pdr))
            conn.commit(); st.success("Breeding Recorded!"); st.rerun()

# TAB 6: CALVING (TWINS WORKING)
with tabs[5]:
    st.subheader("Calving & Twins Logic")
    with st.form("calv_form"):
        dam = st.selectbox("Mother ID", tag_list)
        ctype = st.radio("Birth Type", ["Single", "Twins"], horizontal=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            c1t = st.text_input("Calf 1 Tag").upper()
            c1s = st.selectbox("Sex 1", ["Heifer", "Bull"])
        if ctype == "Twins":
            with col2:
                c2t = st.text_input("Calf 2 Tag").upper()
                c2s = st.selectbox("Sex 2", ["Heifer", "Bull"])
        else:
            c2t, c2s = "N/A", "N/A"
            
        if st.form_submit_button("Register Birth"):
            conn.execute("INSERT INTO CalvingLogs (Date, DamID, Type, Calf1_Tag, Calf1_Sex, Calf2_Tag, Calf2_Sex) VALUES (?,?,?,?,?,?,?)", 
                         (str(date.today()), dam, ctype, c1t, c1s, c2t, c2s))
            # Add to Master
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?,?,'Active')", (c1t, "Calf"))
            if ctype == "Twins":
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?,?,'Active')", (c2t, "Calf"))
            conn.commit(); st.success("Birth Registered!"); st.rerun()

# TAB 7-10 (WEIGHT, VAC, MOVE, REG)
with tabs[6]: # Weight
    w_tag = st.selectbox("Weight ID", tag_list)
    val = st.number_input("Weight (kg)")
    if st.button("Save Weight"):
        conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (val, w_tag)); conn.commit(); st.rerun()

with tabs[9]: # Registration
    with st.form("reg_final"):
        rtag = st.text_input("New Tag ID").upper()
        rcat = st.selectbox("Type", ["Cow", "Bull", "Heifer", "Calf"])
        rbrd = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        if st.form_submit_button("Register Animal"):
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Breed, Status) VALUES (?,?,?,?)", (rtag, rcat, rbrd, "Active"))
            conn.commit(); st.rerun()
