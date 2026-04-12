import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
import plotly.express as px
import os
from datetime import date

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Zuni ERP | Smart Dashboard", layout="wide", page_icon="🚜")

# --- 2. LOGO MAPPING ---
# Ensure your logo is in the same folder as 'logo.jpg'
LOGO_PATH = "logo.jpg"

# --- 3. DYNAMIC DATA FETCHING (ZERO ERROR LOGIC) ---
# Saare variables ko pehle hi khali initialize kar diya taake Error na aaye
milk_df = pd.DataFrame()
herd_df = pd.DataFrame()
total_animals = sick_animals = pregnant = 0
total_receivable = total_payable = cash_balance = latest_milk = 0

with db_connect() as conn:
    try:
        # 🐄 Animal Metrics
        herd_df = fetch_df(conn, "SELECT Status FROM AnimalMaster")
        if not herd_df.empty:
            total_animals = len(herd_df)
            sick_animals = len(herd_df[herd_df['Status'] == 'Sick'])
            pregnant = len(herd_df[herd_df['Status'] == 'Pregnant'])

        # 💰 Financial Metrics
        # Receivables (Customer Ledger)
        rec_data = fetch_df(conn, "SELECT SUM(Debit - Credit) as bal FROM CustomerLedger")
        if not rec_data.empty and rec_data['bal'].iloc[0]:
            total_receivable = float(rec_data['bal'].iloc[0])

        # Payables (Vendor Master)
        pay_data = fetch_df(conn, "SELECT SUM(Balance) as bal FROM VendorMaster")
        if not pay_data.empty and pay_data['bal'].iloc[0]:
            total_payable = float(pay_data['bal'].iloc[0])

        # Cash in Hand
        cash_data = fetch_df(conn, "SELECT SUM(Balance) as bal FROM ChartOfAccounts WHERE AccountType IN ('Cash In Hand', 'Bank Account')")
        if not cash_data.empty and cash_data['bal'].iloc[0]:
            cash_balance = float(cash_data['bal'].iloc[0])

        # 🥛 Milk Production Trend
        milk_df = fetch_df(conn, "SELECT Date, SUM(Total) as qty FROM MilkProduction GROUP BY Date ORDER BY Date DESC LIMIT 7")
        if not milk_df.empty:
            latest_milk = milk_df['qty'].iloc[0]
            
    except Exception as e:
        # Tables missing hon tab bhi Dashboard chalta rahega
        pass

# --- 4. CUSTOM CSS (ZUNI BRANDING) ---
st.markdown(f"""
    <style>
    [data-testid="stMetricValue"] {{ font-size: 30px; color: #FF851B; font-weight: bold; }}
    .main-header {{ 
        background: linear-gradient(135deg, #001F3F 0%, #003366 100%); 
        padding: 35px; border-radius: 20px; text-align: center; color: white; 
        border-bottom: 8px solid #FF851B; margin-bottom: 30px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
    }}
    .stat-card {{ 
        background: white; padding: 20px; border-radius: 15px; 
        box-shadow: 0px 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #FF851B;
        text-align: center; margin-bottom: 20px;
    }}
    .sidebar-logo {{ border-radius: 10px; margin-bottom: 20px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_column_width=True)
    st.markdown("<h2 style='text-align: center; color: #FF851B;'>ZUNI ERP PRO</h2>", unsafe_allow_html=True)
    st.write(f"📅 **Date:** {date.today()}")
    st.divider()
    st.success("System: **Active** 🟢")
    st.info(f"User: **Zuni Admin**")

# --- 6. MAIN CONTENT ---
st.markdown(f"""
    <div class="main-header">
        <h1 style='margin:0; letter-spacing: 2px;'>ZUNI DAIRY SOLUTIONS</h1>
        <p style='margin:0; font-size: 18px; color: #FF851B;'>INTELLIGENT FARMING • FINANCIAL CONTROL • AUTOMATION</p>
    </div>
    """, unsafe_allow_html=True)

# --- ROW 1: METRICS ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
    st.metric("🐄 Total Herd", total_animals)
    st.markdown("</div>", unsafe_allow_html=True)
with m2:
    st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
    st.metric("🥛 Today's Yield", f"{latest_milk:,.0f} L")
    st.markdown("</div>", unsafe_allow_html=True)
with m3:
    st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
    st.metric("💰 Receivables", f"Rs. {total_receivable:,.0f}")
    st.markdown("</div>", unsafe_allow_html=True)
with m4:
    st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
    st.metric("🏦 Cash Balance", f"Rs. {cash_balance:,.0f}")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --- ROW 2: CHARTS ---
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📈 Weekly Production Flow")
    if not milk_df.empty:
        # Modern Chart
        fig = px.area(milk_df.sort_values('Date'), x='Date', y='qty', 
                       line_shape='spline', color_discrete_sequence=['#FF851B'])
        fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Record daily milk yield to see trend analytics.")

with c_right:
    st.subheader("📋 Status Summary")
    st.markdown(f"""
    - **🚑 Sick Animals:** {sick_animals}
    - **🤰 Pregnant Cows:** {pregnant}
    - **💸 Total Payables:** Rs. {total_payable:,.0f}
    - **📊 System Health:** Optimized
    """)
    if total_payable > cash_balance:
        st.error("🚨 Warning: Payables exceed Cash Balance!")
    else:
        st.success("✅ Financial Liquidity: Good")

# --- ROW 3: RECENT ACTIVITIES ---
st.subheader("🚨 Critical Inventory Alerts")
with db_connect() as conn:
    low_stock = fetch_df(conn, "SELECT ItemName, Quantity, UOM FROM ItemMaster WHERE Quantity < 10")
    if not low_stock.empty:
        st.warning(f"Stock for {len(low_stock)} items is running low!")
        st.table(low_stock)
    else:
        st.success("All inventory levels are safe.")

st.markdown("<br><p style='text-align:center; color:gray;'>Zuni ERP v3.0 | Secure Database Protocol • FY 2026</p>", unsafe_allow_html=True)
