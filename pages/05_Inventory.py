import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. DATABASE SETUP (FIXED) ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Item Master Table (Stock)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    
    # Recipe Table (Multi-Ingredient Support)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        RecipeName TEXT, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER,
        PRIMARY KEY (RecipeName, ItemName))""")
    
    # DATABASE STABILIZER: Check if old schema exists and fix it
    try:
        conn.execute("SELECT RecipeName FROM FeedRecipes LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("DROP TABLE IF EXISTS FeedRecipes")
        conn.execute("""CREATE TABLE FeedRecipes (
            RecipeName TEXT, ItemName TEXT, 
            QtyPerAnimal REAL, TotalAnimals INTEGER,
            PRIMARY KEY (RecipeName, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.set_page_config(page_title="Zuni ERP Master", layout="wide")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; font-weight: bold;'>Complete Farm Management System</p>
    </div>
    """, unsafe_allow_html=True)

# --- FETCH DATA ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- TABS ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🌾 FEED RECIPES", "💊 MEDICINES", "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", "💰 ANIMAL P&L", "📊 LIVE STOCK", "➕ REGISTER NEW"
])

# --- TAB 1: FEED RECIPES (THE COMPLETE BUILDER) ---
with t1:
    st.subheader("🧪 Recipe Formulation")
    
    ex_recipes = recipes_df['RecipeName'].unique().tolist() if not recipes_df.empty else []
    col_a, col_b = st.columns(2)
    r_select = col_a.selectbox("Choose Group", ["+ ADD NEW GROUP"] + ex_recipes)
    
    if r_select == "+ ADD NEW GROUP":
        active_group = col_b.text_input("Group Name (e.g. HIGH-MILKING, CALVES)").upper()
    else:
        active_group = r_select

    with st.form("add_ing"):
        st.write(f"Editing: **{active_group}**")
        f_list = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
        c1, c2, c3 = st.columns(3)
        item = c1.selectbox("Ingredient", f_list if f_list else ["No Feed Found"])
        qty = c2.number_input("KG / Animal", min_value=0.01, step=0.5)
        count = c3.number_input("Total Animals", min_value=1, step=1)
        
        if st.form_submit_button("🚀 ADD TO RECIPE"):
            if active_group and item:
                conn.execute("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?)", 
                             (active_group, item, qty, count))
                conn.commit()
                st.success("Recipe Updated!")
                st.rerun()

    if not recipes_df.empty:
        for r_name in recipes_df['RecipeName'].unique():
            with st.expander(f"📋 {r_name} Formulation", expanded=True):
                sub = recipes_df[recipes_df['RecipeName'] == r_name]
                grand_total = 0
                for _, row in sub.iterrows():
                    total_kg = row['QtyPerAnimal'] * row['TotalAnimals']
                    grand_total += total_kg
                    d1, d2, d3, d4 = st.columns([2, 1, 1, 0.5])
                    d1.write(f"🌾 {row['ItemName']}")
                    d2.write(f"{row['QtyPerAnimal']} kg/head")
                    d3.write(f"Total: {total_kg:,.1f} KG")
                    if d4.button("❌", key=f"del_{r_name}_{row['ItemName']}"):
                        conn.execute("DELETE FROM FeedRecipes WHERE RecipeName=? AND ItemName=?", (r_name, row['ItemName']))
                        conn.commit()
                        st.rerun()
                st.info(f"**Grand Total Daily Load: {grand_total:,.1f} KG**")

# --- OTHER TABS (RESTORED) ---
with t2:
    st.subheader("💊 Medicines")
    st.dataframe(stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])], use_container_width=True)

with t3:
    st.subheader("🧬 Semen Straws")
    st.dataframe(stock_df[stock_df['Category'] == 'Semen Straws'], use_container_width=True)

with t4:
    st.subheader("⛽ General Assets")
    st.dataframe(stock_df[stock_df['Category'] == 'General Asset'], use_container_width=True)

with t5:
    st.subheader("💰 Daily Costing")
    if not recipes_df.empty:
        cost_list = []
        for _, r in recipes_df.iterrows():
            rate = stock_df[stock_df['ItemName']==r['ItemName']]['Cost'].values[0] if r['ItemName'] in stock_df['ItemName'].values else 0
            cost_list.append({"Group": r['RecipeName'], "Item": r['ItemName'], "Daily Cost": f"Rs. {rate * r['QtyPerAnimal'] * r['TotalAnimals']:,.0f}"})
        st.table(pd.DataFrame(cost_list))

with t6:
    st.subheader("📊 Total Stock")
    st.dataframe(stock_df, use_container_width=True)

with t7:
    st.subheader("➕ Register New")
    with st.form("reg_item"):
        n = st.text_input("Item Name").upper()
        c = st.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        u = st.selectbox("Unit", ["KG", "Bag", "Litre", "No"])
        r = st.number_input("Rate", min_value=0.0)
        s = st.number_input("Opening Stock", min_value=0.0)
        if st.form_submit_button("SAVE ITEM"):
            if n:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (n, c, u, s, r))
                conn.commit()
                st.rerun()
