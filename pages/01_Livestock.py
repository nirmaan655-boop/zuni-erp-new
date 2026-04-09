import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date

# --- 0. DATABASE CONNECTION & AUTO-FIX ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Tables with all required columns
    conn.execute("CREATE TABLE IF NOT EXISTS AnimalMaster (TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Weight REAL, Status TEXT, LastWeight REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, SemenName TEXT, PD_Result TEXT, Vet TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, Weight REAL, PrevWeight REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL)")
    conn.commit()
    return conn

conn = get_connection()

# --- 1. BRANDING ---
st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK PRO v11.0</h1>", unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
animal_data = pd.read_sql("SELECT * FROM AnimalMaster", conn)
tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []

# --- 3. SIDEBAR MENU ---
menu = ["🔍 360° VIEW", "🥛 MILK LOGS", "🏥 TREATMENT", "🧬 BREEDING & PD", "🍼 CALVING", "⚖️ WEIGHT LOGS", "💉 VACCINATION", "📝 REGISTRATION"]
choice = st.sidebar.selectbox("FARM MENU", menu)

def show_tab_history(query):
    df = pd.read_sql(query, conn)
    if not df.empty:
        st.write("### 📋 History Records")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found yet.")

# --- TAB 1: 360 VIEW ---
if choice == "🔍 360° VIEW":
    st.subheader("Full Herd Inventory")
    st.dataframe(animal_data, use_container_width=True)

# --- TAB 2: MILK ---
elif choice == "🥛 MILK LOGS":
    with st.form("milk_f"):
        c1, c2 = st.columns(2)
        tag = c1.selectbox("Animal", tag_list)
        d = c2.date_input("Date", date.today())
        m1, m2, m3 = st.columns(3)
        morning = m1.number_input("Morning")
        noon = m2.number_input("Noon")
        evening = m3.number_input("Evening")
        if st.form_submit_button("✅ Save"):
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, morning, noon, evening, morning+noon+evening))
            conn.commit(); st.rerun()
    show_tab_history("SELECT * FROM MilkLogs ORDER BY Date DESC")

# --- TAB 3: BREEDING & PD (WITH AUTO STATUS) ---
elif choice == "🧬 BREEDING & PD":
    st.subheader("Breeding & Reproduction")
    with st.form("breed_f"):
        c1, c2 = st.columns(2)
        tag = c1.selectbox("Select Cow", tag_list)
        d = c2.date_input("Date", date.today())
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service"])
        pdr = "N/A"
        if act == "PD Check":
            pdr = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        
        if st.form_submit_button("🚀 Save Record"):
            # Insert Record
            conn.execute("INSERT INTO BreedingLogs (Date, TagID, Action, PD_Result) VALUES (?,?,?,?)", (str(d), tag, act, pdr))
            # Auto Update Status
            if pdr == "Pregnant (+)":
                conn.execute("UPDATE AnimalMaster SET Status = 'Pregnant' WHERE TagID = ?", (tag,))
            elif pdr == "Empty (-)":
                conn.execute("UPDATE AnimalMaster SET Status = 'Active' WHERE TagID = ?", (tag,))
            conn.commit(); st.success("Breeding Data Saved!"); st.rerun()
    show_tab_history("SELECT * FROM BreedingLogs ORDER BY Date DESC")

# --- TAB 4: CALVING (TWINS) ---
elif choice == "🍼 CALVING":
    with st.form("calv_f"):
        dam = st.selectbox("Mother", tag_list)
        d = st.date_input("Date", date.today())
        ctype = st.radio("Type", ["Single", "Twins"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            c1t = st.text_input("Calf 1 Tag").upper()
            c1s = st.selectbox("Sex 1", ["Heifer", "Bull"])
        c2t, c2s = "N/A", "N/A"
        if ctype == "Twins":
            with col2:
                c2t = st.text_input("Calf 2 Tag").upper()
                c2s = st.selectbox("Sex 2", ["Heifer", "Bull"])
        if st.form_submit_button("🍼 Register"):
            conn.execute("INSERT INTO CalvingLogs (Date, DamID, Type, Calf1_Tag, Calf2_Tag) VALUES (?,?,?,?,?)", (str(d), dam, ctype, c1t, c2t))
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?,?,'Active')", (c1t, "Calf"))
            if ctype == "Twins":
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?,?,'Active')", (c2t, "Calf"))
            conn.execute("UPDATE AnimalMaster SET Status = 'Milking' WHERE TagID = ?", (dam,))
            conn.commit(); st.rerun()
    show_tab_history("SELECT * FROM CalvingLogs ORDER BY Date DESC")

# --- TAB 5: WEIGHT LOGS ---
elif choice == "⚖️ WEIGHT LOGS":
    with st.form("weight_f"):
        tag = st.selectbox("Animal", tag_list)
        new_w = st.number_input("Current Weight")
        if st.form_submit_button("⚖️ Update"):
            # Get Previous Weight
            prev = pd.read_sql(f"SELECT Weight FROM AnimalMaster WHERE TagID='{tag}'", conn)
            pw = prev.iloc[0]['Weight'] if not prev.empty else 0
            conn.execute("UPDATE AnimalMaster SET Weight = ?, LastWeight = ? WHERE TagID = ?", (new_w, pw, tag))
            conn.execute("INSERT INTO WeightLogs VALUES (?,?,?,?)", (str(date.today()), tag, new_w, pw))
            conn.commit(); st.rerun()
    show_tab_history("SELECT * FROM WeightLogs ORDER BY Date DESC")

# --- TAB 6: REGISTRATION ---
elif choice == "📝 REGISTRATION":
    with st.form("reg"):
        rtag = st.text_input("New Tag").upper()
        rcat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        rbrd = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        rw = st.number_input("Initial Weight")
        if st.form_submit_button("✅ Register"):
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Breed, Weight, Status) VALUES (?,?,?,?,'Active')", (rtag, rcat, rbrd, rw))
            conn.commit(); st.rerun()
    show_tab_history("SELECT * FROM AnimalMaster ORDER BY rowid DESC")
