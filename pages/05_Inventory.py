import streamlit as st
import pandas as pd
import sqlite3
import os

# --- DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Item Master Table
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # Feed Recipes Table
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
        <p style='color: #FF851B; font-size: 16px; font-weight: bold;'>Inventory Management & Edit History System | FY 2026</p>
    </div>
    """, unsafe_allow_html=True)

# Fetch Data
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# Helper Function for History & Editing
def show_history_and_edit(category):
    st.markdown(f"### 📜 {category} History & Edit")
    items = stock_df[stock_df['Category'] == category]
    if not items.empty:
        for _, row in items.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
                c1.write(f"**{row['ItemName']}**")
                c2.write(f"Stock: {row['Quantity']} {row['UOM']}")
                c3.write(f"Rate: {row['Cost']}")
                
                # EDIT BUTTON: Ye data ko 'Add New' tab ke liye session state mein save kar sakta hai ya direct yahan
                if c4.button("✏️ Edit", key=f"edit_{row['ItemName']}"):
                    st.session_state['edit_item'] = row.to_dict()
                    st.info(f"Go to 'ADD/EDIT ITEM' tab to modify {row['ItemName']}")
                
                if c5.button("🗑️", key=f"del_{row['ItemName']}"):
                    conn.execute("DELETE FROM ItemMaster WHERE ItemName=?", (row['ItemName'],))
                    conn.commit()
                    st.rerun()
    else:
        st.info(f"No {category} items found.")

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🌾 FEED RECIPES", "💊 MEDICINES", "🧬 SEMEN BANK", "⛽ GENERAL STORE", "➕ ADD/EDIT ITEM"])

# --- 1. FEED RECIPES ---
with t1:
    st.subheader("📋 TMR Loading Sheet")
    if not recipes_df.empty:
        for pen in recipes_df['PenID'].unique():
            with st.container(border=True):
                p_data = recipes_df[recipes_df['PenID'] == pen].copy()
                p_data['Total Load (KG)'] = p_data['QtyPerAnimal'] * p_data['TotalAnimals']
                st.markdown(f"#### 📍 {pen} (Animals: {p_data['TotalAnimals'].iloc[0]})")
                st.table(p_data[['ItemName', 'QtyPerAnimal', 'Total Load (KG)']])
                if st.button(f"Confirm Feeding {pen}", key=f"f_{pen}"):
                    for _, r in p_data.iterrows():
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (r['Total Load (KG)'], r['ItemName']))
                    conn.commit()
                    st.success("Stock Deducted!")
                    st.rerun()

# --- 2, 3, 4. MEDICINES, SEMEN, GENERAL ---
with t2: show_history_and_edit("Medicine")
with t3: show_history_and_edit("Semen Straws")
with t4: show_history_and_edit("General Asset")

# --- 5. ADD / EDIT ITEM (MASTER FORM) ---
with t5:
    st.subheader("➕ Register or Update Item")
    
    # Pre-fill if Edit is clicked
    edit_data = st.session_state.get('edit_item', {})
    
    with st.form("master_form", clear_on_submit=True):
        f_name = st.text_input("Item Name", value=edit_data.get('ItemName', '')).upper()
        f_cat = st.selectbox("Category", ["Feed", "Medicine", "Semen Straws", "General Asset"], 
                             index=["Feed", "Medicine", "Semen Straws", "General Asset"].index(edit_data.get('Category', 'Feed')))
        f_uom = st.selectbox("Unit (UOM)", ["KG", "Bag", "Litre", "ml", "Straw", "Each"],
                             index=["KG", "Bag", "Litre", "ml", "Straw", "Each"].index(edit_data.get('UOM', 'KG')))
        f_qty = st.number_input("Current Stock / Initial Quantity", value=float(edit_data.get('Quantity', 0.0)))
        f_cost = st.number_input("Cost Price (Rate)", value=float(edit_data.get('Cost', 0.0)))
        
        if st.form_submit_button("✅ SAVE ITEM TO INVENTORY"):
            if f_name:
                conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", 
                             (f_name, f_cat, f_uom, f_qty, f_cost))
                conn.commit()
                if 'edit_item' in st.session_state: del st.session_state['edit_item']
                st.success(f"{f_name} saved successfully!")
                st.rerun()

    if st.button("Clear Edit Mode"):
        if 'edit_item' in st.session_state: del st.session_state['edit_item']
        st.rerun()
