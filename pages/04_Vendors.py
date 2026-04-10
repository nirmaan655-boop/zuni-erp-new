# =========================
# VENDOR MODULE (PROCUREMENT)
# =========================

def get_vendors():
    with db_connect() as conn:
        df = fetch_df(conn, "SELECT VendorName FROM VendorMaster ORDER BY VendorName")
        if df is None or df.empty:
            return []
        return df["VendorName"].dropna().tolist()


st.subheader("🏢 Vendor Selection")

vendors = get_vendors()

col1, col2 = st.columns([3, 1])

with col1:
    vendor = st.selectbox(
        "Select Vendor",
        options=["-- Select Vendor --"] + vendors
    )

with col2:
    new_vendor = st.text_input("New Vendor")

# ➕ Add new vendor directly from procurement
if st.button("➕ Add Vendor"):
    if new_vendor.strip() != "":
        with db_connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO VendorMaster (VendorName)
                VALUES (?)
            """, (new_vendor.strip().upper(),))
            conn.commit()
        st.success("Vendor Added Successfully")
        st.rerun()

# ⚠️ validation
if vendor == "-- Select Vendor --":
    st.warning("Please select a vendor")
    st.stop()
