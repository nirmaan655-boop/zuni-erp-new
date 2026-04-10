import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date

st.set_page_config(layout="wide")

# ---------------- SAFE FETCH ----------------
def safe_fetch(query, params=None):
    with db_connect() as conn:
        try:
            return fetch_df(conn, query, params)
        except:
            return pd.DataFrame()

# ---------------- LOAD ANIMALS ----------------
animals = safe_fetch("SELECT * FROM AnimalMaster")

if animals.empty:
    animals = pd.DataFrame(columns=["TagID","Category","Weight"])

tags = animals["TagID"].dropna().astype(str).tolist()

# ---------------- UI ----------------
st.title("🐄 HRM Dairy ERP PRO")

search = st.text_input("🔍 Search Animal")

if search:
    animals = animals[animals.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)]

st.dataframe(animals, use_container_width=True)

# ---------------- TABS ----------------
tabs = st.tabs([
    "Cow Card","Milk","Treatment","Breeding","Calving",
    "Weight","Vaccination","Movement","Semen","Pen Register","Reports"
])

# ---------------- 1 COW CARD ----------------
with tabs[0]:
    tag = st.selectbox("Animal", tags, key="cow")
    st.dataframe(animals[animals["TagID"]==tag])

# ---------------- 2 MILK ----------------
with tabs[1]:
    tag = st.selectbox("Animal", tags, key="milk")

    m = st.number_input("Morning", key="m")
    e = st.number_input("Evening", key="e")

    if st.button("Save Milk", key="milk_save"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?)",
                         (str(date.today()), tag, m, e, m+e))
            conn.commit()

    df = safe_fetch("SELECT rowid,* FROM MilkLogs WHERE TagID=?", [tag])
    st.dataframe(df)

    rid = st.number_input("Delete Row ID", step=1, key="milk_del")
    if st.button("Delete Milk", key="milk_btn"):
        with db_connect() as conn:
            conn.execute("DELETE FROM MilkLogs WHERE rowid=?", (rid,))
            conn.commit()

# ---------------- 3 TREATMENT ----------------
with tabs[2]:
    tag = st.selectbox("Animal", tags, key="treat")

    meds = safe_fetch("SELECT ItemName,UOM FROM Inventory WHERE Type='Medicine'")
    med = st.selectbox("Medicine", meds["ItemName"] if not meds.empty else [], key="med")
    qty = st.number_input("Qty", key="med_qty")

    if st.button("Save Treatment"):
        with db_connect() as conn:
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?)",
                         (str(date.today()), tag, med, qty))
            conn.execute("UPDATE Inventory SET Qty=Qty-? WHERE ItemName=?", (qty, med))
            conn.commit()

    st.dataframe(safe_fetch("SELECT rowid,* FROM TreatmentLogs WHERE TagID=?", [tag]))

# ---------------- 4 BREEDING ----------------
with tabs[3]:
    tag = st.selectbox("Cow", tags, key="breed")

    typ = st.selectbox("Type", ["AI","PD","Bull"], key="btype")

    semen = None

    if typ=="AI":
        sem = safe_fetch("SELECT ItemName FROM Inventory WHERE Type='Semen'")
        semen = st.selectbox("Semen", sem["ItemName"] if not sem.empty else [], key="sem")

    elif typ=="Bull":
        bulls = animals[animals["Category"]=="Bull"]["TagID"]
        semen = st.selectbox("Bull", bulls, key="bull")

    if st.button("Save Breeding"):
        with db_connect() as conn:
            conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?)",
                         (str(date.today()), tag, typ, semen))

            if typ=="AI":
                conn.execute("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (semen,))
            conn.commit()

    st.dataframe(safe_fetch("SELECT rowid,* FROM BreedingLogs WHERE TagID=?", [tag]))

# ---------------- 5 CALVING ----------------
with tabs[4]:
    dam = st.selectbox("Dam", tags, key="calv")

    typ = st.radio("Type",["Single","Twins"], key="ctype")

    c1 = st.text_input("Calf 1", key="c1")
    c2 = st.text_input("Calf 2", key="c2") if typ=="Twins" else ""

    if st.button("Save Calving"):
        with db_connect() as conn:
            conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?)",
                         (str(date.today()), dam, typ, c1, c2))
            conn.commit()

    st.dataframe(safe_fetch("SELECT rowid,* FROM CalvingLogs WHERE DamID=?", [dam]))

# ---------------- 6 WEIGHT ----------------
with tabs[5]:
    tag = st.selectbox("Animal", tags, key="weight")

    w = st.number_input("Weight", key="w")

    if st.button("Save Weight"):
        with db_connect() as conn:
            conn.execute("INSERT INTO WeightLogs VALUES (?,?,?)",
                         (str(date.today()), tag, w))
            conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (w, tag))
            conn.commit()

    df = safe_fetch("SELECT * FROM WeightLogs WHERE TagID=?", [tag])
    st.dataframe(df)

    if not df.empty:
        st.line_chart(df.set_index("Date")["Weight"])

# ---------------- 7 VACCINATION ----------------
with tabs[6]:
    sel = st.multiselect("Animals", tags, key="vac_animals")

    vacs = safe_fetch("SELECT ItemName FROM Inventory WHERE Type='Vaccine'")
    vac = st.selectbox("Vaccine", vacs["ItemName"] if not vacs.empty else [], key="vac")

    if st.button("Save Vaccination"):
        with db_connect() as conn:
            for t in sel:
                conn.execute("INSERT INTO VaccinationLogs VALUES (?,?,?)",
                             (str(date.today()), t, vac))
            conn.execute("UPDATE Inventory SET Qty=Qty-? WHERE ItemName=?", (len(sel), vac))
            conn.commit()

    st.dataframe(safe_fetch("SELECT * FROM VaccinationLogs"))

# ---------------- 8 MOVEMENT ----------------
with tabs[7]:
    tag = st.selectbox("Animal", tags, key="move")

    loc = st.text_input("Location", key="loc")

    if st.button("Move"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MovementLogs VALUES (?,?,?)",
                         (str(date.today()), tag, loc))
            conn.commit()

    st.dataframe(safe_fetch("SELECT * FROM MovementLogs WHERE TagID=?", [tag]))

# ---------------- 9 SEMEN ----------------
with tabs[8]:
    st.dataframe(safe_fetch("SELECT * FROM BreedingLogs WHERE Type='AI'"))

# ---------------- 10 PEN REGISTER ----------------
with tabs[9]:
    tag = st.selectbox("Animal", tags, key="pen")

    pen = st.text_input("Pen", key="pen_val")

    if st.button("Assign Pen"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MovementLogs VALUES (?,?,?)",
                         (str(date.today()), tag, pen))
            conn.commit()

    st.dataframe(safe_fetch("SELECT * FROM MovementLogs WHERE TagID=?", [tag]))

# ---------------- 11 REPORTS ----------------
with tabs[10]:
    st.subheader("Milk Report")

    milk = safe_fetch("SELECT Date, SUM(Total) as Total FROM MilkLogs GROUP BY Date")

    st.dataframe(milk)

    if not milk.empty:
        st.line_chart(milk.set_index("Date"))

    csv = milk.to_csv(index=False).encode("utf-8")
    st.download_button("Download Excel", csv, "milk_report.csv")
