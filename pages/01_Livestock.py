import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro", page_icon="🐄")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- MASTER DATA SYNC ---
with db_connect() as conn:
    # Basic Data
    animals_df = fetch_df(conn, "SELECT * FROM AnimalMaster")
    active_tags = animals_df[animals_df['Status'].isin(['Active', 'Sick', 'Lactating', 'Pregnant', 'Dry'])]['TagID'].tolist() if not animals_df.empty else []
    
    # Inventory items for Hospital & Breeding
    inventory = fetch_df(conn, "SELECT ItemName, Category, Cost, Quantity, UOM FROM ItemMaster")
    meds_info = inventory[inventory['Category'] == 'Medicine']
    semen_straws = inventory[inventory['Category'] == 'Semen Straws']
    
    # Pens/Sheds
    pens_df = fetch_df(conn, "SELECT * FROM PensMaster")
    pens_list = pens_df['PenName'].tolist() if not pens_df.empty else ["General"]

st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 ZUNI LIVESTOCK MASTER CONTROL</h1>", unsafe_allow_html=True)

tabs = st.tabs(["📊 COW CARD", "🥛 MILK", "🧬 BREEDING", "🩺 HOSPITAL", "🏠 PENS", "🐣 CALVING", "📉 REMOVAL"])

# ================= 1. COW CARD (ANIMAL P&L) =================
with tabs[0]:
    st.subheader("Individual Animal Performance")
    if active_tags:
        sel_tag = st.selectbox("Select Animal", active_tags, key="p_l_tag")
        m_data = fetch_df(None, f"SELECT SUM(Total) as total FROM MilkProduction WHERE TagID='{sel_tag}'")
        total_milk = float(m_data['total'].iloc[0]) if not m_data.empty and m_data['total'].iloc[0] is not None else 0.0
        
        t_data = fetch_df(None, f"SELECT SUM(TotalCost) as cost FROM TreatmentLogs WHERE TagID='{sel_tag}'")
        med_cost = float(t_data['cost'].iloc[0]) if not t_data.empty and t_data['cost'].iloc[0] is not None else 0.0

        rev = total_milk * 210 
        profit = rev - med_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Milk (Ltr)", f"{total_milk:,.1f}")
        c2.metric("Med Expense", f"Rs. {med_cost:,.0f}")
        c3.metric("Net Profit", f"Rs. {profit:,.0f}", delta=float(profit))
        st.dataframe(animals_df[animals_df['TagID'] == sel_tag], use_container_width=True)
    else:
        st.warning("No active animals found.")

# ================= 2. MILK PRODUCTION =================
with tabs[1]:
    st.subheader("Daily Milk Entry (3-Shift)")
    with st.form("milk_f", clear_on_submit=True):
        m1, m2 = st.columns(2)
        tag = m1.selectbox("Animal", active_tags)
        dt = m2.date_input("Date", date.today())
        s1, s2, s3 = st.columns(3)
        m_val = s1.number_input("Morning", 0.0)
        n_val = s2.number_input("Noon", 0.0)
        e_val = s3.number_input("Evening", 0.0)
        if st.form_submit_button("Save Milk Data"):
            tot = m_val + n_val + e_val
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction (Date, TagID, Morning, Noon, Evening, Total) VALUES (?,?,?,?,?,?)", 
                             (str(dt), tag, m_val, n_val, e_val, tot))
                conn.commit()
            st.success("Milk recorded!")
            st.rerun()

# ================= 3. BREEDING =================
with tabs[2]:
    st.subheader("🧬 Reproduction Management")
    with st.form("br_form"):
        b1, b2, b3 = st.columns(3)
        b_tag = b1.selectbox("Cow/Heifer", active_tags)
        b_mode = b2.radio("Mode", ["AI (Straw)", "Natural"])
        
        if b_mode == "AI (Straw)":
            straw = b3.selectbox("Semen Straw", semen_straws['ItemName'].tolist() if not semen_straws.empty else ["No Stock"])
        else:
            straw = b3.text_input("Bull ID")
            
        b_pd = b2.selectbox("PD Status", ["Pending", "Pregnant", "Open"])
        if st.form_submit_button("Save Breeding"):
            exp = str(date.today() + timedelta(days=280)) if b_pd == "Pregnant" else "N/A"
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Type, Semen, PD_Status, ExpectedCalving) VALUES (?,?,?,?,?,?)",
                             (str(date.today()), b_tag, b_mode, straw, b_pd, exp))
                if b_pd == "Pregnant": conn.execute("UPDATE AnimalMaster SET Status='Pregnant' WHERE TagID=?", (b_tag,))
                conn.commit()
            st.rerun()

# ================= 4. HOSPITAL (MULTI-MED) =================
with tabs[3]:
    st.subheader("🩺 Hospital & Treatment (Multi-Medicine)")
    
    # Common Diseases list
    diseases = ["Mastitis", "Fever", "FMD", "Lumpy Skin", "Indigestion", "Metritis", "Injury"]
    
    with st.form("hosp_multi"):
        h1, h2 = st.columns(2)
        h_tag = h1.selectbox("Select Sick Animal", active_tags)
        h_dis = h2.selectbox("Diagnosis (Disease)", diseases)
        
        st.write("---")
        st.write("💊 **Medicine Consumption (Auto Cost)**")
        
        # 4 Medicine Slots
        med_rows = []
        for i in range(4):
            cols = st.columns([3, 1, 1])
            m_name = cols[0].selectbox(f"Medicine {i+1}", ["None"] + meds_info['ItemName'].tolist(), key=f"m_{i}")
            
            # Fetch UOM for display
            uom = meds_info[meds_info['ItemName'] == m_name]['UOM'].iloc[0] if m_name != "None" else "Qty"
            m_qty = cols[1].number_input(f"{uom}", min_value=0.0, key=f"q_{i}")
            
            if m_name != "None" and m_qty > 0:
                cost_per_unit = meds_info[meds_info['ItemName'] == m_name]['Cost'].iloc[0]
                med_rows.append({'name': m_name, 'qty': m_qty, 'total': m_qty * cost_per_unit})
        
        h_vet = st.text_input("Vet Name")
        h_status = st.selectbox("Update Status", ["Sick", "Active"])

        if st.form_submit_button("Save Complete Treatment"):
            if med_rows:
                total_treatment_cost = sum(item['total'] for item in med_rows)
                all_meds_str = ", ".join([f"{i['name']}({i['qty']})" for i in med_rows])
                
                with db_connect() as conn:
                    # Log treatment
                    conn.execute("""INSERT INTO TreatmentLogs (Date, TagID, Issue, Medicine, TotalCost, Vet) 
                                 VALUES (?,?,?,?,?,?)""", 
                                 (str(date.today()), h_tag, h_dis, all_meds_str, total_treatment_cost, h_vet))
                    
                    # Deduct inventory for each med
                    for m in med_rows:
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (m['qty'], m['name']))
                    
                    conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (h_status, h_tag))
                    conn.commit()
                st.success(f"Treatment Recorded! Total Cost: Rs. {total_treatment_cost}")
                st.rerun()

# ================= 5. PENS (SHEDS) =================
with tabs[4]:
    st.subheader("🏠 Pens & Shed Management")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("### Create New Pen")
        with st.form("pen_f"):
            p_name = st.text_input("Pen Name (e.g. Shed 1, Hospital Pen)")
            p_cap = st.number_input("Capacity", 1)
            if st.form_submit_button("Create Pen"):
                with db_connect() as conn:
                    conn.execute("INSERT INTO PensMaster (PenName, Capacity) VALUES (?,?)", (p_name, p_cap))
                    conn.commit()
                st.rerun()
    
    with c2:
        st.write("### Animal Movement")
        with st.form("move_f"):
            m_tag = st.selectbox("Select Animal", active_tags)
            m_to = st.selectbox("Move to Pen", pens_list)
            if st.form_submit_button("Move Animal"):
                with db_connect() as conn:
                    conn.execute("UPDATE AnimalMaster SET Pen = ? WHERE TagID = ?", (m_to, m_tag))
                    conn.commit()
                st.success(f"{m_tag} moved to {m_to}")

# ================= 6. CALVING =================
with tabs[5]:
    st.subheader("🐣 Birth Registration")
    preg_cows = animals_df[animals_df['Status'] == 'Pregnant']['TagID'].tolist()
    with st.form("calv_f"):
        c_cow = st.selectbox("Mother Tag", preg_cows if preg_cows else ["None"])
        c_tag = st.text_input("New Calf Tag ID")
        gender = st.selectbox("Gender", ["Female", "Male"])
        if st.form_submit_button("Register Calf"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status='Lactating' WHERE TagID=?", (c_cow,))
                conn.execute("INSERT INTO AnimalMaster (TagID, Category, Status, PurchaseDate) VALUES (?,?,?,?)", 
                             (c_tag, "Calf", "Active", str(date.today())))
                conn.commit()
            st.rerun()

# ================= 7. REMOVAL =================
with tabs[6]:
    st.subheader("📉 Animal Removal")
    with st.form("rem_f"):
        r_tag = st.selectbox("Select Animal", active_tags)
        reason = st.radio("Reason", ["Sold", "Death"])
        rem_note = st.text_area("Note")
        if st.form_submit_button("Confirm Removal"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status=?, Remarks=? WHERE TagID=?", (reason, rem_note, r_tag))
                conn.commit()
            st.rerun()
