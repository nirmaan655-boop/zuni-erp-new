import streamlit as st
from zuni_db import *

# ===============================
# AUTO START DB (VERY IMPORTANT)
# ===============================
init_db()

st.title("📦 Vendor Management System")

# ===============================
# ADD VENDOR FORM
# ===============================
st.subheader("➕ Add New Vendor")

with st.form("vendor_form"):
    name = st.text_input("Vendor Name")
    phone = st.text_input("Phone")
    address = st.text_area("Address")

    submit = st.form_submit_button("Save Vendor")

    if submit:
        if name:
            add_vendor(name, phone, address)
            st.success("Vendor Added Successfully ✅")
        else:
            st.error("Vendor name required!")


# ===============================
# SHOW VENDORS
# ===============================
st.subheader("📋 Vendor List")

df_v = fetch_df("SELECT * FROM VendorMaster")
st.dataframe(df_v, use_container_width=True)


# ===============================
# PURCHASE ENTRY
# ===============================
st.subheader("🛒 Add Purchase")

vendors = fetch_df("SELECT id, name FROM VendorMaster")

if len(vendors) > 0:
    vendor_dict = dict(zip(vendors["name"], vendors["id"]))

    with st.form("purchase_form"):
        vendor_name = st.selectbox("Select Vendor", vendor_dict.keys())
        date = st.date_input("Date")
        item = st.text_input("Item")
        amount = st.number_input("Amount", min_value=0.0)

        submit2 = st.form_submit_button("Save Purchase")

        if submit2:
            add_purchase(vendor_dict[vendor_name], str(date), item, amount)
            st.success("Purchase Saved ✅")
else:
    st.warning("Please add vendor first!")


# ===============================
# PAYMENT ENTRY
# ===============================
st.subheader("💰 Add Payment")

if len(vendors) > 0:

    with st.form("payment_form"):
        vendor_name2 = st.selectbox("Select Vendor", vendor_dict.keys(), key="pay_vendor")
        date2 = st.date_input("Date", key="pay_date")
        amount2 = st.number_input("Amount", min_value=0.0, key="pay_amount")

        submit3 = st.form_submit_button("Save Payment")

        if submit3:
            add_payment(vendor_dict[vendor_name2], str(date2), amount2)
            st.success("Payment Saved ✅")


# ===============================
# REPORT
# ===============================
st.subheader("📊 Vendor Report")

report = vendor_report()
st.dataframe(report, use_container_width=True)
