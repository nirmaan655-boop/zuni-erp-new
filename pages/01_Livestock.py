import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date, timedelta

# --- DATABASE INIT ---
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
            LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS BreedingLogs (
            Date TEXT, TagID TEXT, Method TEXT,
            HeatStatus TEXT, SemenName TEXT,
            BullID TEXT, PD_Result TEXT, ExpCalving TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS WeightLogs (
            Date TEXT, TagID TEXT,
            CurrentWeight REAL, PreviousWeight REAL,
            Gain REAL, DaysGap INTEGER, AvgDailyGain REAL
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS CalvingLogs (
            Date TEXT, DamID TEXT, Type TEXT,
            Calf1_Tag TEXT, Calf1_Sex TEXT, Calf1_W REAL, Calf1_Sire TEXT,
            Calf2_Tag TEXT, Calf2_Sex TEXT, Calf2_W REAL, Calf2_Sire TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS MoveLogs (
            Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS VacLogs (
            Date TEXT, TagIDs TEXT, VaccineName TEXT
        )""")

        conn.commit()

init_db()

# --- LOAD DATA ---
with db_connect() as conn:
    animals = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tags = animals["TagID"].tolist() if not animals.empty else []

    # Bull list
    bulls = animals[animals["Category"] == "Bull"]["TagID"].tolist()

# --- UI ---
st.set_page_config(layout="wide")
tabs = st.tabs(["360", "Breeding", "Weight", "Calving", "Move", "Vaccination", "Register"])

# ------------------ 360 ------------------
with tabs[0]:
    st.dataframe(animals, use_container_width=True)

# ------------------ BREEDING ------------------
with tabs[1]:
    st.subheader("Breeding")

    tag = st.selectbox("Select Cow", tags)
    method = st.selectbox("Method", ["AI", "PD", "Natural/Bull"])

    if method == "AI":
        heat = st.selectbox("Heat Status", ["Strong", "Weak"])
        semen = st.text_input("Semen Name")
        exp = st.date_input("Expected Calving", date.today() + timedelta(days=283))

    elif method == "PD":
        pd_result = st.radio("PD Result", ["Pregnant", "Empty"])

    elif method == "Natural/Bull":
        bull = st.selectbox("Select Bull", bulls)

    if st.button("Save Breeding"):
        with db_connect() as conn:
            if method == "AI":
                conn.execute("""INSERT INTO BreedingLogs 
                VALUES (?,?,?,?,?,?,?,?)""",
                (str(date.today()), tag, method, heat, semen, None, None, str(exp)))

            elif method == "PD":
                conn.execute("""INSERT INTO BreedingLogs 
                VALUES (?,?,?,?,?,?,?,?)""",
                (str(date.today()), tag, method, None, None, None, pd_result, None))

            else:
                conn.execute("""INSERT INTO BreedingLogs 
                VALUES (?,?,?,?,?,?,?,?)""",
                (str(date.today()), tag, method, None, None, bull, None, None))

            conn.commit()
            st.success("Saved")

# ------------------ WEIGHT ------------------
with tabs[2]:
    st.subheader("Weight Update")

    tag = st.selectbox("Animal", tags)

    with db_connect() as conn:
        last = fetch_df(conn, "SELECT Weight FROM AnimalMaster WHERE TagID=?", (tag,))
        last_w = float(last.iloc[0]["Weight"]) if not last.empty else 0

    st.write(f"Last Weight: {last_w}")

    new_w = st.number_input("New Weight")

    if st.button("Update Weight"):
        today = date.today()

        with db_connect() as conn:
            prev = fetch_df(conn, """SELECT Date, CurrentWeight 
                                    FROM WeightLogs 
                                    WHERE TagID=? 
                                    ORDER BY Date DESC LIMIT 1""", (tag,))

            if not prev.empty:
                prev_date = datetime.strptime(prev.iloc[0]["Date"], "%Y-%m-%d").date()
                prev_w = prev.iloc[0]["CurrentWeight"]
                days = (today - prev_date).days or 1
            else:
                prev_w = last_w
                days = 1

            gain = new_w - prev_w
            avg = gain / days

            conn.execute("""INSERT INTO WeightLogs VALUES (?,?,?,?,?,?,?)""",
                         (str(today), tag, new_w, prev_w, gain, days, avg))

            conn.execute("""UPDATE AnimalMaster 
                            SET LastWeight=?, Weight=? 
                            WHERE TagID=?""",
                         (prev_w, new_w, tag))

            conn.commit()
            st.success("Weight Updated")

# ------------------ CALVING ------------------
with tabs[3]:
    st.subheader("Calving")

    dam = st.selectbox("Dam", tags)
    ctype = st.radio("Type", ["Single", "Twins"])

    st.markdown("### Calf 1")
    c1_tag = st.text_input("Tag 1")
    c1_sex = st.selectbox("Sex 1", ["Male", "Female"])
    c1_w = st.number_input("Weight 1")
    c1_sire = st.text_input("Sire 1")

    if ctype == "Twins":
        st.markdown("### Calf 2")
        c2_tag = st.text_input("Tag 2")
        c2_sex = st.selectbox("Sex 2", ["Male", "Female"])
        c2_w = st.number_input("Weight 2")
        c2_sire = st.text_input("Sire 2")
    else:
        c2_tag = c2_sex = c2_w = c2_sire = None

    if st.button("Save Calving"):
        with db_connect() as conn:
            conn.execute("""INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                         (str(date.today()), dam, ctype,
                          c1_tag, c1_sex, c1_w, c1_sire,
                          c2_tag, c2_sex, c2_w, c2_sire))

            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category) VALUES (?, 'Calf')", (c1_tag,))
            if ctype == "Twins":
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category) VALUES (?, 'Calf')", (c2_tag,))

            conn.commit()
            st.success("Calving Saved")

# ------------------ MOVE ------------------
with tabs[4]:
    tag = st.selectbox("Animal", tags)
    to_pen = st.text_input("To Pen")

    if st.button("Move"):
        with db_connect() as conn:
            cur = fetch_df(conn, "SELECT CurrentPen FROM AnimalMaster WHERE TagID=?", (tag,))
            from_pen = cur.iloc[0]["CurrentPen"] if not cur.empty else ""

            conn.execute("UPDATE AnimalMaster SET CurrentPen=? WHERE TagID=?", (to_pen, tag))
            conn.execute("INSERT INTO MoveLogs VALUES (?,?,?,?,?)",
                         (str(date.today()), tag, from_pen, to_pen, "Move"))

            conn.commit()
            st.success("Moved")

# ------------------ VACCINATION ------------------
with tabs[5]:
    selected = st.multiselect("Select Animals", tags)
    vname = st.text_input("Vaccine Name")

    if st.button("Save Vaccine"):
        with db_connect() as conn:
            conn.execute("INSERT INTO VacLogs VALUES (?,?,?)",
                         (str(date.today()), ",".join(selected), vname))
            conn.commit()
            st.success("Saved")

# ------------------ REGISTER ------------------
with tabs[6]:
    st.subheader("Register Animal")

    tag = st.text_input("Tag").upper()
    breed = st.selectbox("Breed", ["Sahiwal", "Cholistani", "Cross"])
    cat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
    weight = st.number_input("Weight")

    if st.button("Register"):
        if not tag:
            st.error("Tag required")
        else:
            with db_connect() as conn:
                conn.execute("""INSERT OR REPLACE INTO AnimalMaster 
                                (TagID, Breed, Category, Weight)
                                VALUES (?,?,?,?)""",
                             (tag, breed, cat, weight))
                conn.commit()
                st.success("Registered")
