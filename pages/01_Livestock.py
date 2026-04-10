import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date, timedelta

# ---------------- INIT DB ----------------
def init_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY,
            Breed TEXT,
            Category TEXT,
            CurrentPen TEXT,
            Weight REAL DEFAULT 0,
            LastWeight REAL DEFAULT 0,
            Status TEXT,
            BirthDate TEXT
        )""")

        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")

        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, Med2 TEXT, Qty2 REAL, Med3 TEXT, Qty3 REAL, Med4 TEXT, Qty4 REAL)")

        conn.execute("""CREATE TABLE IF NOT EXISTS BreedingLogs (
            Date TEXT, TagID TEXT, Method TEXT,
            HeatStatus TEXT, SemenName TEXT,
            BullID TEXT, PD_Result TEXT, ExpCalving TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS CalvingLogs (
            Date TEXT, DamID TEXT, Type TEXT,
            Calf1_Tag TEXT, Calf1_Sex TEXT, Calf1_W REAL, Calf1_Sire TEXT,
            Calf2_Tag TEXT, Calf2_Sex TEXT, Calf2_W REAL, Calf2_Sire TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS WeightLogs (
            Date TEXT, TagID TEXT,
            CurrentWeight REAL, PreviousWeight REAL,
            Gain REAL, DaysGap INTEGER, AvgDailyGain REAL
        )""")

        conn.execute("CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")

        conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT)")

        conn.commit()

init_db()

# ---------------- LOAD SAFE ----------------
with db_connect() as conn:
    animals = fetch_df(conn, "SELECT * FROM AnimalMaster")

if animals is None or animals.empty:
    animals = pd.DataFrame(columns=["TagID","Breed","Category","CurrentPen","Weight","LastWeight","Status","BirthDate"])

animals.columns = animals.columns.str.strip()

tags = animals["TagID"].tolist() if "TagID" in animals.columns else []
bulls = animals[animals["Category"] == "Bull"]["TagID"].tolist() if "Category" in animals.columns else []

# ---------------- UI ----------------
st.set_page_config(layout="wide")
tabs = st.tabs(["360°","Cow Card","Milk","Treatment","Breeding","Calving","Weight","Vaccination","Move","Register"])

# ---------------- 1. 360 ----------------
with tabs[0]:
    st.dataframe(animals, use_container_width=True)

# ---------------- 2. COW CARD ----------------
with tabs[1]:
    sid = st.selectbox("Select Animal", [""]+tags)
    if sid:
        row = animals[animals["TagID"] == sid].iloc[0]
        st.metric("Weight", row["Weight"])
        st.write("Breed:", row["Breed"])
        st.write("Status:", row["Status"])

# ---------------- 3. MILK ----------------
with tabs[2]:
    tag = st.selectbox("Animal", tags)
    m = st.number_input("Morning")
    n = st.number_input("Noon")
    e = st.number_input("Evening")

    if st.button("Save Milk"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)",
                         (str(date.today()), tag, m, n, e, m+n+e))
            conn.commit()
            st.success("Saved")

# ---------------- 4. TREATMENT ----------------
with tabs[3]:
    tag = st.selectbox("Animal", tags)
    med1 = st.text_input("Medicine 1")
    qty1 = st.number_input("Qty 1")

    if st.button("Save Treatment"):
        with db_connect() as conn:
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (str(date.today()), tag, med1, qty1, None, None, None, None, None, None))
            conn.commit()
            st.success("Saved")

# ---------------- 5. BREEDING ----------------
with tabs[4]:
    tag = st.selectbox("Cow", tags)
    method = st.selectbox("Method", ["AI","PD","Natural/Bull"])

    heat=semen=bull=pd_result=exp=None

    if method=="AI":
        heat=st.selectbox("Heat",["Strong","Weak"])
        semen=st.text_input("Semen")
        exp=st.date_input("Exp Calving", date.today()+timedelta(days=283))

    elif method=="PD":
        pd_result=st.radio("PD",["Pregnant","Empty"])

    else:
        bull=st.selectbox("Bull", bulls)

    if st.button("Save Breeding"):
        with db_connect() as conn:
            conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)",
                         (str(date.today()), tag, method, heat, semen, bull, pd_result, str(exp) if exp else None))
            conn.commit()
            st.success("Saved")

# ---------------- 6. CALVING ----------------
with tabs[5]:
    dam = st.selectbox("Dam", tags)
    typ = st.radio("Type",["Single","Twins"])

    c1 = st.text_input("Calf1 Tag")
    c1s = st.selectbox("Sex1",["Male","Female"])
    c1w = st.number_input("Weight1")

    if typ=="Twins":
        c2 = st.text_input("Calf2 Tag")
        c2s = st.selectbox("Sex2",["Male","Female"])
        c2w = st.number_input("Weight2")
    else:
        c2=c2s=c2w=None

    if st.button("Save Calving"):
        with db_connect() as conn:
            conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (str(date.today()), dam, typ, c1, c1s, c1w, None, c2, c2s, c2w, None))
            conn.commit()
            st.success("Saved")

# ---------------- 7. WEIGHT ----------------
with tabs[6]:
    tag = st.selectbox("Animal", [""]+tags)

    if tag:
        with db_connect() as conn:
            last = fetch_df(conn, "SELECT Weight FROM AnimalMaster WHERE TagID=?", [tag])
            last_w = float(last.iloc[0]["Weight"]) if not last.empty else 0
    else:
        last_w=0

    st.info(f"Last Weight: {last_w}")
    new_w = st.number_input("New Weight")

    if st.button("Update"):
        today=date.today()

        with db_connect() as conn:
            conn.execute("UPDATE AnimalMaster SET LastWeight=?, Weight=? WHERE TagID=?",
                         (last_w, new_w, tag))
            conn.commit()
            st.success("Updated")

# ---------------- 8. VACCINATION ----------------
with tabs[7]:
    sel = st.multiselect("Animals", tags)
    v = st.text_input("Vaccine")

    if st.button("Save"):
        with db_connect() as conn:
            conn.execute("INSERT INTO VacLogs VALUES (?,?,?)",
                         (str(date.today()), ",".join(sel), v))
            conn.commit()
            st.success("Saved")

# ---------------- 9. MOVE ----------------
with tabs[8]:
    tag = st.selectbox("Animal", tags)
    pen = st.text_input("To Pen")

    if st.button("Move"):
        with db_connect() as conn:
            conn.execute("UPDATE AnimalMaster SET CurrentPen=? WHERE TagID=?",
                         (pen, tag))
            conn.commit()
            st.success("Moved")

# ---------------- 10. REGISTER ----------------
with tabs[9]:
    tag = st.text_input("Tag")
    breed = st.selectbox("Breed",["Sahiwal","Cholistani","Cross"])
    cat = st.selectbox("Category",["Cow","Heifer","Bull","Calf"])
    w = st.number_input("Weight")

    if st.button("Register"):
        with db_connect() as conn:
            conn.execute("INSERT OR REPLACE INTO AnimalMaster VALUES (?,?,?,?,?,?,?,?)",
                         (tag, breed, cat, "", w, 0, "Active", ""))
            conn.commit()
            st.success("Registered")
