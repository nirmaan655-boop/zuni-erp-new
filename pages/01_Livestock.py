import streamlit as st
import pandas as pd
from datetime import date
from zuni_db import db_connect, fetch_df

st.set_page_config(layout="wide")

# ---------------- DB HELPERS ----------------
def q(sql, params=None):
    with db_connect() as conn:
        return fetch_df(conn, sql, params)

def execq(sql, params=None):
    with db_connect() as conn:
        conn.execute(sql, params or ())
        conn.commit()

# ---------------- LOAD ----------------
animals = q("SELECT * FROM AnimalMaster")

if animals.empty:
    animals = pd.DataFrame(columns=["TagID","Status","Category","Weight"])

tags = animals["TagID"].astype(str).tolist()

st.title("🐄 HRM Dairy ERP - FINAL PROFESSIONAL SYSTEM")

# ---------------- SEARCH ----------------
search = st.text_input("🔍 Search Animal")

if search:
    animals = animals[animals.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)]

# ---------------- TABS ----------------
tabs = st.tabs([
    "Cow Card","Breeding","Treatment","Hospital","Calving",
    "Weight","Inventory","Movement","Culling","Death","Reports"
])

# ================= 1 COW CARD =================
with tabs[0]:
    tag = st.selectbox("Animal", tags, key="cow")

    st.dataframe(animals[animals["TagID"]==tag])

# ================= 2 BREEDING =================
with tabs[1]:
    tag = st.selectbox("Cow", tags, key="breed")

    protocol = st.selectbox("Protocol", [
        "Natural","AI","Fixed Time AI","Heat Sync","Observation"
    ])

    straw = q("SELECT ItemName FROM Inventory WHERE Type='Semen'")
    straw_item = st.selectbox("Semen Straw", straw["ItemName"] if not straw.empty else [])

    bull = q("SELECT TagID FROM AnimalMaster WHERE Category='Bull'")
    bull_id = st.selectbox("Bull Tag", bull["TagID"] if not bull.empty else [])

    heat = st.selectbox("Heat Status", ["Observed","Not Observed"])

    vet = st.text_input("Vet Name")

    if st.button("Save Breeding"):
        execq("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?)",
              (str(date.today()), tag, protocol, straw_item, bull_id, vet))

        if straw_item:
            execq("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (straw_item,))

# ================= 3 TREATMENT =================
with tabs[2]:
    tag = st.selectbox("Animal", tags, key="treat")

    disease = st.text_input("Disease")

    meds = q("SELECT ItemName FROM Inventory WHERE Type='Medicine'")
    selected = st.multiselect("Medicines (3-4 allowed)", meds["ItemName"] if not meds.empty else [])

    vet = st.text_input("Vet")

    status = st.selectbox("Status", ["Sick","Under Treatment","Recovered"])

    if st.button("Save Treatment"):
        execq("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?)",
              (str(date.today()), tag, disease, ",".join(selected), vet))

        for m in selected:
            execq("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (m,))

        execq("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (status, tag))

# ================= 4 HOSPITAL =================
with tabs[3]:
    st.subheader("🏥 Hospital Animals")

    hospital = q("SELECT * FROM AnimalMaster WHERE Status IN ('Sick','Hospital')")
    st.dataframe(hospital)

    recover = st.selectbox("Recover Animal", hospital["TagID"] if not hospital.empty else [])

    if st.button("Mark Recovered"):
        execq("UPDATE AnimalMaster SET Status='Healthy' WHERE TagID=?", (recover,))

# ================= 5 CALVING (FULL) =================
with tabs[4]:
    dam = st.selectbox("Dam", tags, key="calv")

    calving_date = st.date_input("Calving Date")
    sire = st.text_input("Sire / Bull Tag")

    calf_count = st.selectbox("Calves", ["Single","Twins"])

    calf1_weight = st.number_input("Calf 1 Weight")
    calf1_gender = st.selectbox("Calf 1 Gender", ["Male","Female"])

    calf2_weight = 0
    calf2_gender = ""

    if calf_count == "Twins":
        calf2_weight = st.number_input("Calf 2 Weight")
        calf2_gender = st.selectbox("Calf 2 Gender", ["Male","Female"])

    if st.button("Save Calving"):
        execq("""INSERT INTO CalvingLogs 
              VALUES (?,?,?,?,?,?,?,?,?)""",
              (str(date.today()), dam, str(calving_date),
               sire, calf_count,
               calf1_weight, calf1_gender,
               calf2_weight, calf2_gender))

# ================= 6 WEIGHT =================
with tabs[5]:
    tag = st.selectbox("Animal", tags, key="weight")

    w = st.number_input("Weight")

    if st.button("Save Weight"):
        execq("INSERT INTO WeightLogs VALUES (?,?,?)",
              (str(date.today()), tag, w))

        execq("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (w, tag))

# ================= 7 INVENTORY =================
with tabs[6]:
    st.subheader("Inventory Stock")

    inv = q("SELECT * FROM Inventory")
    st.dataframe(inv)

# ================= 8 MOVEMENT =================
with tabs[7]:
    tag = st.selectbox("Animal", tags, key="move")
    pen = st.text_input("Pen")

    if st.button("Move"):
        execq("INSERT INTO MovementLogs VALUES (?,?,?)",
              (str(date.today()), tag, pen))

# ================= 9 CULLING =================
with tabs[8]:
    culled = q("SELECT * FROM AnimalMaster WHERE Status='Culled'")
    st.dataframe(culled)

    tag = st.selectbox("Culling Animal", tags, key="cull")

    if st.button("CULL"):
        execq("UPDATE AnimalMaster SET Status='Culled' WHERE TagID=?", (tag,))

# ================= 10 DEATH =================
with tabs[9]:
    st.subheader("💀 Death Register")

    dead = q("SELECT * FROM AnimalMaster WHERE Status='Dead'")
    st.dataframe(dead)

    tag = st.selectbox("Mark Dead", tags, key="death")

    cause = st.text_input("Cause of Death")

    if st.button("Mark Dead"):
        execq("UPDATE AnimalMaster SET Status='Dead' WHERE TagID=?", (tag,))
        execq("INSERT INTO DeathLogs VALUES (?,?,?)",
              (str(date.today()), tag, cause))

# ================= 11 REPORTS =================
with tabs[10]:
    st.subheader("📊 Reports Dashboard")

    milk = q("SELECT Date, SUM(Total) as Milk FROM MilkLogs GROUP BY Date")

    st.dataframe(milk)

    if not milk.empty:
        st.line_chart(milk.set_index("Date")["Milk"])
