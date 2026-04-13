import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni_Enterprise.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, 
        Quantity REAL DEFAULT 0, PurchasePrice REAL DEFAULT 0)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        RecipeName TEXT, ItemName TEXT, QtyPerHead REAL, Mandatory TEXT, TotalAnimals INTEGER,
        PRIMARY KEY (RecipeName, ItemName))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS DailyLogs (
        LogDate DATE, GroupName TEXT, FeedCost REAL, MilkRevenue REAL, MilkQty REAL)""")
    conn.commit()
    return conn

conn = get_connection()

# --- BRANDING ---
st.set_page_config(page_title="Zuni ERP Master", layout="wide")
st.markdown("<h1 style='color: #FF851B;'>📦 ZUNI PRO ENTERPRISE ERP</h1>", unsafe_allow_html=True)

# --- FETCH DATA ---
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)
recipes_df = pd.read_sql("SELECT * FROM FeedRecipes", conn)

# --- ALL TABS (RECIPE SET TO PRO, OTHERS RESTORED) ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "🥗 FEED RECIPES", "💊 MEDICINES", "🧬 SEMEN BANK", 
    "⛽ GENERAL STORE", "📈 PERFORMANCE", "📊 STOCK", "➕ REGISTER"
])

# --- TAB 1: PROFESSIONAL RECIPE BUILDER (IMAGE STYLE) ---
with t1:
    st.subheader("🧪 Professional Formulation Builder")
    col_l, col_r = st.columns([1, 3])
    
    with col_l:
        unique_groups = recipes_df['RecipeName'].unique().tolist() if not recipes_df.empty else []
        recipe_sel = st.selectbox("Select Formulation", ["+ NEW MIX"] + unique_groups)
        recipe_name = st.text_input("Recipe Name").upper() if recipe_sel == "+ NEW MIX" else recipe_sel
        total_an = st.number_input("Total Animals", min_value=1, value=100)

    with col_r:
        # Excel-like Batch Editor for 20-25 items
        feed_items = stock_df[stock_df['Category']=='Feed']['ItemName'].tolist()
        existing = recipes_df[recipes_df['RecipeName'] == recipe_name][['ItemName', 'QtyPerHead', 'Mandatory']] if not recipes_df.empty else pd.DataFrame(columns=['ItemName', 'QtyPerHead', 'Mandatory'])
        
        st.write(f"### Formulation Sheet: {recipe_name}")
        edited_sheet = st.data_editor(
            existing, num_rows="dynamic", use_container_width=True,
            column_config={
                "ItemName": st.column_config.SelectboxColumn("Ingredient", options=feed_items, required=True),
                "QtyPerHead": st.column_config.NumberColumn("Qty (kg)", min_value=0, format="%.3f"),
                "Mandatory": st.column_config.SelectboxColumn("Mandatory", options=["Yes", "No"], default="Yes")
            }, key=f"editor_{recipe_name}"
        )
        
        c1, c2 = st.columns(2)
        if c1.button("💾 SAVE RECIPE STRUCTURE", type="primary", use_container_width=True):
            conn.execute("DELETE FROM FeedRecipes WHERE RecipeName=?", (recipe_name,))
            for _, row in edited_sheet.iterrows():
                if row['ItemName']:
                    conn.execute("INSERT INTO FeedRecipes VALUES (?,?,?,?,?)", (recipe_name, row['ItemName'], row['QtyPerHead'], row['Mandatory'], total_an))
            conn.commit()
            st.success("Recipe Saved Successfully!")

        if c2.button("🚜 POST & DEDUCT STOCK", use_container_width=True):
            total_daily_cost = 0
            for _, row in edited_sheet.iterrows():
                usage = row['QtyPerHead'] * total_an
                rate = stock_df[stock_df['ItemName'] == row['ItemName']]['PurchasePrice'].iloc if row['ItemName'] in stock_df['ItemName'].values else 0
                total_daily_cost += (usage * rate)
                conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (usage, row['ItemName']))
            st.session_state['last_cost'] = total_daily_cost
            conn.commit()
            st.warning(f"Stock Updated. Daily Cost: Rs. {total_daily_cost:,.0f}")

# --- TAB 2: MEDICINES ---
with t2:
    st.subheader("💊 Medicine & Vaccine Stock")
    st.dataframe(stock_df[stock_df['Category'].isin(['Medicine', 'Vaccine'])], use_container_width=True)

# --- TAB 3: SEMEN BANK ---
with t3:
    st.subheader("🧬 Semen Straw Inventory")
    st.dataframe(stock_df[stock_df['Category'] == 'Semen Straws'], use_container_width=True)

# --- TAB 4: GENERAL STORE ---
with t4:
    st.subheader("⛽ Fuel & General Assets")
    st.dataframe(stock_df[stock_df['Category'] == 'General Asset'], use_container_width=True)

# --- TAB 5: PERFORMANCE ---
with t5:
    st.subheader("📈 Farm Profitability (Milk vs Feed)")
    logs_df = pd.read_sql("SELECT * FROM DailyLogs", conn)
    if not logs_df.empty:
        st.line_chart(logs_df.set_index('LogDate')[['FeedCost', 'MilkRevenue']])
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("Log daily data to see trends.")

# --- TAB 6: FULL STOCK ---
with t6:
    st.subheader("📊 Warehouse Inventory")
    st.dataframe(stock_df, use_container_width=True)
    # Purchase Entry Section
    st.divider()
    st.write("### 📥 Update Stock (Purchase)")
    with st.form("buy"):
        col1, col2, col3 = st.columns(3)
        b_item = col1.selectbox("Item", stock_df['ItemName'].tolist())
        b_qty = col2.number_input("Qty In", min_value=0.0)
        b_rate = col3.number_input("Rate", min_value=0.0)
        if st.form_submit_button("Update Stock"):
            conn.execute("UPDATE ItemMaster SET Quantity = Quantity + ?, PurchasePrice = ? WHERE ItemName = ?", (b_qty, b_rate, b_item))
            conn.commit()
            st.rerun()

# --- TAB 7: REGISTER NEW ---
with t7:
    st.subheader("➕ Register New Category")
    with st.form("reg"):
        nn = st.text_input("Item Name").upper()
        cc = st.selectbox("Category", ["Feed", "Medicine", "Vaccine", "Semen Straws", "General Asset"])
        uu = st.selectbox("Unit", ["KG", "Bag", "Litre", "No"])
        if st.form_submit_button("Register"):
            conn.execute("INSERT OR REPLACE INTO ItemMaster (ItemName, Category, UOM) VALUES (?,?,?)", (nn, cc, uu))
            conn.commit()
            st.rerun()
