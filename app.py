import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Zuni ERP | Dashboard", layout="wide")

# --- CUSTOM CSS FOR MODERN LOOK ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #FF851B; }
    .main-title { background: linear-gradient(90deg, #001F3F 0%, #003366 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; border-bottom: 5px solid #FF851B; margin-bottom: 25px; }
    .card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #FF851B; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    </style>
    <div class="main-title">
        <h1 style='margin:0;'>🚜 ZUNI DAIRY SOLUTIONS | ERP DASHBOARD</h1>
        <p style='margin:0; font-weight:bold; color: #FF851B;'>Live Analytics & Financial Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

# --- DATA FETCHING (INTELLIGENT MAPPING) ---
with db_connect() as conn:
    try:
        # 1. Animal Metrics
        herd_df = fetch_df(conn, "SELECT Status, Category FROM AnimalMaster")
        total_animals = len(herd_df)
        sick_animals = len(herd_df[herd_df['Status'] == 'Sick'])
        pregnant = len(herd_df[herd_df['Status'] == 'Pregnant'])

        # 2. Financial Metrics (Payable/Receivable)
        # Receivables (Customer Ledger Debit Balance)
        rec_df = fetch_df(conn, "SELECT SUM(Debit - Credit) as bal FROM CustomerLedger")
        total_receivable = float(rec_df['bal'].iloc[0]) if not rec_df.empty and rec_df['bal'].iloc[0] else 0.0

        # Payables (Vendor Balance)
        pay_df = fetch_df(conn, "SELECT SUM(Balance) as bal FROM VendorMaster")
        total_payable = float(pay_df['bal'].iloc[0]) if not pay_df.empty and pay_df['bal'].iloc[0] else 0.0

        # Cash & Bank
        cash_df = fetch_df(conn, "SELECT SUM(Balance) as bal FROM ChartOfAccounts")
        cash_balance = float(cash_df['bal'].iloc[0]) if not cash_df.empty and cash_df['bal'].iloc[0] else 0.0

        # 3. Milk Summary (Last 7 Days)
        milk_df = fetch_df(conn, "SELECT Date, SUM(Total) as qty FROM MilkProduction GROUP BY Date ORDER BY Date DESC LIMIT 7")
        latest_milk = milk_df['qty'].iloc[0] if not milk_df.empty else 0
        
    except Exception as e:
        st.error(f"Data Sync Error: {e}")
        total_animals = sick_animals = total_receivable = total_payable = cash_balance = latest_milk = 0

# --- ROW 1: KEY PERFORMANCE INDICATORS ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.metric("🐄 Total Herd", total_animals)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.metric("🥛 Today's Milk", f"{latest_milk:,.0f} Ltr")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.metric("💰 Receivables", f"Rs. {total_receivable:,.0f}")
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.metric("💸 Payables", f"Rs. {total_payable:,.0f}")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --- ROW 2: CHARTS & ANALYTICS ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Milk Production Trend (Last 7 Days)")
    if not milk_df.empty:
        fig_milk = px.area(milk_df, x='Date', y='qty', line_shape='spline', color_discrete_sequence=['#FF851B'])
        fig_milk.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_milk, use_container_width=True)
    else:
        st.info("No production data available for charts.")

with col_right:
    st.subheader("📊 Herd Health")
    health_data = pd.DataFrame({
        "Status": ["Healthy", "Sick", "Pregnant"],
        "Count": [total_animals - sick_animals - pregnant, sick_animals, pregnant]
    })
    fig_health = px.pie(health_data, names='Status', values='Count', hole=0.5,
                        color_discrete_map={'Healthy':'#2ECC40', 'Sick':'#FF4136', 'Pregnant':'#0074D9'})
    fig_health.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=True)
    st.plotly_chart(fig_health, use_container_width=True)

# --- ROW 3: RECENT ACTIVITIES & CASH ---
st.divider()
row3_c1, row3_c2 = st.columns(2)

with row3_c1:
    st.subheader("🏦 Bank & Cash Status")
    with db_connect() as conn:
        acc_status = fetch_df(conn, "SELECT AccountName, Balance FROM ChartOfAccounts WHERE AccountType IN ('Cash In Hand', 'Bank Account')")
        if not acc_status.empty:
            st.dataframe(acc_status, use_container_width=True, hide_index=True)
            st.write(f"**Total Liquidity: Rs. {cash_balance:,.0f}**")

with row3_c2:
    st.subheader("🚨 Critical Stock Alerts")
    with db_connect() as conn:
        low_stock = fetch_df(conn, "SELECT ItemName, Quantity, UOM FROM ItemMaster WHERE Quantity < 10")
        if not low_stock.empty:
            st.warning(f"You have {len(low_stock)} items below safety level!")
            st.table(low_stock)
        else:
            st.success("All inventory levels are sufficient.")

# --- FOOTER ---
st.markdown("<br><p style='text-align:center; color:gray;'>Zuni ERP Pro v3.0 | Secure Financial Mapping Enabled</p>", unsafe_allow_html=True)
