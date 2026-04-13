import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. DATABASE SETUP & LINKING ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Master Table (Stock, Rates, Units)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # Multi-Ingredient Recipe Table
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        RecipeName TEXT, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER,
        PRIMARY KEY (RecipeName, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- APP CONFIG & BRANDING ---
st.set_page_config(page_title="Zuni ERP Master", layout="wide")
st.markdown("""
    <div style='background-color: #001F3F; padding: 20px; border-radius: 10px; border-left: 10px solid #FF851B;'>
        <h1 style='color: white; margin: 0;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B;'>Inventory Linked with Precision Nutrition</p>
    </div>
    """, unsafe_allow_html=True)

# --- FETCH REFRESHED DATA ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- NAVIGATION TABS ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🌾 FEED RECIPES", "💊 MEDICINES", "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", "💰 COSTING & P&L", "📊 FULL STOCK", "➕ REGISTER NEW"
])

# --- TAB 1: FEED RECIPES (LINKED TO STOCK) ---
with t1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🛠️ Build Mix")
        ex_recipes = recipes_df['RecipeName'].unique().tolist() if not recipes_df.empty else []
        r_choice = st.selectbox("Select Recipe Group", ["+ NEW GROUP"] + ex_recipes)
        r_name = st.text_input("Group Name").upper() if r_choice == "+ NEW GROUP" else r_choice
        
        with st.form("add_item_to_mix"):
            feed_items = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
            f_item = st.selectbox("Ingredient", feed_items if feed_items else ["Wanda"])
            f_qty = st.number_input("KG / Animal", min_value=0.0, step=0.5)
            # Maintain animal count across group
            existing_count = int(recipes_df[recipes_df['RecipeName']==r_name]['TotalAnimals'].iloc[0]) if not recipes_df[recipes_df['RecipeName']==r_name].empty else 10
            f_count = st.number_input("Total Animals", min_value=1, value=existing_count)
            
            if st.form_submit_button("➕ Add to Mix"):
                if r_name and f_item:
                    conn.execute("UPDATE FeedRecipes SET TotalAnimals = ? WHERE RecipeName = ?", (f_count, r_name))
                    conn.execute("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?)", (r_name, f_item, f_qty, f_count))
                    conn.commit()
                    st.rerun()

    with col2:
        st.subheader("📋 Active Rations")
        if not recipes_df.empty:
            for group in recipes_df['RecipeName'].unique():
                with st.expander(f"📦 {group} (Animals: {recipes_df[recipes_df['RecipeName']==group]['TotalAnimals'].iloc[0]})", expanded=True):
                    sub = recipes_df[recipes_df['RecipeName'] == group]
                    total_kg = 0
                    
                    # Display table
                    for _, row in sub.iterrows():
                        load = row['QtyPerAnimal'] * row['TotalAnimals']
                        total_kg += load
                        c1, c2, c3, c4 = st.columns([2,1,1,0.5])
                        c1.write(f"🌾 **{row['ItemName']}**")
                        c2.write(f"{row['QtyPerAnimal']} kg/head")
                        c3.write(f"{load:,.0f} KG Total")
                        if c4.button("🗑️", key=f"del_{group}_{row['ItemName']}"):
                            conn.execute("DELETE FROM FeedRecipes WHERE RecipeName=? AND ItemName=?", (group, row['ItemName']))
                            conn.commit()
                            st.rerun()
                    
                    st.divider()
                    st.info(f"**Total Mix Weight: {total_kg:,.1f} KG**")
                    
                    # LINKED STOCK OUT BUTTON
                    if st.button(f"🚜 FEEDING DONE: {group}", key=f"btn_{group}"):
                        for _, row in sub.iterrows():
                            usage = row['QtyPerAnimal'] * row['TotalAnimals']
                            conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (usage, row['ItemName']))
                        conn.commit()
                        st.success(f"Stock deducted for {group}!")
                        st.balloons()
                        st.rerun()

# --- TAB 2, 3, 4: CATEGORY DATA VIEWS ---
with t2:
    st.subheader("💊 Medicines & Vaccines")
    st.dataframe(stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])], use_container_width=True)

with t3:
    st.subheader("🧬 Semen Straws")
    st.dataframe(stock_df[stock_df['Category'] == 'Semen Straws'], use_container_width=True)

with t4:
    st.subheader("⛽ General Assets")
    st.dataframe(stock_df[stock_df['Category'] == 'General Asset'], use_container_width=True)

# --- TAB 5: COSTING & P&L ---
with t5:
    st.subheader("💰 Daily Feeding Cost Analysis")
    if not recipes_df.empty:
        costs = []
        for _, r in recipes_df.iterrows():
            rate = stock_df[stock_df['ItemName']==r['ItemName']]['Cost'].iloc[0] if r['ItemName'] in stock_df['ItemName'].values else 0
            daily_c = rate * r['QtyPerAnimal'] * r['TotalAnimals']
            costs.append({"Group": r['RecipeName'], "Item": r['ItemName'], "Daily Cost (Rs)": f"{daily_c:,.0f}"})
        st.table(pd.DataFrame(costs))

# --- TAB 6: FULL INVENTORY ---
with t6:
    st.subheader("📊 Current Stock (Master)")
    st.dataframe(stock_df, use_container_width=True)

# --- TAB 7: REGISTER NEW ---
with t7:
    st.subheader("➕ Register New Item")
    with st.form("reg_new"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Name").upper()
        c = c2.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        u = c3.selectbox("Unit", ["KG", "Bag", "Litre", "No"])
        p = c1.number_input("Purchase Rate", min_value=0.0)
        s = c2.number_input("Initial Stock", min_value=0.0)
        if st.form_submit_button("Register"):
            if n:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (n, c, u, s, p))
                conn.commit()
                st.rerun()
