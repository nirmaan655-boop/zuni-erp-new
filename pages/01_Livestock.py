import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# ================= DB =================
conn = sqlite3.connect("Zuni.db", check_same_thread=False)

def q(sql):
    try:
        return pd.read_sql(sql, conn)
    except:
        return pd.DataFrame()

def execq(sql, params=()):
    conn.execute(sql, params)
    conn.commit()

# ================= AUTO TABLES =================
def setup():
    conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
        TagID TEXT PRIMARY KEY,
        Category TEXT,
        Breed TEXT,
        Status TEXT,
        Weight REAL DEFAULT 0
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS BreedingLogs (
        Date TEXT, CowTag TEXT, Sire TEXT, Semen TEXT, Method TEXT, Vet TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS CalvingLogs (
        Date TEXT, CowTag TEXT, CalvingDate TEXT, Sire TEXT,
        CalfGender TEXT, CalfWeight REAL
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS VaccineLogs (
        Date TEXT, AnimalTag TEXT, Vaccine TEXT, Dose TEXT, Vet TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS TreatmentLogs (
        Date TEXT, AnimalTag TEXT, Disease TEXT, Medicine TEXT, Vet TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS MovementLogs (
        Date TEXT, AnimalTag TEXT, Pen TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS DeathLogs (
        Date TEXT, AnimalTag TEXT, Reason TEXT
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS CullingLogs (
        Date TEXT, AnimalTag TEXT, Reason TEXT
    )""")

    conn.commit()

setup()

# ================= LOAD =================
animals = q("SELECT * FROM AnimalMaster")
tags = animals["TagID"].tolist() if not animals.empty else []

st.set_page_config(layout="wide")
st.title("🐄 ZUNI LIVESTOCK ERP - 11 TAB MASTER SYSTEM")

# ================= TABS =================
tabs = st.tabs([
    "🐄 Cow Card",
    "📋 All Animals",
    "🧬 Breeding",
    "🐣 Calving",
    "💉 Vaccination",
    "🩺 Treatment",
    "🏥 Hospital",
    "📦 Inventory",
    "🚚 Movement",
    "📊 Reports",
    "📈 Dashboard"
])

# ================= 1 COW CARD =================
with tabs[0]:
    st.subheader("🐄 Cow Card (Full Profile)")

    if tags:
        tag = st.selectbox("Select Animal", tags)

        st.dataframe(animals[animals["TagID"]==tag])

        st.markdown("### 📊 History Snapshot")

        st.metric("Vaccines", len(q(f"SELECT * FROM VaccineLogs WHERE AnimalTag='{tag}'")))
        st.metric("Breeding", len(q(f"SELECT * FROM BreedingLogs WHERE CowTag='{tag}'")))
        st.metric("Calving", len(q(f"SELECT * FROM CalvingLogs WHERE CowTag='{tag}'")))
        st.metric("Treatment", len(q(f"SELECT * FROM TreatmentLogs WHERE AnimalTag='{tag}'")))

# ================= 2 ALL ANIMALS =================
with tabs[1]:
    st.subheader("📋 All Animals")
    st.dataframe(animals)

# ================= 3 BREEDING =================
with tabs[2]:
    st.subheader("🧬 Breeding")

    if tags:
        cow = st.selectbox("Cow", tags)
        sire = st.text_input("Sire")
        semen = st.text_input("Semen Straw")
        method = st.selectbox("Method", ["AI","Natural","ET","Sync"])
        vet = st.text_input("Vet")

        if st.button("Save Breeding"):
            execq("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)",
                  (str(date.today()), cow, sire, semen, method, vet))
            st.success("Saved")

# ================= 4 CALVING =================
with tabs[3]:
    st.subheader("🐣 Calving")

    if tags:
        cow = st.selectbox("Cow", tags, key="calv")
        calving_date = st.date_input("Calving Date")
        sire = st.text_input("Sire")
        gender = st.selectbox("Calf Gender", ["Male","Female"])
        weight = st.number_input("Calf Weight")

        if st.button("Save Calving"):
            execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?)",
                  (str(date.today()), cow, str(calving_date), sire, gender, weight))
            st.success("Saved")

# ================= 5 VACCINATION =================
with tabs[4]:
    st.subheader("💉 Vaccination")

    if tags:
        animal = st.selectbox("Animal", tags, key="vac")
        vaccine = st.text_input("Vaccine")
        dose = st.text_input("Dose")
        vet = st.text_input("Vet")

        if st.button("Save Vaccine"):
            execq("INSERT INTO VaccineLogs VALUES (?,?,?,?,?)",
                  (str(date.today()), animal, vaccine, dose, vet))
            st.success("Saved")

# ================= 6 TREATMENT =================
with tabs[5]:
    st.subheader("🩺 Treatment")

    if tags:
        animal = st.selectbox("Animal", tags, key="treat")
        disease = st.text_input("Disease")
        medicine = st.text_input("Medicine")
        vet = st.text_input("Vet")

        if st.button("Save Treatment"):
            execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
                  (str(date.today()), animal, disease, medicine, vet))
            st.success("Saved")

# ================= 7 HOSPITAL =================
with tabs[6]:
    st.subheader("🏥 Hospital (Death + Culling)")

    if tags:
        animal = st.selectbox("Animal", tags, key="hos")
        action = st.selectbox("Action", ["Recover","Death","Culling"])
        reason = st.text_input("Reason")

        if st.button("Execute"):
            if action == "Death":
                execq("INSERT INTO DeathLogs VALUES (?,?,?)", (str(date.today()), animal, reason))
                execq("UPDATE AnimalMaster SET Status='Dead' WHERE TagID=?", (animal,))

            elif action == "Culling":
                execq("INSERT INTO CullingLogs VALUES (?,?,?)", (str(date.today()), animal, reason))
                execq("UPDATE AnimalMaster SET Status='Culled' WHERE TagID=?", (animal,))

            elif action == "Recover":
                execq("UPDATE AnimalMaster SET Status='Healthy' WHERE TagID=?", (animal,))

            st.success("Updated")

# ================= 8 INVENTORY =================
with tabs[7]:
    st.subheader("📦 Inventory")
    st.dataframe(q("SELECT * FROM sqlite_master WHERE type='table'"))

# ================= 9 MOVEMENT =================
with tabs[8]:
    st.subheader("🚚 Movement")

    if tags:
        animal = st.selectbox("Animal", tags, key="move")
        pen = st.text_input("Pen")

        if st.button("Move"):
            execq("INSERT INTO MovementLogs VALUES (?,?,?)",
                  (str(date.today()), animal, pen))
            st.success("Moved")

# ================= 10 REPORTS =================
with tabs[9]:
    st.subheader("📊 Reports")

    st.write("Total Animals:", len(animals))

    st.write("Healthy:", len(animals[animals.get("Status","")=="Healthy"]))
    st.write("Dead:", len(animals[animals.get("Status","")=="Dead"]))

# ================= 11 DASHBOARD =================
with tabs[10]:
    st.subheader("📈 Dashboard")

    st.metric("Total Animals", len(animals))
    st.metric("Active", len(animals))
    st.metric("System Status", "RUNNING")
