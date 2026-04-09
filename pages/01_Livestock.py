import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date, timedelta

# --- 0. DATABASE INITIALIZATION ---
def init_livestock_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY, RFID TEXT, Breed TEXT, Category TEXT, CurrentPen TEXT, 
            Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT, Sire1 TEXT, Sire2 TEXT, LastWeight REAL DEFAULT 0)""")
        
        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS TreatmentLogs (Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS BreedingLogs (Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, DoseQty INTEGER, PD_Result TEXT, Vet TEXT, ExpCalving TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS CalvingLogs (Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, Calf2_Tag TEXT, Calf2_Sex TEXT, Calf1_W REAL, Calf2_W REAL, LactNo INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS WeightLogs (Date TEXT, TagID TEXT, CurrentWeight REAL, PreviousWeight REAL, Gain REAL, DaysGap INTEGER, AvgDailyGain REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS MoveLogs (Date TEXT, TagID TEXT, FromPen TEXT, ToPen TEXT, Reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS VacLogs (Date TEXT, TagIDs TEXT, VaccineName TEXT, Dose REAL, Batch TEXT)")
        conn.commit()

init_livestock_db()

# --- 1. BRANDING ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK PRO <span style='color: #FF851B;'>v11.0</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete 10-Tab Farm Management System</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    try:
        items = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster")
        med_dict = dict(zip(items['ItemName'], items['UOM']))
    except: med_dict = {}
    med_list = ["None"] + list(med_dict.keys())

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# TAB 1: 360°
with t1:
    st.subheader("Herd Inventory")
    st.dataframe(animal_data, use_container_width=True)

# TAB 2: COW CARD
with t2:
    sid = st.selectbox("Select Animal ID", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.markdown(f"### 🐄 CARD: {sid} | Status: {row['Status']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight", f"{row['Weight']} kg")
        c2.metric("Breed", row['Breed'])
        c3.metric("Lactation", row['LactationNo'])
        with db_connect() as conn:
            st.write("**Vaccine/Medical History:**")
            st.dataframe(fetch_df(conn, f"SELECT * FROM VacLogs WHERE TagIDs LIKE '%{sid}%'"), use_container_width=True)
            st.write("**Weight Logs:**")
            st.dataframe(fetch_df(conn, f"SELECT * FROM WeightLogs WHERE TagID='{sid}'"), use_container_width=True)

# TAB 3: MILK
with t3:
    with st.form("milk_f"):
        tag = st.selectbox("Tag ID", tag_list); d = st.date_input("Date", date.today())
        c1, c2, c3 = st.columns(3); m = c1.number_input("Morning"); n = c2.number_input("Noon"); e = c3.number_input("Evening")
        if st.form_submit_button("✅ Save Milk"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
                conn.commit(); st.rerun()

# TAB 4: TREATMENT
with t4:
    with st.form("treat_f"):
        tag = st.selectbox("Select Patient", tag_list)
        cols = st.columns(4); t_ins = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Injection {i+1}", med_list, key=f"tm{i}")
                q = st.number_input(f"Qty {i+1}", key=f"tq{i}")
                u = med_dict.get(m, "-"); t_ins.extend([m, q, u])
        if st.form_submit_button("💉 Log Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *t_ins, "Standard Treatment"))
                conn.commit(); st.rerun()

# TAB 5: BREEDING
with t5:
    with st.form("breed_f"):
        tag = st.selectbox("Cow Tag", tag_list)
        act = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service"])
        pdr = st.radio("PD Result", ["N/A", "Pregnant (+)", "Empty (-)"], horizontal=True)
        if st.form_submit_button("🧬 Save Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Action, PD_Result) VALUES (?,?,?,?)", (str(date.today()), tag, act, pdr))
                if pdr == "Pregnant (+)": conn.execute("UPDATE AnimalMaster SET Status='Pregnant' WHERE TagID=?", (tag,))
                conn.commit(); st.rerun()

# TAB 6: CALVING
with t6:
    with st.form("calv_f"):
        dam = st.selectbox("Dam ID", tag_list); ctype = st.radio("Birth", ["Single", "Twins"])
        c1t = st.text_input("Calf Tag"); c1s = st.selectbox("Sex", ["Heifer", "Bull"])
        if st.form_submit_button("🍼 Register Birth"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs (Date, DamID, Type, Calf1_Tag, Calf1_Sex) VALUES (?,?,?,?,?)", (str(date.today()), dam, ctype, c1t, c1s))
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Status) VALUES (?, 'Calf', 'Active')", (c1t,))
                conn.commit(); st.rerun()

# TAB 7: WEIGHT
with t7:
    with st.form("weight_f"):
        tag = st.selectbox("Animal", tag_list); cur_w = st.number_input("New Weight")
        if st.form_submit_button("⚖️ Update Weight"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Weight=?, LastWeight=Weight WHERE TagID=?", (cur_w, tag))
                conn.execute("INSERT INTO WeightLogs (Date, TagID, CurrentWeight) VALUES (?,?,?)", (str(date.today()), tag, cur_w))
                conn.commit(); st.rerun()

# TAB 8: VACCINATION
with t8:
    with st.form("vac_f"):
        tags = st.text_area("Tags (Separated by comma)"); v_name = st.text_input("Vaccine Name")
        if st.form_submit_button("💉 Log Vaccine"):
            with db_connect() as conn:
                conn.execute("INSERT INTO VacLogs (Date, TagIDs, VaccineName) VALUES (?,?,?)", (str(date.today()), tags, v_name))
                conn.commit(); st.rerun()

# TAB 9: MOVE
with t9:
    with st.form("move_f"):
        tag = st.selectbox("Animal", tag_list); to_p = st.text_input("To Pen")
        if st.form_submit_button("🏠 Move"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET CurrentPen=? WHERE TagID=?", (to_p, tag))
                conn.commit(); st.rerun()

# TAB 10: REGISTRATION
with t10:
    st.subheader("📝 Register New Animal")
    with st.form("reg_final"):
        rtag = st.text_input("Tag ID").upper(); rbreed = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Cross"])
        rstat = st.selectbox("Status", ["Milking", "Dry", "Heifer", "Young Stock"])
        rbirth = st.date_input("Birth Date", date(2022, 1, 1))
        rw = st.number_input("Initial Weight")
        if st.form_submit_button("✅ Register"):
            with db_connect() as conn:
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Breed, BirthDate, Weight, Status) VALUES (?,?,?,?,?)", (rtag, rbreed, str(rbirth), rw, rstat))
                conn.commit(); st.rerun()
