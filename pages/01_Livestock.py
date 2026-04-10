import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# ================= DB =================
conn = sqlite3.connect("Zuni.db", check_same_thread=False)

def q(sql, params=()):
    try:
        return pd.read_sql_query(sql, conn, params=params)
    except:
        return pd.DataFrame()

def execq(sql, params=()):
    conn.execute(sql, params)
    conn.commit()

# ================= TABLES =================
def setup():

    conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
        TagID TEXT PRIMARY KEY,
        Category TEXT,
        Breed TEXT,
        Status TEXT DEFAULT 'Healthy',
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

# ================= LOAD DATA =================
def load_animals():
    return q("SELECT * FROM AnimalMaster")

animals = load_animals()
tags = animals["TagID"].tolist() if not animals.empty else []

st.set_page_config(layout="wide")
st.title("🐄 PRO LIVESTOCK ERP SYSTEM")

# ================= SAFE HISTORY FUNCTION =================
def get_history(table, column, tag):
    return q(f"SELECT * FROM {table} WHERE {column} = ?", (tag,))

# ================= TABS =================
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
    "📈 Dashboard"
])

# ================= 1 COW CARD (FIXED) =================
with tabs[0]:
    st.subheader("🐄 Cow Card (FULL HISTORY FIXED)")

    if len(tags) > 0:
        tag = st.selectbox("Select Animal", tags)

        cow_data = animals[animals["TagID"] == tag]
        st.dataframe(cow_data)

        st.markdown("### 📊 REAL HISTORY")

        vac = get_history("VaccineLogs", "AnimalTag", tag)
        bre = get_history("BreedingLogs", "CowTag", tag)
        cal = get_history("CalvingLogs", "CowTag", tag)
        trt = get_history("TreatmentLogs", "AnimalTag", tag)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("💉 Vaccines", len(vac))
        col2.metric("🧬 Breeding", len(bre))
        col3.metric("🐣 Calving", len(cal))
        col4.metric("🩺 Treatment", len(trt))

        st.markdown("### Full Records")

        st.write("💉 Vaccination History")
        st.dataframe(vac)

        st.write("🧬 Breeding History")
        st.dataframe(bre)

        st.write("🐣 Calving History")
        st.dataframe(cal)

        st.write("🩺 Treatment History")
        st.dataframe(trt)

# ================= 2 ALL ANIMALS =================
with tabs[1]:
    st.subheader("📋 All Animals")
    st.dataframe(animals)

# ================= 3 BREEDING =================
with tabs[2]:
    st.subheader("🧬 Breeding")

    if len(tags) > 0:
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

    if len(tags) > 0:
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

    if len(tags) > 0:
        animal = st.selectbox("Animal", tags)
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

    if len(tags) > 0:
        animal = st.selectbox("Animal", tags)
        disease = st.text_input("Disease")
        medicine = st.text_input("Medicine")
        vet = st.text_input("Vet")

        if st.button("Save Treatment"):
            execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
                  (str(date.today()), animal, disease, medicine, vet))
            st.success("Saved")

# ================= 7 HOSPITAL =================
with tabs[6]:
    st.subheader("🏥 Hospital")

    if len(tags) > 0:
        animal = st.selectbox("Animal", tags)
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

# ================= 8 MOVEMENT =================
with tabs[7]:
    st.subheader("🚚 Movement")

    if len(tags) > 0:
        animal = st.selectbox("Animal", tags)
        pen = st.text_input("Pen")

        if st.button("Move"):
            execq("INSERT INTO MovementLogs VALUES (?,?,?)",
                  (str(date.today()), animal, pen))
            st.success("Moved")

# ================= 9 REPORTS =================
with tabs[8]:
    st.subheader("📊 Reports")

    st.metric("Total Animals", len(animals))
    st.metric("Healthy", len(animals[animals["Status"]=="Healthy"]))
    st.metric("Dead", len(animals[animals["Status"]=="Dead"]))
    st.metric("Culled", len(animals[animals["Status"]=="Culled"]))

# ================= 10 DASHBOARD =================
with tabs[9]:
    st.subheader("📈 Dashboard")

    st.metric("Total Animals", len(animals))
    st.metric("System Status", "ACTIVE")
