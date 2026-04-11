import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
import os
import plotly.express as px

# ================= DATABASE CONNECTION =================
DB_PATH = os.path.join(os.path.dirname(__file__), "Zuni.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

def q(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)

def execq(sql, params=()):
    conn.execute(sql, params)
    conn.commit()

# ================= DATABASE SETUP (ALL TABLES) =================
def setup():
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS AnimalMaster (
        TagID TEXT PRIMARY KEY, Category TEXT, Breed TEXT, Status TEXT, Weight REAL
    );
    CREATE TABLE IF NOT EXISTS BreedingLogs (
        Date TEXT, CowTag TEXT, Type TEXT, Semen TEXT, Protocol TEXT, Vet TEXT, PD_Status TEXT, ExpectedCalving TEXT
    );
    CREATE TABLE IF NOT EXISTS CalvingLogs (
        Date TEXT, CowTag TEXT, CalvingDate TEXT, SireTag TEXT, CalfGender TEXT, CalfWeight REAL, Remarks TEXT
    );
    CREATE TABLE IF NOT EXISTS VaccineLogs (
        Date TEXT, AnimalTag TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT
    );
    CREATE TABLE IF NOT EXISTS TreatmentLogs (
        Date TEXT, AnimalTag TEXT, Disease TEXT, Medicine TEXT, Vet TEXT, Status TEXT
    );
    CREATE TABLE IF NOT EXISTS MovementLogs (
        Date TEXT, AnimalTag TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT
    );
    """)
    conn.commit()

setup()

# ================= DATA LOADING =================
animals = q("SELECT * FROM AnimalMaster")
tags = animals["TagID"].tolist() if not animals.empty else []

# ================= UI SETUP =================
st.set_page_config(layout="wide", page_title="Zuni Livestock ERP PRO")
st.title("🐄 LIVESTOCK ERP PRO (FULL VERSION)")

tabs = st.tabs([
    "🐄 Cow Card", "📋 Inventory", "🧬 Breeding & PD", "🐣 Calving (Twins)", 
    "💉 Vaccination", "🩺 Treatment & Hospital", "🚚 Movement", "📊 Reports & Dashboard", "📌 Full History"
])

# ================= 1. COW CARD =================
with tabs[0]:
    st.subheader("Individual Cow Performance Card")
    if tags:
        tag = st.selectbox("Select Animal Tag", tags, key="card_sel")
        col1, col2, col3 = st.columns([1,2,1])
        
        animal_info = animals[animals["TagID"] == tag]
        with col1:
            st.info(f"**Category:** {animal_info['Category'].values[0]}")
            st.info(f"**Breed:** {animal_info['Breed'].values[0]}")
        with col2:
            st.dataframe(animal_info)
        with col3:
            st.metric("Vaccines", len(q("SELECT * FROM VaccineLogs WHERE AnimalTag=?", (tag,))))
            st.metric("Treatments", len(q("SELECT * FROM TreatmentLogs WHERE AnimalTag=?", (tag,))))
    else:
        st.warning("AnimalMaster is empty. Please purchase animals from Procurement.")

# ================= 2. ALL ANIMALS =================
with tabs[1]:
    st.subheader("Current Stock Inventory")
    st.dataframe(animals, use_container_width=True)

# ================= 3. BREEDING & PD =================
with tabs[2]:
    st.subheader("🧬 Pro Breeding & Pregnancy Diagnosis")
    if tags:
        col1, col2 = st.columns(2)
        with col1:
            cow = st.selectbox("Select Cow for Breeding", tags, key="br_cow")
            b_type = st.selectbox("Breeding Type", ["AI (Artificial)", "Natural Bull"])
            semen = st.text_input("Semen Name / Bull Tag")
            heat_strength = st.slider("Heat Strength (1-5)", 1, 5, 3)
            vet = st.text_input("Vet Name", key="br_vet")
            
            if st.button("Save Breeding Record"):
                execq("INSERT INTO BreedingLogs (Date, CowTag, Type, Semen, Protocol, Vet, PD_Status) VALUES (?,?,?,?,?,?,?)", 
                      (str(date.today()), cow, b_type, semen, f"Heat Score: {heat_strength}", vet, "Pending"))
                st.success(f"Breeding Recorded for {cow}!")

        with col2:
            st.markdown("### 🧪 PD Section (Pregnancy Check)")
            pending_pd = q("SELECT * FROM BreedingLogs WHERE PD_Status='Pending'")
            if not pending_pd.empty:
                pd_cow = st.selectbox("Select Cow for PD", pending_pd["CowTag"].unique())
                pd_result = st.radio("PD Result", ["Pregnant", "Open (Repeat)"])
                if st.button("Update PD Status"):
                    exp_date = str(date.today() + timedelta(days=280)) if pd_result == "Pregnant" else "N/A"
                    execq("UPDATE BreedingLogs SET PD_Status=?, ExpectedCalving=? WHERE CowTag=? AND PD_Status='Pending'", 
                          (pd_result, exp_date, pd_cow))
                    st.success(f"PD Updated! Expected Calving: {exp_date}")
            else:
                st.write("No pending PD checks.")

# ================= 4. CALVING (TWINS ENABLED) =================
with tabs[3]:
    st.subheader("🐣 Calving Registration (Twins Enabled)")
    if tags:
        c_cow = st.selectbox("Mother Tag", tags, key="calv_cow")
        c_date = st.date_input("Calving Date")
        sire = st.text_input("Sire (Father) Tag")
        is_twins = st.checkbox("Is it Twins?")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Calf 1")
            g1 = st.selectbox("Gender 1", ["Male", "Female"])
            w1 = st.number_input("Weight 1 (kg)", min_value=0.0)
        
        if is_twins:
            with col2:
                st.markdown("### Calf 2")
                g2 = st.selectbox("Gender 2", ["Male", "Female"])
                w2 = st.number_input("Weight 2 (kg)", min_value=0.0)

        if st.button("Save Calving"):
            execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?)", (str(date.today()), c_cow, str(c_date), sire, g1, w1, "Single" if not is_twins else "Twin 1"))
            if is_twins:
                execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?)", (str(date.today()), c_cow, str(c_date), sire, g2, w2, "Twin 2"))
            execq("UPDATE AnimalMaster SET Status='Lactating' WHERE TagID=?", (c_cow,))
            st.success("Calving data and Mother status updated!")

# ================= 5. VACCINATION =================
with tabs[4]:
    st.subheader("💉 Vaccination Management")
    if tags:
        v_tag = st.selectbox("Animal Tag", tags, key="vac_tag")
        vac_name = st.selectbox("Vaccine", ["FMD", "HS", "Anthrax", "Lumpy", "Brucellosis"])
        v_dose = st.text_input("Dose (ml/cc)")
        if st.button("Update Vaccination"):
            execq("INSERT INTO VaccineLogs VALUES (?,?,?,?,?)", (str(date.today()), v_tag, vac_name, v_dose, "Authorized Vet"))
            st.success("Vaccination Logged!")

# ================= 6. TREATMENT & HOSPITAL =================
with tabs[5]:
    st.subheader("🩺 Hospital & Sick Bay")
    if tags:
        col1, col2 = st.columns(2)
        with col1:
            t_tag = st.selectbox("Sick Animal", tags, key="treat_tag")
            dis = st.text_input("Disease / Symptoms")
            med = st.text_area("Medicine & Treatment Plan")
            t_status = st.selectbox("Current Condition", ["Under Treatment", "Recovered", "Critical"])
            if st.button("Save Treatment"):
                execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?)", (str(date.today()), t_tag, dis, med, "Dr. Zuni", t_status))
                st.success("Treatment Record Saved!")
        with col2:
            st.markdown("### Active Sick List")
            sick_list = q("SELECT AnimalTag, Disease, Status FROM TreatmentLogs WHERE Status != 'Recovered'")
            st.table(sick_list)

# ================= 7. MOVEMENT =================
with tabs[6]:
    st.subheader("🚚 Pen & Location Movement")
    if tags:
        m_tag = st.selectbox("Animal Tag", tags, key="mov_tag")
        f_pen = st.text_input("From (Old Pen)")
        t_pen = st.text_input("To (New Pen)")
        reason = st.text_input("Reason for Movement")
        if st.button("Log Movement"):
            execq("INSERT INTO MovementLogs VALUES (?,?,?,?,?)", (str(date.today()), m_tag, f_pen, t_pen, reason))
            st.success("Movement Recorded!")

# ================= 8. DASHBOARD & REPORTS =================
with tabs[7]:
    st.subheader("📊 Farm Performance Analytics")
    if not animals.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(animals, names='Category', title='Herd Composition')
            st.plotly_chart(fig1)
        with c2:
            fig2 = px.bar(animals, x='Breed', title='Breed Distribution')
            st.plotly_chart(fig2)
        
        st.markdown("---")
        st.markdown("### Summary Statistics")
        st.write(f"Total Animals: {len(animals)} | Active Treatments: {len(q('SELECT * FROM TreatmentLogs WHERE Status != \"Recovered\"'))}")
    else:
        st.info("Add data to see charts.")

# ================= 9. FULL HISTORY =================
with tabs[8]:
    st.subheader("📌 System Master Logs")
    log_choice = st.selectbox("View History For:", ["Breeding", "Calving", "Vaccine", "Treatment", "Movement"])
    
    map_tables = {
        "Breeding": "BreedingLogs", "Calving": "CalvingLogs",
        "Vaccine": "VaccineLogs", "Treatment": "TreatmentLogs", "Movement": "MovementLogs"
    }
    
    st.dataframe(q(f"SELECT * FROM {map_tables[log_choice]} ORDER BY Date DESC"), use_container_width=True)
