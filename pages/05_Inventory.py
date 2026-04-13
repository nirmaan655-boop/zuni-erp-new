import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # 1. Item Master
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    # 2. Feed Recipes (Fix: Added OR REPLACE logic in code)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        PenID TEXT, ItemName TEXT, 
        QtyPerAnimal REAL, TotalAnimals INTEGER,
        PRIMARY KEY (PenID, ItemName))""")
    # 3. Consumption Logs (For History)
    conn.execute("""CREATE TABLE IF NOT EXISTS ConsumptionLog (
        Date TEXT, PenID TEXT, ItemName TEXT, TotalQty REAL, TotalCost REAL)""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.set_page_config(page_title="Zuni ERP Master", layout="wide")
st.markdown("""
    <div style='background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 20px; border-radius: 15px; border-bottom: 5px solid #FF851B; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>📦 ZUNI <span style='color: #FF851B;'>PRO ERP MASTER</span></h1>
        <p style='color: #FF851B; margin: 0;'>Precision Feeding & Date-Wise History | FY 2026</p>
    </div>
    """, unsafe_allow_html=True)

# Fetch Data
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# Tabs
t1, t2, t3, t4, t5, t6 = st.tabs(["🌾 DAILY FEEDING", "📜 FEED HISTORY", "📊 STOCK REPORT", "💊 MEDICINES", "⛽ GENERAL STORE", "➕ ADD/EDIT MASTER"])

# --- 1. DAILY FEEDING (With Fix) ---
with t1:
    st.subheader("📋 Pen Recipe Master")
    with st.container(border=True):
        with st.form("tmr_form"):
            c1, c2 = st.columns(2)
            f_pen = c1.text_input("PEN NAME").upper()
            f_count = c2.number_input("TOTAL ANIMALS", min_value=1, value=1)
            st.write("---")
            feed_items = stock_df[stock_df['Category']=='Feed']
            recipe_list = []
            if not feed_items.empty:
                cols = st.columns(4)
                for idx, row in enumerate(feed_items.itertuples()):
                    with cols[idx % 4]:
                        qty = st.number_input(f"{row.ItemName}", min_value=0.0, format="%.2f", key=f"f_{row.ItemName}")
                        if qty > 0: recipe_list.append((f_pen, row.ItemName, qty, f_count))
            
            if st.form_submit_button("🚀 SAVE RECIPE"):
                if f_pen and recipe_list:
                    conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (f_pen,))
                    # FIXED: Added INSERT OR REPLACE to avoid IntegrityError
                    conn.executemany("INSERT OR REPLACE INTO FeedRecipes VALUES (?,?,?,?)", recipe_list)
                    conn.commit()
                    st.success(f"Recipe saved for {f_pen}!")
                    st.rerun()

    if not recipes_df.empty:
        st.divider()
        for pen in recipes_df['PenID'].unique():
            with st.container(border=True):
                p_data = recipes_df[recipes_df['PenID'] == pen].copy()
                p_data['Total Load'] = p_data['QtyPerAnimal'] * p_data['TotalAnimals']
                st.markdown(f"#### 📍 {pen} (Animals: {p_data['TotalAnimals'].iloc})")
                st.table(p_data[['ItemName', 'QtyPerAnimal', 'Total Load']])
                
                # DATE SELECTION FOR CONSUMPTION
                f_date = st.date_input("Feeding Date", datetime.now(), key=f"date_{pen}")
                
                if st.button(f"✅ CONFIRM FEEDING ({pen})", key=f"btn_{pen}"):
                    for _, r in p_data.iterrows():
                        # Get Item Cost
                        rate = stock_df[stock_df['ItemName']==r['ItemName']]['Cost'].values[0] if not stock_df[stock_df['ItemName']==r['ItemName']].empty else 0
                        total_cost = r['Total Load'] * rate
                        # 1. Deduct Stock
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (r['Total Load'], r['ItemName']))
                        # 2. Log History
                        conn.execute("INSERT INTO ConsumptionLog VALUES (?,?,?,?,?)", (f_date.strftime('%Y-%m-%d'), pen, r['ItemName'], r['Total Load'], total_cost))
                    conn.commit()
                    st.success(f"Feeding recorded for {f_date}")
                    st.rerun()

# --- 2. FEED HISTORY (DATE-WISE) ---
with t2:
    st.subheader("📜 Daily Consumption History")
    history_df = pd.read_sql("SELECT * FROM ConsumptionLog ORDER BY Date DESC", conn)
    if not history_df.empty:
        # Date Filter
        search_date = st.date_input("Filter by Date", datetime.now())
        filtered_h = history_df[history_df['Date'] == search_date.strftime('%Y-%m-%d')]
        st.dataframe(filtered_h, use_container_width=True, hide_index=True)
        st.metric("Total Cost for Day", f"Rs. {filtered_h['TotalCost'].sum():,.0f}")
    else:
        st.info("No feeding records found.")

# --- 3. STOCK REPORT ---
with t3:
    st.subheader("📊 Current Stock Status")
    st.dataframe(stock_df, use_container_width=True, hide_index=True)

# --- 4 & 5. MEDICINES & GENERAL STORE ---
for i, cat in enumerate(["Medicine", "General Asset"], 4):
    with [t4, t5][i-4]:
        st.subheader(f"📦 {cat} Records")
        cat_data = stock_df[stock_df['Category'] == cat]
        st.dataframe(cat_data, use_container_width=True, hide_index=True)

# --- 6. ADD/EDIT MASTER ---
with t6:
    st.subheader("➕ Inventory Master Form")
    edit_data = st.session_state.get('edit_item', {})
    with st.form("master_form"):
        n = st.text_input("Item Name", value=edit_data.get('ItemName', '')).upper()
        c = st.selectbox("Category", ["Feed", "Medicine", "Semen Straws", "General Asset"], index=0)
        u = st.selectbox("Unit", ["KG", "Bag", "Litre", "ml", "Straw", "Each"], index=0)
        q = st.number_input("Quantity", value=0.0)
        r = st.number_input("Rate", value=0.0)
        if st.form_submit_button("💾 Save Item"):
            conn.execute("INSERT OR REPLACE INTO ItemMaster VALUES (?,?,?,?,?)", (n, c, u, q, r))
            conn.commit()
            st.success("Item saved!")
            st.rerun()
