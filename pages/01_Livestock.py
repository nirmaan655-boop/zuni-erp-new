import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import os

# ================= DB =================
DB_PATH = os.path.join(os.path.dirname(__file__), "Zuni.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

def q(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)

def execq(sql, params=()):
    conn.execute(sql, params)
    conn.commit()

# ================= INIT =================
def setup():
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS AnimalMaster (
        TagID TEXT PRIMARY KEY,
        Category TEXT,
        Breed TEXT,
        Status TEXT,
        Weight REAL
    );

    CREATE TABLE IF NOT EXISTS BreedingLogs (
        Date TEXT, CowTag TEXT, Sire TEXT, Semen TEXT, Method TEXT, Vet TEXT
    );

    CREATE TABLE IF NOT EXISTS CalvingLogs (
        Date TEXT, CowTag TEXT, CalvingDate TEXT, Sire TEXT,
        CalfGender TEXT, CalfWeight REAL
    );

    CREATE TABLE IF NOT EXISTS VaccineLogs (
        Date TEXT, AnimalTag TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT
    );

    CREATE TABLE IF NOT EXISTS TreatmentLogs (
        Date TEXT, AnimalTag TEXT, Disease TEXT, Medicine TEXT, Vet TEXT
    );

    CREATE TABLE IF NOT EXISTS MovementLogs (
        Date TEXT, AnimalTag TEXT, Pen TEXT
    );

    CREATE TABLE IF NOT EXISTS DeathLogs (
        Date TEXT, AnimalTag TEXT, Reason TEXT
    );

    CREATE TABLE IF NOT EXISTS CullingLogs (
        Date TEXT, AnimalTag TEXT, Reason TEXT
    );
    """)

    conn.commit()

def seed():
    df = q("SELECT * FROM AnimalMaster")
    if df.empty:
        conn.execute("""
        INSERT INTO AnimalMaster VALUES
        ('COW001','Cow','HF','Healthy',420),
        ('COW002','Cow','Jersey','Healthy',380),
        ('BUF001','Buffalo','Nili Ravi','Healthy',520)
        """)
        conn.commit()

setup()
seed()

animals = q("SELECT * FROM AnimalMaster")
tags = animals["TagID"].tolist()

# ================= UI =================
st.set_page_config(layout="wide")
st.title("🐄 LIVESTOCK ERP PRO (FIXED VERSION)")

tabs = st.tabs([
    "🐄 Cow Card",
    "📋 All Animals",
    "🧬 Breeding",
    "🐣 Calving",
    "💉 Vaccination",
    "🩺 Treatment",
    "🏥 Hospital",
    "🚚 Movement",
    "📊 Reports",
    "📈 Dashboard",
    "📌 Full History"
])

# ================= 1 COW CARD =================
with tabs[0]:
    st.subheader("Cow Card")

    tag = st.selectbox("Select Animal", tags, key="card_tag")

    st.dataframe(animals[animals["TagID"] == tag])

    st.metric("Vaccination", len(q("SELECT * FROM VaccineLogs WHERE AnimalTag=?", (tag,))))
    st.metric("Breeding", len(q("SELECT * FROM BreedingLogs WHERE CowTag=?", (tag,))))
    st.metric("Calving", len(q("SELECT * FROM CalvingLogs WHERE CowTag=?", (tag,))))
    st.metric("Treatment", len(q("SELECT * FROM TreatmentLogs WHERE AnimalTag=?", (tag,))))

# ================= 2 ALL ANIMALS =================
with tabs[1]:
    st.subheader("All Animals")
    st.dataframe(animals, use_container_width=True)

# ================= 3 BREEDING =================
with tabs[2]:
    st.subheader("Breeding")

    cow = st.selectbox("Cow", tags, key="breed_cow")
    sire = st.text_input("Sire", key="breed_sire")
    semen = st.text_input("Semen", key="breed_semen")
    method = st.selectbox("Method", ["AI","Natural","ET"], key="breed_method")
    vet = st.text_input("Vet", key="breed_vet")

    if st.button("Save Breeding", key="breed_btn"):
        execq("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)",
              (str(date.today()), cow, sire, semen, method, vet))
        st.success("Saved")

# ================= 4 CALVING =================
with tabs[3]:
    st.subheader("Calving")

    cow = st.selectbox("Cow", tags, key="calv_cow")
    calving_date = st.date_input("Calving Date", key="calv_date")
    sire = st.text_input("Sire", key="calv_sire")
    gender = st.selectbox("Calf Gender", ["Male","Female"], key="calv_gender")
    weight = st.number_input("Calf Weight", key="calv_weight")

    if st.button("Save Calving", key="calv_btn"):
        execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?)",
              (str(date.today()), cow, str(calving_date), sire, gender, weight))
        st.success("Saved")

# ================= 5 VACCINATION =================
with tabs[4]:
    st.subheader("Vaccination")

    animal = st.selectbox("Animal", tags, key="vac_animal")
    vaccine = st.text_input("Vaccine", key="vac_vaccine")
    dose = st.text_input("Dose", key="vac_dose")
    vet = st.text_input("Vet", key="vac_vet")

    if st.button("Save Vaccine", key="vac_btn"):
        execq("INSERT INTO VaccineLogs VALUES (?,?,?,?,?)",
              (str(date.today()), animal, vaccine, dose, vet))
        st.success("Saved")

# ================= 6 TREATMENT =================
with tabs[5]:
    st.subheader("Treatment")

    animal = st.selectbox("Animal", tags, key="treat_animal")
    disease = st.text_input("Disease", key="treat_disease")
    medicine = st.text_input("Medicine", key="treat_medicine")
    vet = st.text_input("Vet", key="treat_vet")

    if st.button("Save Treatment", key="treat_btn"):
        execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
              (str(date.today()), animal, disease, medicine, vet))
        st.success("Saved")

# ================= 7 HOSPITAL =================
with tabs[6]:
    st.subheader("Hospital")

    animal = st.selectbox("Animal", tags, key="hos_animal")
    action = st.selectbox("Action", ["Recover","Death","Culling"], key="hos_action")
    reason = st.text_input("Reason", key="hos_reason")

    if st.button("Execute", key="hos_btn"):
        if action == "Death":
            execq("INSERT INTO DeathLogs VALUES (?,?,?)",
                  (str(date.today()), animal, reason))
            execq("UPDATE AnimalMaster SET Status='Dead' WHERE TagID=?", (animal,))

        elif action == "Culling":
            execq("INSERT INTO CullingLogs VALUES (?,?,?)",
                  (str(date.today()), animal, reason))
            execq("UPDATE AnimalMaster SET Status='Culled' WHERE TagID=?", (animal,))

        else:
            execq("UPDATE AnimalMaster SET Status='Healthy' WHERE TagID=?", (animal,))

        st.success("Updated")

# ================= 8 MOVEMENT =================
with tabs[7]:
    st.subheader("Movement")

    animal = st.selectbox("Animal", tags, key="mov_animal")
    pen = st.text_input("Pen", key="mov_pen")

    if st.button("Move", key="mov_btn"):
        execq("INSERT INTO MovementLogs VALUES (?,?,?)",
              (str(date.today()), animal, pen))
        st.success("Moved")

# ================= 9 REPORTS =================
with tabs[8]:
    st.subheader("Reports")

    st.metric("Total Animals", len(animals))
    st.metric("Healthy", len(animals[animals["Status"]=="Healthy"]))
    st.metric("Dead", len(animals[animals["Status"]=="Dead"]))
    st.metric("Culled", len(animals[animals["Status"]=="Culled"]))

# ================= 10 DASHBOARD =================
with tabs[9]:
    st.subheader("Dashboard")

    st.success("System Running Perfect")
    st.metric("Total Animals", len(animals))

# ================= 11 FULL HISTORY =================
with tabs[10]:
    st.subheader("Full History")

    animal = st.selectbox("Select Animal", tags, key="hist_animal")

    st.write("Vaccination")
    st.dataframe(q("SELECT * FROM VaccineLogs WHERE AnimalTag=?", (animal,)))

    st.write("Breeding")
    st.dataframe(q("SELECT * FROM BreedingLogs WHERE CowTag=?", (animal,)))

    st.write("Calving")
    st.dataframe(q("SELECT * FROM CalvingLogs WHERE CowTag=?", (animal,)))

    st.write("Treatment")
    st.dataframe(q("SELECT * FROM TreatmentLogs WHERE AnimalTag=?", (animal,)))
