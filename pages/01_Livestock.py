import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
from datetime import date

st.set_page_config(layout="wide", page_title="Zuni Dairy Pro")

# --- DATA FETCHING ---
with db_connect() as conn:
    animals_df = fetch_df(conn, "SELECT * FROM AnimalMaster")
    tags = animals_df[animals_df['Status'] != 'Sold']['TagID'].tolist()
    bulls = animals_df[animals_df['Category'] == 'Bull']['TagID'].tolist()
    
    # Inventory items
    inventory = fetch_df(conn, "SELECT ItemName, Category, UOM, Cost FROM ItemMaster")
    medicines = inventory[inventory['Category'] == 'Medicine']
    semen_straws = inventory[inventory['Category'] == 'Semen Straws']['ItemName'].tolist()
    
    # Feed Rates for P&L
    feed_items = inventory[inventory['Category'] == 'Feed']

st.markdown("<h1 style='text-align: center; color: #FF851B;'>🐄 LIVESTOCK PRO CONTROL (SYNCED)</h1>", unsafe_allow_html=True)

tabs = st.tabs(["📊 COW CARD (P&L)", "🥛 MILK PRODUCTION", "🧬 BREEDING", "🩺 HOSPITAL (4-MED)", "🚚 MOVEMENT", "📉 REMOVAL"])

# ================= 1. COW CARD (ANIMAL WISE P/L) =================
with tabs[0]:
    st.subheader("Individual Animal Performance & Profitability")
    if tags:
        sel_tag = st.selectbox("Select Animal", tags, key="p_l_tag")
        
        # Calculations
        milk_data = fetch_df(None, f"SELECT SUM(Total) as total FROM MilkProduction WHERE TagID='{sel_tag}'")
        treat_data = fetch_df(None, f"SELECT SUM(TotalCost) as cost FROM TreatmentLogs WHERE TagID='{sel_tag}'")
        
        total_milk = milk_data['total'].iloc[0] if milk_data['total'].iloc[0] else 0
        total_med_cost = treat_data['cost'].iloc[0] if treat_data['cost'].iloc[0] else 0
        
        # Revenue @ 210 per liter
        revenue = total_milk * 210 
        profit = revenue - total_med_cost
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Milk (Ltr)", f"{total_milk:,.1f}")
        c2.metric("Milk Revenue", f"Rs. {revenue:,.0f}")
        c3.metric("Medicine Expense", f"Rs. {total_med_cost:,.0f}")
        c4.metric("Net Profit/Loss", f"Rs. {profit:,.0f}", delta=float(profit))
        
        st.divider()
        st.write("### Animal Profile")
        st.dataframe(animals_df[animals_df['TagID'] == sel_tag], use_container_width=True)

# ================= 2. MILK PRODUCTION (3-TIME) =================
with tabs[1]:
    st.subheader("🥛 Daily Yield (Morning/Noon/Evening)")
    with st.form("milk_form"):
        m1, m2, m3 = st.columns(3)
        m_tag = m1.selectbox("Animal", tags, key="m_tag")
        m_date = m2.date_input("Date", date.today())
        
        c1, c2, c3 = st.columns(3)
        m_m = c1.number_input("Morning", 0.0)
        m_n = c2.number_input("Noon", 0.0)
        m_e = c3.number_input("Evening", 0.0)
        
        if st.form_submit_button("Save Milk"):
            total = m_m + m_n + m_e
            with db_connect() as conn:
                conn.execute("INSERT INTO MilkProduction VALUES (?,?,?,?,?,?)", (str(m_date), m_tag, m_m, m_n, m_e, total))
                conn.commit()
            st.rerun()

# ================= 3. BREEDING (AUTO INVENTORY LINK) =================
with tabs[2]:
    st.subheader("🧬 Breeding Bank Integration")
    with st.form("breeding_pro"):
        col1, col2 = st.columns(2)
        b_tag = col1.selectbox("Select Cow", tags, key="b_cow")
        b_mode = col2.radio("Breeding Mode", ["AI (Semen Straw)", "Natural (Bull)"], horizontal=True)
        
        if b_mode == "AI (Semen Straw)":
            b_semen = col1.selectbox("Select Semen Straw (From Inventory)", semen_straws if semen_straws else ["No Stock"])
        else:
            b_semen = col1.selectbox("Select Bull (From Herd)", bulls if bulls else ["No Bull in Herd"])
            
        b_vet = col2.text_input("Vet Name")
        if st.form_submit_button("Record Breeding"):
            with db_connect() as conn:
                conn.execute("INSERT INTO BreedingLogs (Date, TagID, Type, Semen, Vet, PD_Status) VALUES (?,?,?,?,?,?)",
                             (str(date.today()), b_tag, b_mode, b_semen, b_vet, "Pending"))
                if b_mode == "AI (Semen Straw)":
                    conn.execute("UPDATE ItemMaster SET Quantity = Quantity - 1 WHERE ItemName=?", (b_semen,))
                conn.commit()
            st.success("Breeding recorded and Straw deducted!")

# ================= 4. HOSPITAL (4 MEDICINE LOGIC) =================
with tabs[3]:
    st.subheader("🩺 Advanced Hospitalization (Multi-Medicine)")
    with st.form("hospital_pro"):
        h1, h2 = st.columns(2)
        h_tag = h1.selectbox("Sick Animal", tags, key="h_tag")
        h_dis = h2.text_input("Disease Name")
        
        st.write("### 💊 Treatment (Select up to 4 Medicines)")
        med_list = medicines['ItemName'].tolist() if not medicines.empty else ["No Med"]
        
        total_treatment_cost = 0
        med_entries = []
        
        # 4 Medicine Rows
        for i in range(4):
            r1, r2, r3 = st.columns([3,2,2])
            m_name = r1.selectbox(f"Medicine {i+1}", ["None"] + med_list, key=f"med_{i}")
            m_qty = r2.number_input(f"Qty {i+1}", 0.0, key=f"qty_{i}")
            
            if m_name != "None":
                med_info = medicines[medicines['ItemName'] == m_name].iloc[0]
                cost = m_qty * med_info['Cost']
                total_treatment_cost += cost
                r3.write(f"Unit: {med_info['UOM']} | Cost: {cost:,.0f}")
                med_entries.append((m_name, m_qty))

        st.markdown(f"### Total Treatment Cost: **Rs. {total_treatment_cost:,.0f}**")
        
        if st.form_submit_button("Post Treatment & Deduct Inventory"):
            with db_connect() as conn:
                conn.execute("INSERT INTO TreatmentLogs (Date, TagID, Disease, TotalCost, Status) VALUES (?,?,?,?,?)",
                             (str(date.today()), h_tag, h_dis, total_treatment_cost, "Under Treatment"))
                for m, q in med_entries:
                    conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName=?", (q, m))
                conn.commit()
            st.success("Medicine used and Stock updated!")

# ================= 5. MOVEMENT & 6. REMOVAL (Summary) =================
with tabs[4]:
    st.write("### Movement History")
    st.dataframe(fetch_df(None, "SELECT * FROM MovementLogs"), use_container_width=True)

with tabs[5]:
    st.write("### Death / Sold Archives")
    st.dataframe(animals_df[animals_df['Status'].isin(['Death', 'Sold', 'Culled'])], use_container_width=True)
