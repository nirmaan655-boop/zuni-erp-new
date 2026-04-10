import streamlit as st
import pandas as pd
from datetime import date
from zuni_db import db_connect, fetch_df

st.set_page_config(layout="wide")

# ---------------- SAFE DB ----------------
def q(sql, params=None):
    try:
        with db_connect() as conn:
            return fetch_df(conn, sql, params)
    except:
        return pd.DataFrame()

def execq(sql, params=None):
    with db_connect() as conn:
        conn.execute(sql, params or ())
        conn.commit()

# ---------------- LOAD ----------------
animals = q("SELECT * FROM AnimalMaster")

if animals.empty:
    animals = pd.DataFrame(columns=["TagID","Status","Category","Weight"])

tags = animals["TagID"].tolist()

st.title("🐄 HRM Dairy ERP - COMPLETE LIVESTOCK SYSTEM")

search = st.text_input("🔍 Search Animal")

if search:
    animals = animals[animals.astype(str).apply(lambda x: x.str.contains(search, case=False).any(), axis=1)]

# ---------------- TABS ----------------
tabs = st.tabs([
    "Cow Card","All Animals","Breeding","Treatment",
    "Hospital","Calving","Weight","Inventory",
    "Movement","Reports","Dashboard"
])

# ================= 1 COW CARD =================
with tabs[0]:
    tag = st.selectbox("Select Animal", tags)

    st.dataframe(animals[animals["TagID"]==tag])

# ================= 2 ALL ANIMALS =================
with tabs[1]:
    st.dataframe(animals)

# ================= 3 BREEDING =================
with tabs[2]:
    tag = st.selectbox("Cow", tags, key="breed")

    protocol = st.selectbox("Protocol", ["Natural","AI","F-T-AI","Heat Sync"])

    bulls = q("SELECT TagID FROM AnimalMaster WHERE Category='Bull'")
    bull = st.selectbox("Bull", bulls["TagID"] if not bulls.empty else [])

    semen_df = q("SELECT * FROM Inventory")
    semen = semen_df[semen_df.get("Type","")=="Semen"]["ItemName"].tolist() if not semen_df.empty else []

    straw = st.selectbox("Semen Straw", semen)

    vet = st.text_input("Vet Name")

    if st.button("Save Breeding"):
        execq("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)",
              (str(date.today()), tag, protocol, straw, bull, vet))

        if straw:
            execq("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (straw,))

# ================= 4 TREATMENT =================
with tabs[3]:
    tag = st.selectbox("Animal", tags, key="treat")

    disease = st.text_input("Disease")

    meds_df = q("SELECT * FROM Inventory")
    meds = meds_df[meds_df.get("Type","")=="Medicine"]["ItemName"].tolist() if not meds_df.empty else []

    selected = st.multiselect("Medicines", meds)

    status = st.selectbox("Status", ["Sick","Under Treatment","Recovered"])

    vet = st.text_input("Vet")

    if st.button("Save Treatment"):
        execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
              (str(date.today()), tag, disease, ",".join(selected), vet))

        for m in selected:
            execq("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (m,))

        execq("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (status, tag))

# ================= 5 HOSPITAL (DEATH + CULLING) =================
with tabs[4]:
    st.subheader("🏥 Hospital Management")

    hospital = q("SELECT * FROM AnimalMaster WHERE Status IN ('Sick','Hospital')")
    st.dataframe(hospital)

    st.markdown("### ⚠️ Critical Actions")

    tag = st.selectbox("Animal", tags, key="hospital")

    action = st.selectbox("Action", ["Recover","Culling","Death"])

    reason = st.text_input("Reason")

    if st.button("Execute Action"):
        if action == "Recover":
            execq("UPDATE AnimalMaster SET Status='Healthy' WHERE TagID=?", (tag,))

        elif action == "Culling":
            execq("UPDATE AnimalMaster SET Status='Culled' WHERE TagID=?", (tag,))
            execq("INSERT INTO CullingLogs VALUES (?,?,?)", (str(date.today()), tag, reason))

        elif action == "Death":
            execq("UPDATE AnimalMaster SET Status='Dead' WHERE TagID=?", (tag,))
            execq("INSERT INTO DeathLogs VALUES (?,?,?)", (str(date.today()), tag, reason))

# ================= 6 CALVING =================
with tabs[5]:
    dam = st.selectbox("Dam", tags, key="calving")

    calving_date = st.date_input("Calving Date")
    sire = st.text_input("Sire")

    calf_gender = st.selectbox("Calf Gender", ["Male","Female"])
    calf_weight = st.number_input("Calf Weight")

    if st.button("Save Calving"):
        execq("INSERT INTO CalvingLogs VALUES (?,?,?,?,?)",
              (str(date.today()), dam, str(calving_date), sire, calf_gender))

# ================= 7 WEIGHT =================
with tabs[6]:
    tag = st.selectbox("Animal", tags, key="weight")

    w = st.number_input("Weight")

    if st.button("Save Weight"):
        execq("INSERT INTO WeightLogs VALUES (?,?,?)",
              (str(date.today()), tag, w))

        execq("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (w, tag))

# ================= 8 INVENTORY =================
with tabs[7]:
    inv = q("SELECT * FROM Inventory")
    st.dataframe(inv)

# ================= 9 MOVEMENT =================
with tabs[8]:
    tag = st.selectbox("Animal", tags, key="move")
    pen = st.text_input("Pen")

    if st.button("Move"):
        execq("INSERT INTO MovementLogs VALUES (?,?,?)",
              (str(date.today()), tag, pen))

# ================= 10 REPORTS =================
with tabs[9]:
    st.subheader("Reports")

    st.dataframe(animals.groupby("Status").size().reset_index(name="Count"))

# ================= 11 DASHBOARD =================
with tabs[10]:
    st.subheader("Dashboard")

    st.metric("Total Animals", len(animals))
    st.metric("Active", len(animals[animals["Status"]=="Healthy"]))
    st.metric("Hospital", len(animals[animals["Status"]=="Sick"]))
    st.metric("Dead", len(animals[animals["Status"]=="Dead"]))
