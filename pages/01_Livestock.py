import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import datetime, date

# --- 0. DATABASE INITIALIZATION ---
def init_livestock_db():
    with db_connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS AnimalMaster (
            TagID TEXT PRIMARY KEY, Breed TEXT, Category TEXT, CurrentPen TEXT, 
            Weight REAL DEFAULT 0, Status TEXT DEFAULT 'Active', LactationNo INTEGER DEFAULT 0,
            BirthDate TEXT, Sire1 TEXT, Sire2 TEXT)""")
        
        conn.execute("CREATE TABLE IF NOT EXISTS MilkLogs (Date TEXT, TagID TEXT, Morning REAL, Noon REAL, Evening REAL, Total REAL)")
        
        conn.execute("""CREATE TABLE IF NOT EXISTS TreatmentLogs (
            Date TEXT, TagID TEXT, Med1 TEXT, Qty1 REAL, UOM1 TEXT, Med2 TEXT, Qty2 REAL, UOM2 TEXT, 
            Med3 TEXT, Qty3 REAL, UOM3 TEXT, Med4 TEXT, Qty4 REAL, UOM4 TEXT, Symptoms TEXT)""")
            
        conn.execute("""CREATE TABLE IF NOT EXISTS BreedingLogs (
            Date TEXT, TagID TEXT, Action TEXT, HeatStatus TEXT, SemenName TEXT, 
            DoseQty INTEGER, PD_Result TEXT, Vet TEXT)""")
            
        conn.execute("""CREATE TABLE IF NOT EXISTS CalvingLogs (
            Date TEXT, DamID TEXT, Result TEXT, Type TEXT, Calf1_Tag TEXT, Calf1_Sex TEXT, 
            Calf2_Tag TEXT, Calf2_Sex TEXT, Weight REAL, LactNo INTEGER)""")
            
        conn.commit()

init_livestock_db()

# --- 1. VIP BRANDING ---
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 15px; border-bottom: 8px solid #FF851B; margin-bottom: 20px; text-align: center;'>
        <h1 style='color: white; margin: 0; font-size: 40px;'>🐄 ZUNI <span style='color: #FF851B;'>LIVESTOCK PRO v2.0</span></h1>
        <p style='color: #FF851B; font-size: 16px; font-weight: bold;'>Smart Breeding | Advanced Treatment | Precision Calving</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
with db_connect() as conn:
    animal_data = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tag_list = animal_data['TagID'].tolist() if not animal_data.empty else []
    
    # Staff & Inventory
    try:
        staff_list = fetch_df(conn, "SELECT Name FROM EmployeeMaster WHERE Designation IN ('Doctor', 'Manager')")['Name'].tolist()
        items = fetch_df(conn, "SELECT ItemName, UOM FROM ItemMaster WHERE Category IN ('Medicine', 'Vaccine')")
        med_dict = dict(zip(items['ItemName'], items['UOM']))
        med_list = ["None"] + list(med_dict.keys())
        semen_inventory = fetch_df(conn, "SELECT ItemName FROM ItemMaster WHERE Category = 'Semen Straws'")['ItemName'].tolist()
    except:
        staff_list, med_list, med_dict, semen_inventory = [], ["None"], {}, []

# --- HELPER: AGE CALCULATION ---
def get_age_days(bday_str):
    try:
        bday = datetime.strptime(bday_str, '%Y-%m-%d').date()
        return (date.today() - bday).days
    except: return "N/A"

# --- 3. TABS ---
t_search, t_milk, t_treat, t_breed, t_calv, t_reg = st.tabs([
    "🔍 360° VIEW", "🥛 MILK", "🏥 TREATMENT", "🧬 BREEDING", "🍼 CALVING", "📝 REGISTRATION"
])

with t_search:
    if not animal_data.empty:
        # Age column dynamically add karna
        animal_data['Age(Days)'] = animal_data['BirthDate'].apply(get_age_days)
        st.dataframe(animal_data, use_container_width=True)
    else:
        st.info("No animals registered yet.")

with t_treat:
    st.subheader("🏥 Medicine Entry with UOM")
    with st.form("treat_form"):
        tr_tag = st.selectbox("Patient Tag", tag_list)
        
        # 4 Injection slots with Qty and Auto-UOM
        cols = st.columns(4)
        meds_input = []
        for i in range(4):
            with cols[i]:
                m = st.selectbox(f"Injection {i+1}", med_list, key=f"m{i}")
                q = st.number_input(f"Qty {i+1}", min_value=0.0, step=0.5, key=f"q{i}")
                u = med_dict.get(m, "-")
                st.caption(f"UOM: {u}")
                meds_input.append((m, q, u))
        
        rem = st.text_area("Symptoms / Remarks")
        if st.form_submit_button("💉 SAVE TREATMENT & CALCULATE COST"):
            with db_connect() as conn:
                conn.execute("""INSERT INTO TreatmentLogs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (str(date.today()), tr_tag, 
                     meds_input[0][0], meds_input[0][1], meds_input[0][2],
                     meds_input[1][0], meds_input[1][1], meds_input[1][2],
                     meds_input[2][0], meds_input[2][1], meds_input[2][2],
                     meds_input[3][0], meds_input[3][1], meds_input[3][2], rem))
                conn.commit()
                st.success("Treatment Logged!")

with t_breed:
    st.subheader("🧬 Heat & Insemination")
    with st.form("breed_form"):
        b_tag = st.selectbox("Cow Tag", tag_list)
        b_action = st.selectbox("Action", ["Insemination (AI)", "PD Check", "Natural Service", "Dry Off"])
        
        c1, c2 = st.columns(2)
        # Heat Status Requirement
        h_status = c1.selectbox("Heat Status / Protocol", ["Natural", "Ovsynch", "G6G", "Pre-Synch", "Silent Heat"])
        
        # PD Result update for Abortion
        pd_res = "N/A"
        if b_action == "PD Check":
            pd_res = c2.selectbox("PD Result", ["Pregnant (+)", "Empty (-)", "Abortion", "Re-Check"])
        
        sem = c1.selectbox("Semen/Bull", semen_inventory if b_action == "Insemination (AI)" else ["N/A"])
        vet = c2.selectbox("Vet/Staff", staff_list if staff_list else ["Manual"])
        
        if st.form_submit_button("✅ LOG BREEDING"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs VALUES (?,?,?,?,?,?,?,?)",
                             (str(date.today()), b_tag, b_action, h_status, sem, 1, pd_res, vet))
                conn.commit()
                st.rerun()

with t_calv:
    st.subheader("🍼 Calving & Abortion Details")
    with st.form("calv_form"):
        d_tag = st.selectbox("Dam (Mother) Tag", tag_list)
        res = st.radio("Result", ["Live Birth", "Stillborn", "Abortion"], horizontal=True)
        c_type = st.selectbox("Type", ["Single", "Twins"])
        
        # Auto-fetch Sire (Optional Logic)
        st.info("System will fetch Last AI Sire automatically for records.")
        
        col1, col2 = st.columns(2)
        c1_tag = col1.text_input("Calf 1 Tag")
        c1_sex = col1.selectbox("Calf 1 Sex", ["Heifer", "Bull", "Freemartin"])
        
        c2_tag, c2_sex = "N/A", "N/A"
        if c_type == "Twins":
            c2_tag = col2.text_input("Calf 2 Tag")
            c2_sex = col2.selectbox("Calf 2 Sex", ["Heifer", "Bull", "Freemartin"])
            
        w = st.number_input("Birth Weight (kg)", 20.0)
        
        if st.form_submit_button("🍼 REGISTER CALVING"):
            with db_connect() as conn:
                conn.execute("INSERT INTO CalvingLogs VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (str(date.today()), d_tag, res, c_type, c1_tag, c1_sex, c2_tag, c2_sex, w, 1))
                # Add Calf to AnimalMaster Automatically
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, BirthDate, Weight) VALUES (?,?,?,?)",
                             (c1_tag, "Young", str(date.today()), w))
                conn.commit()
                st.success("Calving Registered & Calf Added to Master!")

with t_reg:
    st.subheader("📝 New Animal Registration")
    with st.form("reg_form"):
        r_tag = st.text_input("Tag ID")
        r_breed = st.selectbox("Breed", ["Cholistani", "Sahiwal", "HF", "Jersey", "Cross"])
        r_bday = st.date_input("Date of Birth", date.today())
        
        c1, c2 = st.columns(2)
        sire1 = c1.text_input("Sire 1 (Father)")
        sire2 = c2.text_input("Sire 2 (Grand Father)")
        
        r_weight = st.number_input("Current Weight", 0.0)
        r_pen = st.selectbox("Assign Pen", ["PEN-A", "CALF-PEN", "DRY-PEN"])
        
        if st.form_submit_button("💾 REGISTER ANIMAL"):
            with db_connect() as conn:
                conn.execute("INSERT INTO AnimalMaster (TagID, Breed, Category, CurrentPen, Weight, BirthDate, Sire1, Sire2) VALUES (?,?,?,?,?,?,?,?)",
                             (r_tag, r_breed, "Adult", r_pen, r_weight, str(r_bday), sire1, sire2))
                conn.commit()
                st.success(f"Animal {r_tag} Registered Successfully!")
