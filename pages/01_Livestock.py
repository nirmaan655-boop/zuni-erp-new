import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date

st.set_page_config(layout="wide")

# ---------------- LOAD ----------------
with db_connect() as conn:
    animals = fetch_df(conn, "SELECT * FROM AnimalMaster")

if animals is None or animals.empty:
    animals = pd.DataFrame(columns=["TagID","Category","Weight"])

tags = animals["TagID"].tolist()

# ---------------- UI ----------------
st.title("🐄 HRM Dairy - Livestock ERP PRO")

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
    m = st.number_input("Morning")
    e = st.number_input("Evening")

    if st.button("Save Milk"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?)",
                         (str(date.today()), tag, m, e, m+e))
            conn.commit()

    df = fetch_df(db_connect(), "SELECT * FROM MilkLogs WHERE TagID=?", [tag])
    st.dataframe(df)

# ---------------- 3 TREATMENT ----------------
with tabs[2]:
    tag = st.selectbox("Animal", tags, key="treat")

    with db_connect() as conn:
        meds = fetch_df(conn, "SELECT ItemName,UOM FROM Inventory WHERE Type='Medicine'")

    med = st.selectbox("Medicine", meds["ItemName"], key="med")
    qty = st.number_input("Qty")

    if st.button("Save Treatment"):
        with db_connect() as conn:
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?)",
                         (str(date.today()), tag, med, qty))

            # 🔥 STOCK MINUS
            conn.execute("UPDATE Inventory SET Qty=Qty-? WHERE ItemName=?", (qty, med))
            conn.commit()

    df = fetch_df(db_connect(), "SELECT * FROM TreatmentLogs WHERE TagID=?", [tag])
    st.dataframe(df)

# ---------------- 4 BREEDING ----------------
with tabs[3]:
    tag = st.selectbox("Cow", tags, key="breed")

    typ = st.selectbox("Type", ["AI","PD","Bull"])

    if typ=="AI":
        semen = st.selectbox("Semen", fetch_df(db_connect(),"SELECT ItemName FROM Inventory WHERE Type='Semen'")["ItemName"])

    if typ=="Bull":
        bulls = animals[animals["Category"]=="Bull"]["TagID"]
        semen = st.selectbox("Bull", bulls)

    if st.button("Save Breeding"):
        with db_connect() as conn:
            conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?)",
                         (str(date.today()), tag, typ, semen if typ!="PD" else None))

            if typ=="AI":
                conn.execute("UPDATE Inventory SET Qty=Qty-1 WHERE ItemName=?", (semen,))
            conn.commit()

    df = fetch_df(db_connect(), "SELECT * FROM BreedingLogs WHERE TagID=?", [tag])
    st.dataframe(df)

# ---------------- 5 CALVING ----------------
with tabs[4]:
    dam = st.selectbox("Dam", tags, key="calv")

    typ = st.radio("Type",["Single","Twins"])

    c1 = st.text_input("Calf 1")

    c2 = ""
    if typ=="Twins":
        c2 = st.text_input("Calf 2")

    if st.button("Save Calving"):
        with db_connect() as conn:
            conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?)",
                         (str(date.today()), dam, typ, c1, c2))
            conn.commit()

# ---------------- 6 WEIGHT ----------------
with tabs[5]:
    tag = st.selectbox("Animal", tags, key="weight")

    w = st.number_input("Weight")

    if st.button("Save Weight"):
        with db_connect() as conn:
            conn.execute("INSERT INTO WeightLogs VALUES (?,?,?)",
                         (str(date.today()), tag, w))
            conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (w, tag))
            conn.commit()

    df = fetch_df(db_connect(), "SELECT * FROM WeightLogs WHERE TagID=?", [tag])
    st.dataframe(df)

    if not df.empty:
        st.line_chart(df.set_index("Date")["Weight"])

# ---------------- 7 VACCINATION ----------------
with tabs[6]:
    sel = st.multiselect("Animals", tags)

    vac = st.selectbox("Vaccine",
        fetch_df(db_connect(),"SELECT ItemName FROM Inventory WHERE Type='Vaccine'")["ItemName"]
    )

    if st.button("Save Vaccination"):
        with db_connect() as conn:
            for t in sel:
                conn.execute("INSERT INTO VaccinationLogs VALUES (?,?,?)",
                             (str(date.today()), t, vac))
            conn.execute("UPDATE Inventory SET Qty=Qty-? WHERE ItemName=?", (len(sel), vac))
            conn.commit()

# ---------------- 8 MOVEMENT ----------------
with tabs[7]:
    tag = st.selectbox("Animal", tags, key="move")

    loc = st.text_input("New Location")

    if st.button("Move"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MovementLogs VALUES (?,?,?)",
                         (str(date.today()), tag, loc))
            conn.commit()

# ---------------- 9 SEMEN ----------------
with tabs[8]:
    st.subheader("Semen Usage Log")

    df = fetch_df(db_connect(), "SELECT * FROM BreedingLogs WHERE Type='AI'")
    st.dataframe(df)

# ---------------- 10 PEN REGISTER ----------------
with tabs[9]:
    tag = st.selectbox("Animal", tags, key="pen")

    pen = st.text_input("Pen")

    if st.button("Assign Pen"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MovementLogs VALUES (?,?,?)",
                         (str(date.today()), tag, pen))
            conn.commit()

# ---------------- 11 REPORTS ----------------
with tabs[10]:
    st.subheader("Reports")

    with db_connect() as conn:
        milk = fetch_df(conn, "SELECT Date, SUM(Total) as Milk FROM MilkLogs GROUP BY Date")

    st.line_chart(milk.set_index("Date"))

    csv = milk.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report", csv, "report.csv")
