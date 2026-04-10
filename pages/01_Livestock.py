import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date

st.set_page_config(layout="wide")

# ---------------- LOAD DATA ----------------
with db_connect() as conn:
    animals = fetch_df(conn, "SELECT * FROM AnimalMaster")

if animals is None or animals.empty:
    animals = pd.DataFrame(columns=["TagID","Breed","Category","Weight"])

tags = animals["TagID"].tolist() if "TagID" in animals.columns else []

# ---------------- SEARCH BAR ----------------
st.title("🐄 Livestock ERP PRO")

search = st.text_input("🔍 Search Animal")

if search:
    animals = animals[animals.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)]

st.dataframe(animals, use_container_width=True)

# ---------------- TABS ----------------
tabs = st.tabs(["Cow Card","Milk","Treatment","Breeding","Calving","Weight","Vaccination","Move","Register","Reports"])

# ---------------- COW CARD ----------------
with tabs[0]:
    sid = st.selectbox("Animal", tags, key="cow")
    if sid:
        st.write(animals[animals["TagID"]==sid])

# ---------------- MILK ----------------
with tabs[1]:
    tag = st.selectbox("Animal", tags, key="milk")
    m = st.number_input("Morning")
    n = st.number_input("Noon")
    e = st.number_input("Evening")

    if st.button("Save Milk"):
        with db_connect() as conn:
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)",
                         (str(date.today()), tag, m, n, e, m+n+e))
            conn.commit()

    # HISTORY
    with db_connect() as conn:
        milk_df = fetch_df(conn, "SELECT * FROM MilkLogs WHERE TagID=?", [tag])

    st.subheader("Milk History")
    st.dataframe(milk_df, use_container_width=True)

    # DELETE
    del_id = st.number_input("Row index to delete", step=1, key="milk_del")
    if st.button("Delete Milk Row"):
        with db_connect() as conn:
            conn.execute("DELETE FROM MilkLogs WHERE rowid=?", [del_id])
            conn.commit()

# ---------------- WEIGHT ----------------
with tabs[5]:
    tag = st.selectbox("Animal", tags, key="weight")

    new_w = st.number_input("Weight")

    if st.button("Save Weight"):
        with db_connect() as conn:
            conn.execute("INSERT INTO WeightLogs (Date,TagID,CurrentWeight) VALUES (?,?,?)",
                         (str(date.today()), tag, new_w))
            conn.execute("UPDATE AnimalMaster SET Weight=? WHERE TagID=?", (new_w, tag))
            conn.commit()

    # HISTORY
    with db_connect() as conn:
        wdf = fetch_df(conn, "SELECT * FROM WeightLogs WHERE TagID=?", [tag])

    st.subheader("Weight History")
    st.dataframe(wdf)

    # GRAPH
    if not wdf.empty:
        st.line_chart(wdf.set_index("Date")["CurrentWeight"])

# ---------------- CALVING ----------------
with tabs[4]:
    dam = st.selectbox("Dam", tags, key="calv")

    typ = st.radio("Type",["Single","Twins"], key="ctype")

    c1 = st.text_input("Calf1", key="c1")

    if typ=="Twins":
        c2 = st.text_input("Calf2", key="c2")

    if st.button("Save Calving"):
        with db_connect() as conn:
            conn.execute("INSERT INTO CalvingLogs (Date,DamID,Type,Calf1_Tag,Calf2_Tag) VALUES (?,?,?,?,?)",
                         (str(date.today()), dam, typ, c1, c2 if typ=="Twins" else None))
            conn.commit()

# ---------------- REPORT TAB ----------------
with tabs[9]:
    st.subheader("Reports")

    with db_connect() as conn:
        milk = fetch_df(conn, "SELECT Date, SUM(Total) as TotalMilk FROM MilkLogs GROUP BY Date")

    st.line_chart(milk.set_index("Date"))

    # DOWNLOAD
    csv = milk.to_csv(index=False).encode("utf-8")
    st.download_button("Download Milk Report", csv, "milk_report.csv")
