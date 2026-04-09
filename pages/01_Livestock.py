import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date

# --- 0. DATABASE CONNECTION & FORCE REPAIR ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # 1. Animal Master
    conn.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Weight REAL, Status TEXT, LastWeight REAL)")
    # 2. Milk Logs
    conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
    # 3. Breeding Logs
    conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, SemenName TEXT, PD_Result TEXT, Vet TEXT)")
    # 4. Calving Logs
    conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL)")
    # 5. Treatment Logs (FIXED)
    conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med TEXT, Qty REAL, Symptoms TEXT)")
    # 6. Vaccination Logs
    conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL)")
    # 7. Weight Logs
    conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, Weight REAL, PrevWeight REAL)")
    
    conn.commit()
    return conn

conn = get_connection()

# --- 1. BRANDING ---
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK PRO v12.0</h1>", unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
animal_data = pd.read_sql("SELECT * FROM AnimalMaster", conn)
tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []

# --- 3. SIDEBAR MENU ---
menu = ["🔍 360° VIEW", "🥛 MILK LOGS", "🏥 TREATMENT", "🧬 BREEDING & PD", "🍼 CALVING", "⚖️ WEIGHT LOGS", "💉 VACCINATION", "📝 REGISTRATION"]
choice = st.sidebar.selectbox("FARM MENU", menu)

def show_history(query):
    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.write("### 📋 History Records")
            st.dataframe(df, use_container_width=True)
    except:
        st.error("Error loading history. Try registering an item first.")

# --- TAB: TREATMENT ---
if choice == "🏥 TREATMENT":
    st.subheader("Medical Treatment Log")
    with st.form("treat_form"):
        t_tag = st.selectbox("Select Patient", tag_list)
        t_med = st.text_input("Medicine Name")
        t_qty = st.number_input("Quantity (ml/mg)")
        t_sym = st.text_area("Symptoms")
        if st.form_submit_button("💉 Save Treatment"):
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)", (str(date.today()), t_tag, t_med, t_qty, t_sym))
            conn.commit(); st.success("Treatment Logged!"); st.rerun()
    show_history("SELECT * FROM TreatmentLogs ORDER BY Date DESC")

# --- TAB: BREEDING (PD STATUS FIX) ---
elif choice == "🧬 BREEDING & PD":
    st.subheader("Breeding & Reproduction")
    with st.form("breed_f"):
        tag = st.selectbox("Cow ID", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service"])
        pdr = "N/A"
        if act == "PD Check":
            pdr = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        
        if st.form_submit_button("🚀 Save Breeding"):
            conn.execute("INSERT INTO BreedingLogs (Date, TagID, Action, SemenName, PD_Result, Vet) VALUES (?,?,?,?,?,?)", 
                         (str(date.today()), tag, act, "Semen", pdr, "Dr. Zuni"))
            if pdr == "Pregnant (+)":
                conn.execute("UPDATE AnimalMaster SET Status = 'Pregnant' WHERE TagID = ?", (tag,))
            conn.commit(); st.success("Record Saved!"); st.rerun()
    show_history("SELECT * FROM BreedingLogs ORDER BY Date DESC")

# --- TAB: CALVING (TWINS FIX) ---
elif choice == "🍼 CALVING":
    st.subheader("Register Calving/Birth")
    with st.form("calv_f"):
        dam = st.selectbox("Mother", tag_list)
        ctype = st.radio("Birth Type", ["Single", "Twins"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            c1t = st.text_input("Calf 1 Tag").upper()
            c1s = st.selectbox("Sex 1", ["Heifer", "Bull"])
            c1w = st.number_input("Weight 1", 25.0)
        c2t, c2s, c2w = "N/A", "N/A", 0
        if ctype == "Twins":
            with col2:
                c2t = st.text_input("Calf 2 Tag").upper()
                c2s = st.selectbox("Sex 2", ["Heifer", "Bull"])
                c2w = st.number_input("Weight 2", 25.0)
        
        if st.form_submit_button("🍼 Register"):
            conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?)", 
                         (str(date.today()), dam, "Live", ctype, c1t, c1s, c1w, c2t, c2s, c2w))
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status, Weight) VALUES (?,?,'Active',?)", (c1t, "Calf", c1w))
            if ctype == "Twins":
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status, Weight) VALUES (?,?,'Active',?)", (c2t, "Calf", c2w))
            conn.commit(); st.rerun()
    show_history("SELECT * FROM CalvingLogs ORDER BY Date DESC")

# --- TAB: REGISTRATION (360 Fix) ---
elif choice == "📝 REGISTRATION":
    with st.form("reg"):
        rtag = st.text_input("New Tag ID").upper()
        rcat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        rbrd = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        rw = st.number_input("Weight")
        if st.form_submit_button("✅ Register"):
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Breed, Weight, Status) VALUES (?,?,?,?,'Active')", (rtag, rcat, rbrd, rw))
            conn.commit(); st.success("Registered!"); st.rerun()

# --- OTHER TABS (MILK, WEIGHT, 360) ---
elif choice == "🔍 360° VIEW":
    st.dataframe(animal_data, use_container_width=True)
elif choice == "🥛 MILK LOGS":
    # (Milk code as before)
    show_history("SELECT * FROM MilkLogs ORDER BY Date DESC")
