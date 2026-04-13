import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- DATABASE SETUP ---
def get_connection():
    db_path = os.path.join(os.getcwd(), 'Zuni.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Master Recipe Table (Ek baar set karne ke liye)
    conn.execute("""CREATE TABLE IF NOT EXISTS FeedRecipes (
        PenID TEXT, ItemName TEXT, QtyPerAnimal REAL, PRIMARY KEY (PenID, ItemName))""")
    # Animal Count Table (Tadad alag save hogi)
    conn.execute("""CREATE TABLE IF NOT EXISTS PenAnimals (PenID TEXT PRIMARY KEY, TotalAnimals INTEGER)""")
    # Daily Consumption Log
    conn.execute("""CREATE TABLE IF NOT EXISTS ConsumptionLog (
        Date TEXT, PenID TEXT, ItemName TEXT, TotalQty REAL, TotalCost REAL)""")
    # Inventory
    conn.execute("""CREATE TABLE IF NOT EXISTS ItemMaster (
        ItemName TEXT PRIMARY KEY, Category TEXT, UOM TEXT, Quantity REAL DEFAULT 0, Cost REAL DEFAULT 0)""")
    conn.commit()
    return conn

conn = get_connection()
stock_df = pd.read_sql("SELECT * FROM ItemMaster", conn)

# --- 1. DAILY FEEDING (CONSOLIDATED SYSTEM) ---
st.title("🌾 Zuni Daily Feed System")

tabs = st.tabs(["🚜 CONFIRM DAILY FEED", "🛠️ SET MASTER RECIPE", "📜 HISTORY"])

# --- TAB 1: DAILY FEED (Rozana ka kaam) ---
with tabs[0]:
    st.subheader("Daily Feeding Confirmation")
    # Get all pens that have a recipe
    saved_pens = pd.read_sql("SELECT DISTINCT PenID FROM FeedRecipes", conn)['PenID'].tolist()
    
    if saved_pens:
        for pen in saved_pens:
            with st.container(border=True):
                # Get current animal count
                current_count_res = conn.execute("SELECT TotalAnimals FROM PenAnimals WHERE PenID=?", (pen,)).fetchone()
                current_count = current_count_res[0] if current_count_res else 10
                
                c1, c2 = st.columns([2,1])
                c1.markdown(f"### 📍 {pen}")
                new_count = c2.number_input(f"Animals in {pen}", min_value=1, value=current_count, key=f"count_{pen}")
                
                # Fetch the master recipe for this pen
                p_recipe = pd.read_sql(f"SELECT * FROM FeedRecipes WHERE PenID='{pen}'", conn)
                p_recipe['Total Load'] = p_recipe['QtyPerAnimal'] * new_count
                
                st.dataframe(p_recipe[['ItemName', 'QtyPerAnimal', 'Total Load']], use_container_width=True, hide_index=True)
                
                f_date = st.date_input("Feeding Date", datetime.now(), key=f"d_{pen}")
                
                if st.button(f"🚀 Confirm & Deduct Stock ({pen})", key=f"btn_{pen}"):
                    # Save the animal count for next time
                    conn.execute("INSERT OR REPLACE INTO PenAnimals VALUES (?,?)", (pen, new_count))
                    
                    for _, r in p_recipe.iterrows():
                        rate_res = conn.execute("SELECT Cost FROM ItemMaster WHERE ItemName=?", (r['ItemName'],)).fetchone()
                        rate = rate_res[0] if rate_res else 0
                        total_cost = r['Total Load'] * rate
                        
                        # Deduct Stock & Log
                        conn.execute("UPDATE ItemMaster SET Quantity = Quantity - ? WHERE ItemName = ?", (r['Total Load'], r['ItemName']))
                        conn.execute("INSERT INTO ConsumptionLog VALUES (?,?,?,?,?)", 
                                     (f_date.strftime('%Y-%m-%d'), pen, r['ItemName'], r['Total Load'], total_cost))
                    
                    conn.commit()
                    st.success(f"Feeding recorded for {pen} on {f_date}")
                    st.rerun()
    else:
        st.warning("Pehle 'SET MASTER RECIPE' tab mein ja kar recipe banayein.")

# --- TAB 2: MASTER RECIPE SETUP (Kabhi kabhi wala kaam) ---
with tabs[1]:
    st.subheader("🛠️ Define Master Recipe (One-Time Setup)")
    with st.form("master_recipe_form"):
        f_pen = st.text_input("New or Existing Pen Name").upper()
        feed_items = stock_df[stock_df['Category']=='Feed']
        
        updates = []
        cols = st.columns(3)
        for idx, row in enumerate(feed_items.itertuples()):
            with cols[idx % 3]:
                qty = st.number_input(f"{row.ItemName} (kg/animal)", min_value=0.0)
                if qty > 0: updates.append((f_pen, row.ItemName, qty))
        
        if st.form_submit_button("Save Master Recipe"):
            if f_pen and updates:
                conn.execute("DELETE FROM FeedRecipes WHERE PenID=?", (f_pen,))
                conn.executemany("INSERT INTO FeedRecipes VALUES (?,?,?)", updates)
                conn.commit()
                st.success("Master Recipe Saved!")
                st.rerun()

# --- TAB 3: HISTORY ---
with tabs[2]:
    st.subheader("📜 Date-wise Consumption")
    history_df = pd.read_sql("SELECT * FROM ConsumptionLog ORDER BY Date DESC", conn)
    st.dataframe(history_df, use_container_width=True)
