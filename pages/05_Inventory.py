import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Master Table
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # Professional Recipe Table
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        RecipeName TEXT, ItemName TEXT, Qty REAL, 
        Mandatory TEXT, TotalAnimals INTEGER,
        PRIMARY KEY (RecipeName, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- 2. LAYOUT & BRANDING ---
st.set_page_config(page_title="Zuni Pro ERP", layout="wide")

st.markdown("""
    <div style='background-color: #001F3F; padding: 15px; border-radius: 10px; border-bottom: 5px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; margin: 0;'>Enterprise Resource Planning | Professional Feed & Inventory</p>
    </div>
    """, unsafe_allow_html=True)

# --- 3. DATA REFRESH ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- 4. NAVIGATION TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs([
    "🥗 RECIPE MANAGEMENT", 
    "📊 LIVE STOCK (INVENTORY)", 
    "💊 MEDICINES & SEMEN", 
    "💰 COSTING / P&L", 
    "➕ REGISTER NEW ITEM",
    "⛽ GENERAL STORE"
])

# --- TAB 1: PROFESSIONAL RECIPE (IMAGE STYLE) ---
with t1:
    col_list, col_main = st.columns([1, 3])
    
    with col_list:
        st.write("### 📂 Recipes")
        search_r = st.text_input("🔍 Search...", "").upper()
        unique_r = recipes_df['RecipeName'].unique().tolist() if not recipes_df.empty else []
        
        # Sidebar-style list
        selected_r = st.session_state.get('sel_recipe', None)
        for r in unique_r:
            if search_r in r:
                if st.button(f"📄 {r}", key=f"btn_{r}", use_container_width=True):
                    st.session_state.sel_recipe = r
                    st.rerun()
        
        if st.button("➕ CREATE NEW", type="primary", use_container_width=True):
            st.session_state.sel_recipe = "NEW"
            st.rerun()

    with col_main:
        curr_r = st.session_state.get('sel_recipe', "NEW")
        
        if curr_r == "NEW":
            st.subheader("🆕 Create New Formulation")
            new_name = st.text_input("Enter Recipe Name (e.g. ELITE 2)").upper()
            if st.button("Initialize Recipe"):
                st.session_state.sel_recipe = new_name
                st.rerun()
        else:
            st.subheader(f"📍 Recipe: {curr_r}")
            
            # --- FORM TO ADD INGREDIENTS ---
            with st.expander("➕ Add Ingredient to Table"):
                with st.form("ing_form"):
                    f_items = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
                    c1, c2, c3 = st.columns([2,1,1])
                    item = c1.selectbox("Item Description", f_items if f_items else ["Register Feed Items First"])
                    qty = c2.number_input("Qty (per head)", min_value=0.0, step=0.1)
                    mand = c3.selectbox("Issuance Mandatory", ["Yes", "No"])
                    
                    curr_animals = int(recipes_df[recipes_df['RecipeName']==curr_r]['TotalAnimals'].iloc[0]) if not recipes_df[recipes_df['RecipeName']==curr_r].empty else 100
                    total_an = st.number_input("Total Animals for this Group", value=curr_animals)
                    
                    if st.form_submit_button("Add to Table"):
                        conn.execute("UPDATE FeedRecipes SET TotalAnimals = ? WHERE RecipeName = ?", (total_an, curr_r))
                        conn.execute("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?,?)", (curr_r, item, qty, mand, total_an))
                        conn.commit()
                        st.rerun()

            # --- PROFESSIONAL TABLE (AS PER IMAGE) ---
            r_data = recipes_df[recipes_df['RecipeName'] == curr_r]
            if not r_data.empty:
                st.markdown("""
                    <style>
                        .tbl-hdr { background-color: #f0f2f6; font-weight: bold; padding: 10px; border-bottom: 2px solid #ddd; }
                    </style>
                """, unsafe_allow_html=True)
                
                # Table Header
                h1, h2, h3, h4, h5 = st.columns([0.5, 3, 1, 1, 0.5])
                h1.markdown("**Sr#**")
                h2.markdown("**Item Description**")
                h3.markdown("**Qty**")
                h4.markdown("**Issuance Mandatory**")
                h5.markdown("**-**")
                
                total_head_qty = 0
                for i, row in enumerate(r_data.itertuples(), 1):
                    total_head_qty += row.Qty
                    d1, d2, d3, d4, d5 = st.columns([0.5, 3, 1, 1, 0.5])
                    d1.write(i)
                    d2.write(row.ItemName)
                    d3.write(row.Qty)
                    d4.write(row.Mandatory)
                    if d5.button("❌", key=f"del_{row.ItemName}"):
                        conn.execute("DELETE FROM FeedRecipes WHERE RecipeName=? AND ItemName=?", (curr_r, row.ItemName))
                        conn.commit()
                        st.rerun()
                
                st.divider()
                st.info(f"**Group Summary:** Total Animals: {r_data['TotalAnimals'].iloc[0]} | Daily Ration per Head: {total_head_qty} KG")
                
                # POST BUTTON
                if st.button(f"🚀 POST & ISSUE FEED ({curr_r})", type="primary", use_container_width=True):
                    for row in r_data.itertuples():
                        usage = row.Qty * row.TotalAnimals
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (usage, row.ItemName))
                    conn.commit()
                    st.success(f"Stock Deducted for {curr_r} successfully!")
                    st.balloons()

# --- TAB 2: LIVE INVENTORY ---
with t2:
    st.subheader("📊 Current Warehouse Stock")
    st.dataframe(stock_df, use_container_width=True)

# --- TAB 3: MEDICINES & SEMEN ---
with t3:
    col_m, col_s = st.columns(2)
    with col_m:
        st.subheader("💊 Medicines")
        st.table(stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])])
    with col_s:
        st.subheader("🧬 Semen Bank")
        st.table(stock_df[stock_df['Category'] == 'Semen Straws'])

# --- TAB 4: COSTING / P&L ---
with t5:
    st.subheader("➕ Register New Stock Item")
    with st.form("master_reg"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Item Name").upper()
        c = c2.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        u = c3.selectbox("Unit", ["KG", "Bag", "Litre", "No"])
        p = c1.number_input("Purchase Price (Rs)", min_value=0.0)
        s = c2.number_input("Opening Stock Quantity", min_value=0.0)
        if st.form_submit_button("SAVE TO MASTER"):
            if n:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (n, c, u, s, p))
                conn.commit()
                st.success(f"{n} registered!")
                st.rerun()

# --- TAB 6: GENERAL STORE ---
with t6:
    st.subheader("⛽ Fuel & General Assets")
    st.dataframe(stock_df[stock_df['Category'] == 'General Asset'], use_container_width=True)
