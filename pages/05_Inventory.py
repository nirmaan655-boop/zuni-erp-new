import streamlit as st
import pandas as pd
import sqlite3
import os

# --- DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Item Master (Stock, Rates, Units)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # Feed Recipes (Pen Wise)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        PenID TEXT, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER,
        PRIMARY KEY (PenID, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.set_page_config(page_title="Zuni Pro ERP", layout="wide")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 25px; border-radius: 15px; border-bottom: 8px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; font-size: 35px;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; font-size: 16px; font-weight: bold;'>Complete Farm Management System | FY 2026</p>
    </div>
    """, unsafe_allow_html=True)

# Fetch Data
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# Helper for History & Editing
def render_history(category):
    st.subheader(f"📜 {category} Inventory & Records")
    items = stock_df[stock_df['Category'] == category]
    if not items.empty:
        for item in items.itertuples():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                c1.write(f"**{item.ItemName}**")
                c2.write(f"📦 Stock: {item.Quantity} {item.UOM} | 💰 Rate: {item.Cost}")
                if c3.button("✏️ Edit", key=f"edit_{category}_{item.ItemName}"):
                    st.session_state['edit_item'] = {'ItemName': item.ItemName, 'Category': item.Category, 'UOM': item.UOM, 'Quantity': item.Quantity, 'Cost': item.Cost}
                    st.info(f"Editing {item.ItemName}. Please go to 'ADD/EDIT MASTER' tab.")
                if c4.button("🗑️", key=f"del_{category}_{item.ItemName}"):
                    conn.execute("DELETE FROM ItemMaster WHERE ItemName=?", (item.ItemName,))
                    conn.commit()
                    st.rerun()
    else:
        st.info(f"No items found in {category}")

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs([
    "🌾 DAILY FEEDING", 
    "📊 STOCK REPORT", 
    "💊 MEDICINES", 
    "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", 
    "➕ ADD/EDIT MASTER"
])

# --- 1. DAILY FEEDING (TMR) ---
with t1:
    st.subheader("📋 Pen-Wise Recipe Form")
    with st.container(border=True):
        with st.form("tmr_form"):
            col1, col2 = st.columns(2)
            f_pen = col1.text_input("PEN / SHED NAME (e.g. SHED-A)").upper()
            f_count = col2.number_input("TOTAL ANIMALS", min_value=1, value=1)
            
            st.write("---")
            st.write("**Set Ingredient Quantity (KG Per Animal):**")
            feed_items = stock_df[stock_df['Category']=='Feed']
            
            recipe_list = []
            if not feed_items.empty:
                cols = st.columns(4)
                for idx, row in enumerate(feed_items.itertuples()):
                    with cols[idx % 4]:
                        qty = st.number_input(f"{row.ItemName}", min_value=0.0, format="%.2f")
                        if qty > 0: recipe_list.append((f_pen, row.ItemName, qty, f_count))
            
            if st.form_submit_button("🚀 SAVE FULL RECIPE"):
                if f_pen and recipe_list:
                    conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (f_pen,))
                    conn.executemany("INSERT INTO FeedRecipes VALUES (?,?,?,?)", recipe_list)
                    conn.commit()
                    st.success(f"Recipe saved for {f_pen}")
                    st.rerun()

    if not recipes_df.empty:
        st.divider()
        st.subheader("🚜 Daily Loading Sheet")
        for pen in recipes_df['PenID'].unique():
            with st.container(border=True):
                p_data = recipes_df[recipes_df['PenID'] == pen].copy()
                p_data['Total Load (KG)'] = p_data['QtyPerAnimal'] * p_data['TotalAnimals']
                
                c_a, c_b = st.columns([2, 1])
                c_a.markdown(f"#### 📍 {pen} (Animals: {p_data['TotalAnimals'].iloc})")
                c_b.metric("Mixer Load", f"{p_data['Total Load (KG)'].sum():,.1f} KG")
                
                st.table(p_data[['ItemName', 'QtyPerAnimal', 'Total Load (KG)']])
                
                if st.button(f"✅ Confirm Feeding & Deduct Stock ({pen})", key=f"f_{pen}"):
                    for _, r in p_data.iterrows():
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (r['Total Load (KG)'], r['ItemName']))
                    conn.commit()
                    st.success(f"Stock deducted for {pen}")
                    st.rerun()

# --- 2. STOCK REPORT ---
with t2:
    st.subheader("📊 Live Inventory Overview")
    st.dataframe(stock_df, use_container_width=True, hide_index=True)

# --- 3, 4, 5. CATEGORY TABS ---
with t3: render_history("Medicine")
with t4: render_history("Semen Straws")
with t5: render_history("General Asset")

# --- 6. ADD/EDIT MASTER ---
with t6:
    st.subheader("➕ Inventory Master Entry")
    edit_data = st.session_state.get('edit_item', {})
    
    with st.form("master_entry", clear_on_submit=True):
        name = st.text_input("Item Name", value=edit_data.get('ItemName', '')).upper()
        cat = st.selectbox("Category", ["Feed", "Medicine", "Semen Straws", "General Asset"], 
                           index=["Feed", "Medicine", "Semen Straws", "General Asset"].index(edit_data.get('Category', 'Feed')))
        uom = st.selectbox("Unit (UOM)", ["KG", "Bag", "Litre", "ml", "Straw", "Each"],
                           index=["KG", "Bag", "Litre", "ml", "Straw", "Each"].index(edit_data.get('UOM', 'KG')))
        qty = st.number_input("Quantity in Stock", value=float(edit_data.get('Quantity', 0.0)))
        rate = st.number_input("Cost per Unit", value=float(edit_data.get('Cost', 0.0)))
        
        if st.form_submit_button("💾 Save to Inventory"):
            if name:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (name, cat, uom, qty, rate))
                conn.commit()
                if 'edit_item' in st.session_state: del st.session_state['edit_item']
                st.success(f"{name} has been saved!")
                st.rerun()

    if st.button("Cancel / Clear Edit Mode"):
        if 'edit_item' in st.session_state: del st.session_state['edit_item']
        st.rerun()
