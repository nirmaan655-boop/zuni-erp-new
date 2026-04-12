import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date, timedelta
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Zuni Livestock Pro")

# --- DATA FETCHING (MASTER SYNC) ---
with db_connect() as conn:
    animals_df = fetch_df(None, "SELECT * FROM AnimalMaster")
    active_tags = animals_df[animals_df['Status'].isin(['Active', 'Sick', 'Lactating', 'Pregnant', 'Dry'])]['TagID'].tolist() if not animals_df.empty else []
    
    # Inventory items for link
    inventory = fetch_df(None, "SELECT ItemName, Category, Cost FROM ItemMaster")
    semen_straws = inventory[inventory['Category'] == 'Semen Straws']['ItemName'].tolist() if not inventory.empty else []
    bulls = animals_df[animals_df['Category'] == 'Bull']['TagID'].tolist() if not animals_df.empty else []

st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 LIVESTOCK MASTER CONTROL</h1>", unsafe_allow_html=True)

# Sab tabs ko define kar diya
tabs = st.tabs(["📊 COW CARD", "🥛 MILK (3-TIME)", "🧬 BREEDING", "🐣 CALVING", "🩺 HOSPITAL", "🚚 MOVEMENT", "📉 REMOVAL"])

# ================= 1. COW CARD (ANIMAL P&L) =================
with tabs[0]:
    st.subheader("Performance & Profitability")
    if active_tags:
        sel_tag = st.selectbox("Select Animal", active_tags, key="p_l_tag")
        
        # Milk & Treatment Cost Calculation
        m_data = fetch_df(None, f"SELECT SUM(Total) as total FROM MilkProduction WHERE TagID='{sel_tag}'")
        total_milk = float(m_data['total'].iloc[0]) if not m_data.empty and m_data['total'].iloc[0] is not None else 0.0
        
        try:
            t_data = fetch_df(None, f"SELECT SUM(TotalCost) as cost FROM TreatmentLogs WHERE TagID='{sel_tag}'")
            med_cost = float(t_data['cost'].iloc[0]) if not t_data.empty and t_data['cost'].iloc[0] is not None else 0.0
        except: med_cost = 0.0

        rev = total_milk * 210 # Revenue @ 210/Ltr
        profit = rev - med_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Milk (Ltr)", f"{total_milk:,.1f}")
        c2.metric("Med Expense", f"Rs. {med_cost:,.0f}")
        c3.metric("Net Profit/Loss", f"Rs. {profit:,.0f}", delta=float(profit))
        
        st.dataframe(animals_df[animals_df['TagID'] == sel_tag], use_container_width=True)
    else:
        st.warning("Inventory khali hai. Pehle Procurement se janwar add karein.")

# ================= 2. MILK PRODUCTION (3-SHIFT) =================
with tabs[1]:
    st.subheader("Daily Milk Entry")
    with st.form("milk_f", clear_on_submit=True):
        m1, m2 = st.columns(2)
        tag = m1.selectbox("Animal", active_tags, key="m_tag")
        dt = m2.date_input("Date", date.today())
        s1, s2, s3 = st.columns(3)
        m_val = s1.number_input("Morning", 0.0)
        n_val = s2.number_input("Noon", 0.0)
        e_val = s3.number_input("Evening", 0.0)
        if st.form_submit_button("Save Milk"):
            tot = m_val + n_val + e_val
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction VALUES (?,?,?,?,?,?)", (str(dt), tag, m_val, n_val, e_val, tot))
                conn.commit()
            st.rerun()
    
    st.write("### 📜 Milk History")
    m_hist = fetch_df(None, "SELECT rowid as ID, * FROM MilkProduction ORDER BY Date DESC LIMIT 10")
    st.dataframe(m_hist, use_container_width=True)

# ================= 3. BREEDING & PD (PRO SYNC) =================
with tabs[2]:  # Index 2 Breeding ke liye hai
    st.subheader("🧬 Reproduction & Breeding Bank")
    
    # 1. FETCH DATA (Semen from Inventory & Bulls from Herd)
    with db_connect() as conn:
        # Inventory se straws aur unki quantity uthana
        semen_df = fetch_df(conn, "SELECT ItemName, Quantity FROM ItemMaster WHERE Category = 'Semen Straws' AND Quantity > 0")
        semen_options = [f"{r['ItemName']} (Qty: {int(r['Quantity'])})" for _, r in semen_df.iterrows()] if not semen_df.empty else []
        
        # Herd se Bulls ke TagID uthana
        bull_list = fetch_df(conn, "SELECT TagID FROM AnimalMaster WHERE Category = 'Bull' AND Status != 'Sold'")['TagID'].tolist()
        
        # Cows list (tags variable ko dobara define kar dete hain safety ke liye)
        cows_df = fetch_df(conn, "SELECT TagID FROM AnimalMaster WHERE Category IN ('Cow', 'Heifer') AND Status NOT IN ('Sold', 'Death')")
        tags_list = cows_df['TagID'].tolist() if not cows_df.empty else []

    # Form Shuru
    with st.form("br_form_pro"):
        b1, b2, b3 = st.columns(3)
        
        # Animal Selection
        b_tag = b1.selectbox("Select Cow/Heifer", tags_list, key="br_cow_select")
        
        # Mode Selection
        b_mode = b2.radio("Breeding Mode", ["AI (Straw)", "Natural (Bull)"], horizontal=True)
        
        # Dynamic Selection for Semen/Bull
        if b_mode == "AI (Straw)":
            actual_semen_name = b3.selectbox("Select Semen Straw", semen_options if semen_options else ["No Stock"])
        else:
            actual_semen_name = b3.selectbox("Select Bull Tag", bull_list if bull_list else ["No Bull Found"])
            
        b_vet = b1.text_input("Vet Name")
        b_pd = b2.selectbox("PD Status", ["Pending", "Pregnant", "Open"])
        
        # SUBMIT BUTTON (Error Fix)
        submit_breeding = st.form_submit_button("✅ Save Breeding Record")
        
        if submit_breeding:
            if b_tag and "No" not in str(actual_semen_name):
                # Cleaning name to get only ItemName from "ItemName (Qty: 10)"
                clean_semen_name = str(actual_semen_name).split(" (Qty:")[0]
                
                exp = str(date.today() + timedelta(days=280)) if b_pd == "Pregnant" else "N/A"
                
                with db_connect() as conn:
                    # 1. Log entry
                    conn.execute("""INSERT INTO BreedingLogs (Date, TagID, Type, Semen, Vet, PD_Status, ExpectedCalving) 
                                    VALUES (?,?,?,?,?,?,?)""", 
                                 (str(date.today()), b_tag, b_mode, clean_semen_name, b_vet, b_pd, exp))
                    
                    # 2. Agar AI hai toh Inventory se 1 kam karna
                    if b_mode == "AI (Straw)":
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - 1 WHERE ItemName = ?", (clean_semen_name,))
                    
                    # 3. Status update
                    if b_pd == "Pregnant":
                        conn.execute("UPDATE AnimalMaster SET Status='Pregnant' WHERE TagID=?", (b_tag,))
                    
                    conn.commit()
                st.success(f"Record Saved for {b_tag}!")
                st.rerun()
            else:
                st.error("Please select valid Animal and Semen/Bull")

    st.write("---")
    st.write("### 📜 Breeding History")
    st.dataframe(fetch_df(None, "SELECT * FROM BreedingLogs ORDER BY Date DESC"), use_container_width=True)


# ================= 4. CALVING =================
with tabs[3]:
    st.subheader("New Birth Registration")
    preg_cows = animals_df[animals_df['Status'] == 'Pregnant']['TagID'].tolist()
    if preg_cows:
        with st.form("calv_f"):
            c_cow = st.selectbox("Mother Tag", preg_cows)
            gender = st.selectbox("Calf Gender", ["Female", "Male"])
            weight = st.number_input("Birth Weight", 25.0)
            if st.form_submit_button("Register Calving"):
                with db_connect() as conn:
                    conn.execute("UPDATE AnimalMaster SET Status='Lactating' WHERE TagID=?", (c_cow,))
                    conn.execute("INSERT INTO AnimalMaster (TagID, Category, Status, Weight, PurchaseDate) VALUES (?,?,?,?,?)", 
                                 (f"C-{c_cow}", "Calf", "Active", weight, str(date.today())))
                    conn.commit()
                st.balloons()
                st.rerun()
    else: st.info("No pregnant cows found.")

# ================= 5. HOSPITAL (MULTI-MED) =================
with tabs[4]:
    st.subheader("Hospital & Sick Bay")
    with st.form("hosp_f"):
        h_tag = st.selectbox("Sick Animal", active_tags, key="h_tag")
        dis = st.text_input("Disease")
        cost = st.number_input("Total Med Cost", 0.0)
        if st.form_submit_button("Post Treatment"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Disease, TotalCost, Status) VALUES (?,?,?,?,?)",
                             (str(date.today()), h_tag, dis, cost, "Under Treatment"))
                conn.commit()
            st.rerun()
    st.dataframe(fetch_df(None, "SELECT * FROM TreatmentLogs"), use_container_width=True)

# ================= 6. MOVEMENT =================
with tabs[5]:
    st.subheader("Pen Movement History")
    with st.form("mov_f"):
        mv_tag = st.selectbox("Animal", active_tags)
        to_pen = st.text_input("New Pen/Shed")
        if st.form_submit_button("Log Move"):
            with db_connect() as conn:
                conn.execute("INSERT INTO MovementLogs (Date, TagID, ToPen) VALUES (?,?,?)", (str(date.today()), mv_tag, to_pen))
                conn.commit()
            st.rerun()
    st.dataframe(fetch_df(None, "SELECT * FROM MovementLogs"), use_container_width=True)

# ================= 7. REMOVAL (DEATH/SOLD) =================
with tabs[6]:
    st.subheader("Removal Record")
    with st.form("rem_f"):
        r_tag = st.selectbox("Animal", active_tags, key="rem_tag")
        reason = st.selectbox("Reason", ["Death", "Sold", "Culling"])
        if st.form_submit_button("Confirm Removal"):
            with db_connect() as conn:
                conn.execute("UPDATE AnimalMaster SET Status=? WHERE TagID=?", (reason, r_tag))
                conn.commit()
            st.rerun()
    st.write("### 📜 Archives (Non-Active)")
    st.dataframe(animals_df[animals_df['Status'].isin(['Death', 'Sold', 'Culling'])], use_container_width=True)
