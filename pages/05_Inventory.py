import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- DATABASE SETUP (ZUNI MASTER) ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # 1. Item Master (Stock, Rates, Units)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # 2. Feed Recipes (Pen Wise)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        PenID TEXT PRIMARY KEY, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER)""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 25px; border-radius: 15px; border-bottom: 8px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; font-size: 35px;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; font-size: 16px; font-weight: bold;'>Complete Inventory & Farm Management | FY 2026</p>
    </div>
    """, unsafe_allow_html=True)

# --- FETCH DATA ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- MAIN TABS (NO TAB MISSING) ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🌾 FEED RECIPES", 
    "💊 MEDICINES", 
    "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", 
    "💰 ANIMAL P&L", 
    "📊 LIVE STOCK", 
    "➕ REGISTER NEW"
])

# --- 1. FEED RECIPES (PEN WISE) ---
with t1:
    st.subheader("📍 Pen-Wise Recipe Mapping")
    with st.form("pen_recipe_form"):
        col1, col2 = st.columns(2)
        f_pen = col1.text_input("Pen Name (e.g. SHED-A)").upper()
        feed_items = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
        f_item = col2.selectbox("Select Feed Item", feed_items if feed_items else ["WANDA"])
        
        col3, col4 = st.columns(2)
        f_qty = col3.number_input("KG Per Animal (Daily)", min_value=0.1, value=5.0)
        f_count = col4.number_input("Total Animals in Pen", min_value=1, value=10)
        
        if st.form_submit_button("🚀 SAVE PEN RECIPE"):
            if f_pen:
                conn.execute("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?)", (f_pen, f_item, f_qty, f_count))
                conn.commit()
                st.success(f"Recipe Saved for {f_pen}")
                st.rerun()

    if not recipes_df.empty:
        st.write("### Active Pen Recipes")
        for i, row in recipes_df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1,1,1,0.5])
                total_load = row['QtyPerAnimal'] * row['TotalAnimals']
                c1.write(f"🏠 **{row['PenID']}**")
                c2.write(f"🌾 {row['ItemName']}")
                c3.metric("Daily Load", f"{total_load} KG")
                if c4.button("❌", key=f"del_pen_{row['PenID']}"):
                    conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (row['PenID'],))
                    conn.commit()
                    st.rerun()

# --- 2. MEDICINES ---
with t2:
    st.subheader("💊 Medicine & Vaccine Store")
    med_df = stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])]
    st.dataframe(med_df, use_container_width=True)

# --- 3. SEMEN BANK ---
with t3:
    st.subheader("🧬 Semen Straw Inventory")
    semen_df = stock_df[stock_df['Category'] == 'Semen Straws']
    st.dataframe(semen_df, use_container_width=True)

# --- 4. GENERAL STORE ---
with t4:
    st.subheader("⛽ General Assets & Fuel")
    gen_df = stock_df[stock_df['Category'] == 'General Asset']
    st.dataframe(gen_df, use_container_width=True)

# --- 5. ANIMAL P&L ---
with t5:
    st.subheader("💰 Animal Wise Feed Cost & P&L")
    if not recipes_df.empty:
        pl_data = []
        for _, r in recipes_df.iterrows():
            rate_row = stock_df[stock_df['ItemName'] == r['ItemName']]
            rate = rate_row['Cost'].values[0] if not rate_row.empty else 125
            
            daily_cost = r['QtyPerAnimal'] * rate
            revenue = 10 * 210 # Assuming 10L milk @ 210
            profit = revenue - daily_cost
            
            pl_data.append({
                "Pen": r['PenID'],
                "Feed Item": r['ItemName'],
                "Cost/Animal": f"Rs. {daily_cost:,.0f}",
                "Profit/Animal": f"Rs. {profit:,.0f}"
            })
        st.table(pd.DataFrame(pl_data))
    else:
        st.info("Pehle Recipe save karein.")

# --- 6. LIVE STOCK OVERVIEW ---
with t6:
    st.subheader("📊 Full Inventory Status")
    st.dataframe(stock_df, use_container_width=True)
    if not recipes_df.empty:
        weekly = (recipes_df['QtyPerAnimal'] * recipes_df['TotalAnimals']).sum() * 7
        st.error(f"🚨 Total Feed Needed for Next 7 Days: {weekly:,.0f} KG")

# --- 7. REGISTER NEW ITEM ---
with t7:
    st.subheader("➕ Add New Item to Catalog")
    with st.form("master_reg_form"):
        r_name = st.text_input("Item Name").upper()
        r_cat = st.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        r_uom = st.selectbox("Unit", ["KG", "Bag", "Litre", "ml", "Straw", "Each"])
        r_qty = st.number_input("Current Stock", min_value=0.0)
        r_cost = st.number_input("Rate (Price per Unit)", min_value=0.0, value=100.0)
        
        if st.form_submit_button("✅ REGISTER ITEM"):
            if r_name:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", 
                             (r_name, r_cat, r_uom, r_qty, r_cost))
                conn.commit()
                st.success(f"{r_name} Added Successfully!")
                st.rerun()
