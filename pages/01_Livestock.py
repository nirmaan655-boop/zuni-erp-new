import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import os

# ================= DATABASE =================
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
        Date TEXT, CowTag TEXT, Type TEXT, Semen TEXT, Protocol TEXT, Vet TEXT
    );

    CREATE TABLE IF NOT EXISTS CalvingLogs (
        Date TEXT, CowTag TEXT, CalvingDate TEXT, SireTag TEXT,
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

setup()

# ================= LOAD =================
animals = q("SELECT * FROM AnimalMaster")
tags = animals["TagID"].tolist() if not animals.empty else []

# ================= UI =================
st.set_page_config(layout="wide")
st.title("🐄 LIVESTOCK ERP PRO (FINAL VERSION)")

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

    if tags:
        tag = st.selectbox("Select Animal", tags, key="card")

        st.dataframe(animals[animals["TagID"] == tag])

        st.metric("Vaccination", len(q("SELECT * FROM VaccineLogs WHERE AnimalTag=?", (tag,))))
        st.metric("Breeding", len(q("SELECT * FROM BreedingLogs WHERE CowTag=?", (tag,))))
        st.metric("Calving", len(q("SELECT * FROM CalvingLogs WHERE CowTag=?", (tag,))))
        st.metric("Treatment", len(q("SELECT * FROM TreatmentLogs WHERE AnimalTag=?", (tag,))))
    else:
        st.warning("No Animals Found. Add via Procurement Module.")

# ================= 2 ALL ANIMALS =================
with tabs[1]:
    st.subheader("All Animals")
    st.dataframe(animals, use_container_width=True)

with tabs[2]:
    st.subheader("🧬 PRO BREEDING MODULE")

    if tags:

        # ================= SELECT COW =================
        cow = st.selectbox("Select Cow", tags, key="cow_main")

        # ================= COW DATA =================
        cow_data = animals[animals["TagID"] == cow]

        st.markdown("### 📋 Cow Profile")
        st.dataframe(cow_data)

        # ================= HEAT INFO =================
        heat_type = st.selectbox(
            "Heat Type",
            ["Standing Heat", "Silent Heat", "Repeat Heat"],
            key="heat"
        )

        heat_strength = st.slider("Heat Strength (1-5)", 1, 5, 3, key="heat_strength")

        # ================= BREEDING TYPE =================
        breed_type = st.selectbox("Breeding Type", ["AI", "Natural"], key="breed_type")

        semen_or_bull = None

        # ================= AI =================
        if breed_type == "AI":
            st.markdown("### 🧪 AI MODE")

            semen_or_bull = st.text_input("Semen Name", key="semen")

            straw_qty = st.number_input("Straw Qty", 1, 10, 1, key="straw")

        # ================= NATURAL =================
        else:
            st.markdown("### 🐂 NATURAL MODE")

            bulls = q("SELECT TagID FROM AnimalMaster WHERE Category='Bull'")

            bull_list = bulls["TagID"].tolist() if not bulls.empty else ["BULL001"]

            semen_or_bull = st.selectbox("Select Bull", bull_list, key="bull")

        # ================= VET =================
        vet = st.text_input("Vet Name", key="vet")

        # ================= FERTILITY SCORE =================
        st.markdown("### 🧠 Fertility Score")

        score = (heat_strength * 20)

        if cow_data.shape[0] > 0:
            if cow_data.iloc[0]["Status"] == "Healthy":
                score += 20
            if cow_data.iloc[0]["Weight"] > 350:
                score += 20

        score = min(score, 100)

        if score >= 80:
            st.success(f"🟢 Excellent Fertility Score: {score}")
        elif score >= 50:
            st.warning(f"🟡 Medium Fertility Score: {score}")
        else:
            st.error(f"🔴 Low Fertility Score: {score}")

        # ================= SAVE BREEDING =================
        if st.button("Save Breeding Record", key="save_breed"):

            execq("""
            INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)
            """, (
                str(date.today()),
                cow,
                breed_type,
                semen_or_bull,
                heat_type,
                vet
            ))

            st.success("Breeding Saved ✔")

        # ================= PD SECTION =================
        st.markdown("### 🧪 Pregnancy Diagnosis (PD)")

        pd_result = st.selectbox("PD Result", ["Not Done", "Pregnant", "Open"], key="pd")

        if pd_result == "Pregnant":

            expected_calving = pd.to_datetime(date.today()) + pd.Timedelta(days=280)

            st.info(f"📅 Expected Calving Date: {expected_calving.date()}")

        # ================= HISTORY =================
        st.markdown("### 📊 Breeding History")

        history = q("SELECT * FROM BreedingLogs WHERE CowTag=?", (cow,))
        st.dataframe(history)

# ================= 4 CALVING =================
with tabs[3]:
    st.subheader("🐣 Calving (TWINS ENABLED)")

    if tags:
        cow = st.selectbox("Cow", tags, key="c1")

        calving_date = st.date_input("Calving Date", key="c2")
        sire = st.text_input("Sire Tag", key="c3")

        twins = st.checkbox("Twins", key="c4")

        st.markdown("### Calf 1")
        g1 = st.selectbox("Gender", ["Male","Female"], key="c5")
        w1 = st.number_input("Weight", key="c6")

        g2 = None
        w2 = None

        if twins:
            st.markdown("### Calf 2")
            g2 = st.selectbox("Gender 2", ["Male","Female"], key="c7")
            w2 = st.number_input("Weight 2", key="c8")

        if st.button("Save Calving", key="c9"):

            execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?)",
                  (str(date.today()), cow, str(calving_date), sire, g1, w1))

            if twins:
                execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?)",
                      (str(date.today()), cow, str(calving_date), sire, g2, w2))

            execq("UPDATE AnimalMaster SET Status='Fresh' WHERE TagID=?", (cow,))

            st.success("Saved")

# ================= 5 VACCINE =================
with tabs[4]:
    st.subheader("Vaccination")

    if tags:
        a = st.selectbox("Animal", tags, key="v1")
        v = st.text_input("Vaccine", key="v2")
        d = st.text_input("Dose", key="v3")
        vet = st.text_input("Vet", key="v4")

        if st.button("Save", key="v5"):
            execq("INSERT INTO VaccineLogs VALUES (?,?,?,?,?)",
                  (str(date.today()), a, v, d, vet))
            st.success("Saved")

# ================= 6 TREATMENT =================
with tabs[5]:
    st.subheader("Treatment")

    if tags:
        a = st.selectbox("Animal", tags, key="t1")
        dis = st.text_input("Disease", key="t2")
        med = st.text_input("Medicine", key="t3")
        vet = st.text_input("Vet", key="t4")

        if st.button("Save", key="t5"):
            execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
                  (str(date.today()), a, dis, med, vet))
            st.success("Saved")

# ================= 7 HOSPITAL =================
with tabs[6]:
    st.subheader("Hospital")

    if tags:
        a = st.selectbox("Animal", tags, key="h1")
        act = st.selectbox("Action", ["Recover","Death","Culling"], key="h2")
        r = st.text_input("Reason", key="h3")

        if st.button("Execute", key="h4"):
            if act == "Death":
                execq("INSERT INTO DeathLogs VALUES (?,?,?)",
                      (str(date.today()), a, r))
                execq("UPDATE AnimalMaster SET Status='Dead' WHERE TagID=?", (a,))

            elif act == "Culling":
                execq("INSERT INTO CullingLogs VALUES (?,?,?)",
                      (str(date.today()), a, r))
                execq("UPDATE AnimalMaster SET Status='Culled' WHERE TagID=?", (a,))

            else:
                execq("UPDATE AnimalMaster SET Status='Healthy' WHERE TagID=?", (a,))

            st.success("Done")

# ================= 8 MOVEMENT =================
with tabs[7]:
    st.subheader("Movement")

    if tags:
        a = st.selectbox("Animal", tags, key="m1")
        p = st.text_input("Pen", key="m2")

        if st.button("Move", key="m3"):
            execq("INSERT INTO MovementLogs VALUES (?,?,?)",
                  (str(date.today()), a, p))
            st.success("Moved")

# ================= 9 REPORTS =================
with tabs[8]:
    st.subheader("Reports")

    st.metric("Total", len(animals))
    st.metric("Healthy", len(animals[animals["Status"]=="Healthy"]))
    st.metric("Dead", len(animals[animals["Status"]=="Dead"]))
    st.metric("Culled", len(animals[animals["Status"]=="Culled"]))

# ================= 10 DASHBOARD =================
with tabs[9]:
    st.subheader("Dashboard")
    st.success("System Running Perfect")
    st.metric("Animals", len(animals))

# ================= 11 FULL HISTORY =================
with tabs[10]:
    st.subheader("Full History")

    if tags:
        a = st.selectbox("Animal", tags, key="f1")

        st.write("Breeding")
        st.dataframe(q("SELECT * FROM BreedingLogs WHERE CowTag=?", (a,)))

        st.write("Calving")
        st.dataframe(q("SELECT * FROM CalvingLogs WHERE CowTag=?", (a,)))

        st.write("Vaccination")
        st.dataframe(q("SELECT * FROM VaccineLogs WHERE AnimalTag=?", (a,)))

        st.write("Treatment")
        st.dataframe(q("SELECT * FROM TreatmentLogs WHERE AnimalTag=?", (a,)))
