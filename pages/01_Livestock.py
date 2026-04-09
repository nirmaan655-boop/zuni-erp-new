import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date

# --- 0. DATABASE CONNECTION ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

conn = get_connection()

# --- 1. BRANDING & UI ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro Master")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 15px; border-bottom: 5px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0;'>🐄 ZUNI LIVESTOCK <span style='color: #FF851B;'>PRO MASTER</span></h1>
        <p style='color: #FF851B; font-weight: bold; font-size: 18px;'>Dynamic Farm Management | Version 8.0</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
animal_data = pd.read_sql("SELECT * FROM AnimalMaster", conn)
tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
# Sirf Bulls ki list Natural Service ke liye
bull_list = animal_data[animal_data['Category'] == 'Bull']['TagID'].tolist()

# Semen Bank Items fetching from ItemMaster
try:
    semen_items = pd.read_sql("SELECT ItemName FROM ItemMaster WHERE Category = 'Semen Straws'", conn)['ItemName'].tolist()
except: semen_items = ["Local Semen", "Imported Semen"]

# Medicine mapping for Treatment
try:
    med_df = pd.read_sql("SELECT ItemName, UOM FROM ItemMaster", conn)
    med_dict = dict(zip(med_df['ItemName'], med_df['UOM']))
except: med_dict = {}

def show_history(table, tag=None):
    st.markdown(f"**📋 Recent {table} Records**")
    query = f"SELECT * FROM {table}"
    if tag: query += f" WHERE TagID='{tag}' OR DamID='{tag}'"
    query += " ORDER BY rowid DESC LIMIT 5"
    df = pd.read_sql(query, conn)
    if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. THE 10 TABS ---
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = st.tabs([
    "🔍 360°", "🗂️ COW CARD", "🥛 MILK", "🏥 TREAT", "🧬 BREED", "🍼 CALVING", "⚖️ WEIGHT", "💉 VAC", "🏠 MOVE", "📝 REG"
])

# TAB 1: 360° VIEW
with t1:
    st.subheader("All Animals Status")
    st.dataframe(animal_data, use_container_width=True)

# TAB 2: COW CARD
with t2:
    sid = st.selectbox("Search Animal ID", [""] + tag_list)
    if sid:
        row = animal_data[animal_data['TagID'] == sid].iloc[0]
        st.markdown(f"### 🐄 {sid} | {row['Breed']} | {row['Category']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Weight", f"{row['Weight']} kg")
        c2.metric("Lactation", row['LactationNo'])
        c3.metric("Status", row['Status'])
        show_history("MilkLogs", sid)
        show_history("TreatmentLogs", sid)

# TAB 3: MILK LOGS
with t3:
    with st.form("milk_f"):
        c1, c2 = st.columns(2)
        tag = c1.selectbox("Tag ID", tag_list)
        d = c2.date_input("Date", date.today())
        m1, m2, m3 = st.columns(3)
        m = m1.number_input("Morning"); n = m2.number_input("Noon"); e = m3.number_input("Evening")
        if st.form_submit_button("✅ Save Milk"):
            conn.execute("INSERT INTO MilkLogs VALUES (?,?,?,?,?,?)", (str(d), tag, m, n, e, m+n+e))
            conn.commit(); st.rerun()
    show_history("MilkLogs")

# TAB 4: TREATMENT
with t4:
    with st.form("treat_f"):
        tag = st.selectbox("Animal", tag_list)
        cols = st.columns(4); t_data = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Med {i+1}", ["None"] + list(med_dict.keys()), key=f"m{i}")
                q = st.number_input(f"Qty {i+1}", key=f"q{i}")
                u = med_dict.get(m, "-")
                t_data.extend([m, q, u])
        if st.form_submit_button("💉 Save Treatment"):
            conn.execute("INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), tag, *t_data, "Normal"))
            conn.commit(); st.rerun()

# TAB 5: BREEDING (DYNAMIC AI/PD/NATURAL)
with t5:
    st.subheader("🧬 Breeding & Reproduction")
    with st.form("breed_dynamic"):
        tag = st.selectbox("Cow Tag", tag_list)
        act = st.selectbox("Select Action", ["Insemination (AI)", "PD Check", "Natural Service", "Dry Off"])
        
        # Dynamic Options based on Action
        heat, semen, qty, pd_r, bull = "N/A", "N/A", 0, "N/A", "N/A"
        
        if act == "Insemination (AI)":
            c1, c2, c3 = st.columns(3)
            heat = c1.selectbox("Heat Status", ["Natural", "Ovsynch", "Silent"])
            semen = c2.selectbox("Select Straw (Semen Bank)", semen_items)
            qty = c3.number_input("Doses Used", min_value=1, value=1)
        elif act == "PD Check":
            pd_r = st.radio("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion"], horizontal=True)
        elif act == "Natural Service":
            bull = st.selectbox("Select Bull (from Farm)", bull_list if bull_list else ["No Bull Registered"])
        
        vet = st.text_input("Vet/Inseminator", "Dr. Zuni")
        if st.form_submit_button("🧬 Save Breeding"):
            conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)", (str(date.today()), tag, act, heat, semen, qty, pd_r, vet))
            conn.commit(); st.success("Breeding Data Logged!"); st.rerun()

# TAB 6: CALVING (DYNAMIC SINGLE/TWINS)
with t6:
    st.subheader("🍼 Calving Registration")
    with st.form("calving_dynamic"):
        dam = st.selectbox("Mother (Dam) ID", tag_list)
        ctype = st.radio("Birth Type", ["Single", "Twins"], horizontal=True)
        res = st.selectbox("Result", ["Live Birth", "Stillborn"])
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Calf 1 Details")
            c1t = st.text_input("Calf 1 Tag").upper()
            c1s = st.selectbox("Sex 1", ["Heifer", "Bull"])
            c1w = st.number_input("Weight 1 (kg)", value=30.0)
            
        if ctype == "Twins":
            with col2:
                st.markdown("### Calf 2 Details")
                c2t = st.text_input("Calf 2 Tag").upper()
                c2s = st.selectbox("Sex 2", ["Heifer", "Bull"])
                c2w = st.number_input("Weight 2 (kg)", value=28.0)
        else:
            c2t, c2s, c2w = "N/A", "N/A", 0

        if st.form_submit_button("🍼 Register Birth"):
            if c1t:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (str(date.today()), dam, res, ctype, c1t, c1s, c2t, c2s, c1w, c2w, 1))
                # Add to Master
                conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, BirthDate, Weight, Status) VALUES (?,?,?,?,'Active')", (c1t, "Calf", str(date.today()), c1w))
                if ctype == "Twins" and c2t:
                    conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, BirthDate, Weight, Status) VALUES (?,?,?,?,'Active')", (c2t, "Calf", str(date.today()), c2w))
                conn.commit(); st.success("Birth Registered!"); st.rerun()

# TAB 7: WEIGHT
with t7:
    w_tag = st.selectbox("Select for Weight", [""] + tag_list)
    if w_tag:
        cur_w = st.number_input("Current Weight", min_value=0.0)
        if st.button("⚖️ Log Weight"):
            conn.execute("UPDATE AnimalMaster SET Weight = ? WHERE TagID = ?", (cur_w, w_tag))
            conn.execute("INSERT INTO WeightLogs (Date, TagID, CurrentWeight) VALUES (?,?,?)", (str(date.today()), w_tag, cur_w))
            conn.commit(); st.rerun()

# TAB 10: REGISTRATION
with t10:
    st.subheader("📝 Register New Animal")
    with st.form("reg_new"):
        rtag = st.text_input("Tag ID").upper()
        rcat = st.selectbox("Category", ["Cow", "Heifer", "Bull", "Calf"])
        rbreed = st.selectbox("Breed", ["Cholistani", "Sahiwal", "Friesian", "Cross"])
        rstat = st.selectbox("Status", ["Active", "Dry", "Sold", "Dead"])
        if st.form_submit_button("✅ Register"):
            conn.execute("INSERT OR REPLACE INTO AnimalMaster (TagID, Category, Breed, Status, Weight) VALUES (?,?,?,?,0)", (rtag, rcat, rbreed, rstat))
            conn.commit(); st.success("Registered!"); st.rerun()
