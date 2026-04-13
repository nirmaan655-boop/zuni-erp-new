import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. DATABASE SETUP (ZUNI MASTER) ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Item Master Table
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, 
        Category TEXT, 
        UOM TEXT, 
        Quantity REAL DEFAULT 0, 
        Cost REAL DEFAULT 0)""")
    # Multi-Recipe Table (Composite Primary Key to allow multiple items per recipe)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        RecipeName TEXT, 
        ItemName TEXT, 
        QtyPerAnimal REAL, 
        TotalAnimals INTEGER,
        PRIMARY KEY (RecipeName, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- 2. APP INTERFACE & BRANDING ---
st.set_page_config(page_title="Zuni Pro ERP", layout="wide")

st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 25px; border-radius: 15px; border-bottom: 8px solid #FF851B; margin-bottom: 25px;'>
        <h1 style='color: white; margin: 0; font-size: 38px;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; font-size: 18px; font-weight: bold;'>Ultimate Farm & Nutrition Management System | FY 2026</p>
    </div>
    """, unsafe_allow_html=True)

# --- 3. DATA REFRESH ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- 4. MAIN NAVIGATION TABS (ALL TABS INCLUDED) ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🌾 FEED RECIPES", 
    "💊 MEDICINES", 
    "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", 
    "💰 ANIMAL P&L", 
    "📊 LIVE STOCK", 
    "➕ REGISTER NEW"
])

# --- TAB 1: FEED RECIPES (MULTI-GROUP) ---
with t1:
    st.subheader("🧪 Nutrition & Recipe Builder")
    
    # Recipe Type Selection
    existing_types = recipes_df['RecipeName'].unique().tolist() if not recipes_df.empty else []
    
    col_a, col_b = st.columns(2)
    r_choice = col_a.selectbox("Select/Create Recipe Group", ["+ CREATE NEW GROUP"] + existing_types)
    
    if r_choice == "+ CREATE NEW GROUP":
        group_name = col_b.text_input("Group Name (e.g., HIGH-MILKING, DRY-COWS, CALVES)").upper()
    else:
        group_name = r_choice

    # Add Ingredient Form
    with st.form("recipe_entry_form"):
        st.write(f"📝 Adding to Group: **{group_name}**")
        feed_items = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
        
        c1, c2, c3 = st.columns(3)
        f_item = c1.selectbox("Select Ingredient", feed_items if feed_items else ["WANDA (Register First)"])
        f_qty = c2.number_input("KG Per Animal (Daily)", min_value=0.01, step=0.1)
        f_count = c3.number_input("Total Animals in Group", min_value=1, value=1)
        
        if st.form_submit_button("🚀 SAVE INGREDIENT TO RECIPE"):
            if group_name and f_item:
                conn.execute("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?)", 
                             (group_name, f_item, f_qty, f_count))
                conn.commit()
                st.success(f"Updated {f_item} for {group_name}")
                st.rerun()

    # Display Active Recipes
    if not recipes_df.empty:
        st.write("---")
        for g in recipes_df['RecipeName'].unique():
            with st.expander(f"📋 {g} - Detailed Formulation", expanded=True):
                sub_df = recipes_df[recipes_df['RecipeName'] == g]
                total_group_load = 0
                
                for _, row in sub_df.iterrows():
                    load = row['QtyPerAnimal'] * row['TotalAnimals']
                    total_group_load += load
                    d1, d2, d3, d4 = st.columns([2, 1, 1, 0.5])
                    d1.write(f"🔹 **{row['ItemName']}**")
                    d2.write(f"{row['QtyPerAnimal']} kg/animal")
                    d3.write(f"Total: **{load:,.1f} KG**")
                    if d4.button("🗑️", key=f"del_{g}_{row['ItemName']}"):
                        conn.execute("DELETE FROM FeedRecipes WHERE RecipeName=? AND ItemName=?", (g, row['ItemName']))
                        conn.commit()
                        st.rerun()
                st.warning(f"Total Daily Requirement for {g}: **{total_group_load:,.1f} KG**")

# --- TAB 2: MEDICINES ---
with t2:
    st.subheader("💊 Medicine & Vaccine Inventory")
    med_df = stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])]
    st.table(med_df) if not med_df.empty else st.info("No medicines registered.")

# --- TAB 3: SEMEN BANK ---
with t3:
    st.subheader("🧬 Semen Straw Stock")
    semen_df = stock_df[stock_df['Category'] == 'Semen Straws']
    st.dataframe(semen_df, use_container_width=True)

# --- TAB 4: GENERAL STORE ---
with t4:
    st.subheader("⛽ General Assets & Fuel")
    gen_df = stock_df[stock_df['Category'] == 'General Asset']
    st.dataframe(gen_df, use_container_width=True)

# --- TAB 5: ANIMAL P&L ---
with t5:
    st.subheader("💰 Group-Wise Costing & P&L Analysis")
    if not recipes_df.empty:
        pl_data = []
        for _, r in recipes_df.iterrows():
            # Fetch cost from ItemMaster
            item_info = stock_df[stock_df['ItemName'] == r['ItemName']]
            unit_cost = item_info['Cost'].values[0] if not item_info.empty else 0
            
            daily_cost_per_animal = r['QtyPerAnimal'] * unit_cost
            group_daily_cost = daily_cost_per_animal * r['TotalAnimals']
            
            pl_data.append({
                "Group": r['RecipeName'],
                "Ingredient": r['ItemName'],
                "Cost/Animal (Rs)": f"{daily_cost_per_animal:,.2f}",
                "Group Daily Cost (Rs)": f"{group_daily_cost:,.0f}"
            })
        st.table(pd.DataFrame(pl_data))
    else:
        st.info("Recipes add karein taake costing show ho.")

# --- TAB 6: STOCK OVERVIEW ---
with t6:
    st.subheader("📊 Master Stock Status")
    st.dataframe(stock_df, use_container_width=True)
    
    # Quick Alert for Feed
    if not recipes_df.empty:
        total_needed = (recipes_df['QtyPerAnimal'] * recipes_df['TotalAnimals']).sum()
        st.error(f"🚨 Total Daily Feed Required: {total_needed:,.1f} KG")

# --- TAB 7: REGISTER NEW ITEM ---
with t7:
    st.subheader("➕ Register New Item in Master")
    with st.form("master_reg"):
        n_name = st.text_input("Item Name (Unique)").upper()
        n_cat = st.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        n_uom = st.selectbox("Unit (UOM)", ["KG", "Bag", "Litre", "No", "Straw"])
        n_cost = st.number_input("Unit Purchase Rate (Rs)", min_value=0.0)
        n_stock = st.number_input("Current Stock Quantity", min_value=0.0)
        
        if st.form_submit_button("✅ REGISTER ITEM"):
            if n_name:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", 
                             (n_name, n_cat, n_uom, n_stock, n_cost))
                conn.commit()
                st.success(f"{n_name} has been added to the system!")
                st.rerun()
