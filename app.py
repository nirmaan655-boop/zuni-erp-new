import streamlit as st
import pandas as pd
from zuni_db import db_connect, fetch_df

# --- 1. SESSION STATE FOR ROLES ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_role" not in st.session_state: st.session_state.user_role = None

# --- 2. LOGIN SYSTEM WITH ROLES ---
def login_screen():
    st.markdown("<h2 style='text-align: center; color: #FF851B;'>🔐 ZUNI ERP LOGIN</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("LOGIN", type="primary", use_container_width=True):
            # Master User Credentials
            if user == "master" and pw == "zuni786":
                st.session_state.logged_in = True
                st.session_state.user_role = "Master"
                st.rerun()
            # Vet User Credentials
            elif user == "vet" and pw == "vet123":
                st.session_state.logged_in = True
                st.session_state.user_role = "Vet"
                st.rerun()
            else:
                st.error("❌ Invalid Login Details")
    return False

# --- 3. MAIN APP LOGIC ---
if not st.session_state.logged_in:
    login_screen()
else:
    # Sidebar Info
    st.sidebar.success(f"✅ Logged in as: {st.session_state.user_role}")
    if st.sidebar.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()

    # Branding Header
    st.markdown("<h1 style='text-align: center; color: #FF851B;'>ZUNI ERP CONTROL CENTER</h1>", unsafe_allow_html=True)

    # Role-Based Sidebar Access (Hide tabs based on Role)
    if st.session_state.user_role == "Vet":
        st.sidebar.warning("Note: Accounting Access is Restricted for Vet.")
        # Is role ke liye hum sirf zaruri pages dikhayenge (Sidebar logic in Streamlit pages folder is automatic)
    
    # --- DASHBOARD METRICS ---
    with db_connect() as conn:
        try:
            total = fetch_df(conn, "SELECT COUNT(*) as c FROM Livestock")['c'].iloc[0]
            cash = fetch_df(conn, "SELECT SUM(Balance) as b FROM ChartOfAccounts")['b'].iloc[0]
        except: total = cash = 0

    c1, c2 = st.columns(2)
    c1.metric("Total Livestock", total)
    
    # Financial data only for Master
    if st.session_state.user_role == "Master":
        c2.metric("Total Cash/Bank", f"Rs. {cash:,.0f}")
    else:
        c2.info("💰 Finance data hidden for Vet")

    st.divider()
    st.write(f"Welcome back! You have **{st.session_state.user_role}** permissions.")
