import streamlit as st
import pandas as pd
import sqlite3
import os

# --- DATABASE & SESSION SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        PenID TEXT, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER,
        PRIMARY KEY (PenID, ItemName))""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.set_page_config(page_title="Zuni ERP Pro", layout="wide")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 15px; border-bottom: 5px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>📦 ZUNI <span style='color: #FF851B;'>TMR MASTER ERP</span></h1>
        <p style='color: #FF851B; margin: 0;'>Precision Feeding & Inventory Management</p>
    </div>
    """, unsafe_allow_html=True)

# Fetch Data
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

tabs = st.tabs(["🚜 DAILY FEEDING", "📦 STOCK REPORT", "💊 MEDICINES", "🧬 SEMEN BANK", "➕ ADD/EDIT MASTER"])

# --- 1. DAILY FEEDING (THE MASTER RECIPE FORM) ---
with tabs[0]:
    st.subheader("📝 Pen Recipe Master Form")
    
    # Recipe Creation Form (Bulk)
    with st.container(border=True):
        with st.form("bulk_recipe_form"):
            col1, col2 = st.columns(2)
            f_pen = col1.text_input("PEN NAME (e.g., DRY COWS / SHED-A)").upper()
            f_count = col2.number_input("TOTAL ANIMALS IN THIS PEN", min_value=1, value=10)
            
            st.markdown("---")
            st.write("**Set Ingredient Quantity (KG Per Animal):**")
            
            feed_items = stock_df[stock_df['Category']=='Feed']
            
            # Form grid for all feed ingredients
            recipe_updates = []
            if not feed_items.empty:
                cols = st.columns(4)
                for idx, row in enumerate(feed_items.itertuples()):
                    with cols[idx % 4]:
                        qty = st.number_input(f"{row.ItemName}", min_value=0.0, step=0.1, format="%.2f")
                        if qty > 0:
                            recipe_updates.append((f_pen, row.ItemName, qty, f_count))
            
            if st.form_submit_button("🚀 SAVE FULL PEN RECIPE"):
                if f_pen and recipe_updates:
                    conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (f_pen,))
                    conn.executemany("INSERT INTO FeedRecipes VALUES (?,?,?,?)", recipe_updates)
                    conn.commit()
                    st.success(f"Recipe Saved for {f_pen}!")
                    st.rerun()

    # Loading Sheet (Screenshot Style)
    st.divider()
    st.subheader("📋 Active Loading Sheets")
    if not recipes_df.empty:
        for pen in recipes_df['PenID'].unique():
            with st.container(border=True):
                p_data = recipes_df[recipes_df['PenID'] == pen].copy()
                p_data['Total Load (KG)'] = p_data['QtyPerAnimal'] * p_data['TotalAnimals']
                
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"### 📍 {pen}")
                c2.metric("Animals", p_data['TotalAnimals'].iloc[0])
                c3.metric("Total Mixer Load", f"{p_data['Total Load (KG)'].sum():,.1f} KG")
                
                st.dataframe(p_data[['ItemName', 'QtyPerAnimal', 'Total Load (KG)']], use_container_width=True, hide_index=True)
                
                col_btn1, col_btn2 = st.columns([1, 5])
                if col_btn1.button(f"✅ CONFIRM FEEDING", key=f"feed_{pen}"):
                    for _, r in p_data.iterrows():
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (r['Total Load (KG)'], r['ItemName']))
                    conn.commit()
                    st.success(f"Stock deducted for {pen}")
                    st.rerun()
                if col_btn2.button(f"🗑️ Delete Recipe", key=f"del_rec_{pen}"):
                    conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (pen,))
                    conn.commit()
                    st.rerun()

# --- 2. STOCK REPORT ---
with tabs[1]:
    st.subheader("📊 Live Inventory Report")
    st.dataframe(stock_df, use_container_width=True, hide_index=True)
    
    # Simple alert for low stock
    low_stock = stock_df[stock_df['Quantity'] < 100]
    if not low_stock.empty:
        st.warning("🚨 **Low Stock Alert:** " + ", ".join(low_stock['ItemName'].tolist()))

# --- 3 & 4. MEDICINES & SEMEN (HISTORY & EDIT) ---
for i, cat in enumerate(["Medicine", "Semen Straws"], 2):
    with tabs[i]:
        st.subheader(f"📜 {cat} Inventory & History")
        cat_items = stock_df[stock_df['Category'] == cat]
        if not cat_items.empty:
            for item in cat_items.itertuples():
                with st.container(border=True):
                    col_a, col_b, col_c, col_d = st.columns([3, 2, 1, 1])
                    col_a.write(f"**{item.ItemName}**")
                    col_b.write(f"Stock: {item.Quantity} {item.UOM} | Rate: {item.Cost}")
                    if col_c.button("✏️ Edit", key=f"ed_{item.ItemName}"):
                        st.session_state['edit_item'] = {'ItemName': item.ItemName, 'Category': item.Category, 'UOM': item.UOM, 'Quantity': item.Quantity, 'Cost': item.Cost}
                        st.info("Now go to 'ADD/EDIT MASTER' tab.")
                    if col_d.button("🗑️", key=f"del_{item.ItemName}"):
                        conn.execute("DELETE FROM ItemMaster WHERE ItemName=?", (item.ItemName,))
                        conn.commit()
                        st.rerun()

# --- 5. ADD/EDIT MASTER ---
with tabs[4]:
    st.subheader("➕ Master Inventory Entry")
    edit_data = st.session_state.get('edit_item', {})
    with st.form("master_item_form"):
        name = st.text_input("Item Name", value=edit_data.get('ItemName', '')).upper()
        cat = st.selectbox("Category", ["Feed", "Medicine", "Semen Straws", "General Asset"], 
                           index=["Feed", "Medicine", "Semen Straws", "General Asset"].index(edit_data.get('Category', 'Feed')))
        uom = st.selectbox("Unit", ["KG", "Bag", "Litre", "ml", "Straw", "Each"],
                           index=["KG", "Bag", "Litre", "ml", "Straw", "Each"].index(edit_data.get('UOM', 'KG')))
        qty = st.number_input("Stock Quantity", value=float(edit_data.get('Quantity', 0.0)))
        rate = st.number_input("Rate per Unit", value=float(edit_data.get('Cost', 0.0)))
        
        if st.form_submit_button("💾 Save Item"):
            conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (name, cat, uom, qty, rate))
            conn.commit()
            if 'edit_item' in st.session_state: del st.session_state['edit_item']
            st.success("Item saved!")
            st.rerun()
