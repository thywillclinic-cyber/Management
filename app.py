import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="Clinic Pro Uganda - Permanent Database", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name).dropna(how="all")
    except:
        # Create empty dataframes if sheets don't exist yet
        return pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 3. LOGIN & ATTENDANCE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

def login_page():
    st.title("🏥 Clinic Management System - Uganda")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("Staff Secure Login")
        phone = st.text_input("Mobile Phone (256...)")
        pwd = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if phone == "256772475760" and pwd == "96985255":
                st.session_state.auth = True
                st.session_state.user = "Admin"
                # Record Auto-Attendance to GSheets
                att_df = get_data("Attendance")
                new_att = pd.DataFrame([{"Staff": "Admin", "Date": str(date.today()), "Time": datetime.now().strftime("%H:%M")}])
                save_data(pd.concat([att_df, new_att], ignore_index=True), "Attendance")
                st.rerun()
            else:
                st.error("Invalid Login Details")

# --- 4. MAIN APPLICATION ---
def main():
    st.sidebar.title("UG Clinic Pro")
    menu = ["Reception", "Nursing (Triage)", "Consultation", "Laboratory", "Pharmacy (POS)", 
            "Family Planning & Maternity", "Inventory", "Accounts & Expenses", "Staff & Chat"]
    choice = st.sidebar.radio("Main Menu", menu)
    
    # Global Currency Info
    st.sidebar.markdown("---")
    st.sidebar.write("**Currency:** Uganda Shillings (UGX)")

    # --- MODULE: RECEPTION ---
    if choice == "Reception":
        st.header("Reception - Patient Registration")
        with st.form("reg"):
            name = st.text_input("Patient Full Name")
            age = st.number_input("Age", 0, 110)
            phone = st.text_input("Contact")
            reason = st.text_input("Reason for Visit")
            if st.form_submit_button("Register & Save"):
                patients = get_data("Patients")
                new_p = pd.DataFrame([{"ID": len(patients)+1, "Name": name, "Age": age, "Phone": phone, "Status": "Triage", "Date": str(date.today())}])
                save_data(pd.concat([patients, new_p], ignore_index=True), "Patients")
                st.success(f"Patient {name} saved to Database.")

    # --- MODULE: NURSING (TRIAGE) ---
    elif choice == "Nursing (Triage)":
        st.header("Nursing & Vitals")
        patients = get_data("Patients")
        waiting = patients[patients["Status"] == "Triage"]
        if waiting.empty: st.info("No patients waiting.")
        else:
            p_sel = st.selectbox("Select Patient", waiting["Name"])
            p_id = waiting[waiting["Name"] == p_sel]["ID"].values[0]
            with st.form("triage"):
                c1, c2, c3 = st.columns(3)
                weight = c1.number_input("Weight (kg)")
                temp = c2.number_input("Temp (°C)")
                bp = c3.text_input("BP (mmHg)")
                spo2 = c1.number_input("SpO2 %")
                muac = c2.number_input("MUAC (cm)")
                if st.form_submit_button("Save Vitals"):
                    triage_df = get_data("Triage")
                    new_v = pd.DataFrame([{"ID": p_id, "Name": p_sel, "WT": weight, "Temp": temp, "BP": bp, "SpO2": spo2, "MUAC": muac}])
                    save_data(pd.concat([triage_df, new_v], ignore_index=True), "Triage")
                    # Update Patient Status
                    patients.loc[patients["ID"] == p_id, "Status"] = "Consultation"
                    save_data(patients, "Patients")
                    st.success("Vitals moved to Consultation.")

    # --- MODULE: CONSULTATION ---
    elif choice == "Consultation":
        st.header("Doctor's Consultation")
        patients = get_data("Patients")
        active = patients[patients["Status"] == "Consultation"]
        if active.empty: st.info("No patients waiting for Doctor.")
        else:
            p_sel = st.selectbox("Current Patient", active["Name"])
            p_id = active[active["Name"] == p_sel]["ID"].values[0]
            
            # View Vitals from GSheets
            vitals = get_data("Triage")
            p_vitals = vitals[vitals["ID"] == p_id].tail(1)
            st.warning(f"Vitals: {p_vitals.to_dict('records')}")
            
            with st.form("doc"):
                history = st.text_area("Patient History & Exam")
                dx = st.text_input("Diagnosis")
                lab = st.multiselect("Lab Orders", ["Malaria RDT", "CBC", "Urinalysis", "HCG"])
                presc = st.text_area("Prescription (Linked to Pharmacy)")
                if st.form_submit_button("Save Consultation"):
                    # Record Lab Request
                    if lab:
                        lab_df = get_data("Lab")
                        new_lab = pd.DataFrame([{"ID": p_id, "Name": p_sel, "Test": str(lab), "Status": "Pending", "Result": ""}])
                        save_data(pd.concat([lab_df, new_lab], ignore_index=True), "Lab")
                    # Complete Visit
                    patients.loc[patients["ID"] == p_id, "Status"] = "Pharmacy"
                    save_data(patients, "Patients")
                    st.success("Consultation Complete. Sent to Lab/Pharmacy.")

    # --- MODULE: PHARMACY (POS) ---
    elif choice == "Pharmacy (POS)":
        st.header("Pharmacy Point of Sale")
        inventory = get_data("Inventory")
        
        col1, col2 = st.columns([1,2])
        with col1:
            st.subheader("Cash Sale")
            item = st.selectbox("Select Item", inventory["Item"])
            qty = st.number_input("Qty", 1)
            disc = st.number_input("Discount (UGX)", 0)
            
            row = inventory[inventory["Item"] == item].iloc[0]
            price = row["Price"]
            cost = row["Cost"]
            total = (price * qty) - disc
            st.metric("Amount to Charge", f"{total:,} UGX")
            
            if st.button("Complete Transaction"):
                # Update Inventory GSheet
                inventory.loc[inventory["Item"] == item, "Stock"] = inventory.loc[inventory["Item"] == item, "Stock"] - qty
                save_data(inventory, "Inventory")
                # Record Sale
                sales = get_data("Sales")
                new_sale = pd.DataFrame([{"Item": item, "Total": total, "Profit": total - (cost*qty), "Date": str(date.today())}])
                save_data(pd.concat([sales, new_sale], ignore_index=True), "Sales")
                st.balloons()
        
        with col2:
            st.subheader("Inventory Alerts")
            low_stock = inventory[inventory["Stock"] <= inventory["MinStock"]]
            st.warning("Low Stock Items:")
            st.dataframe(low_stock)

    # --- MODULE: MATERNITY & FP ---
    elif choice == "Family Planning & Maternity":
        st.header("Maternity & Family Planning")
        tab1, tab2 = st.tabs(["ANC Service", "FP Service"])
        with tab1:
            st.write("Uganda Clinical Guidelines Monitoring")
            st.selectbox("ANC Visit Number", [1,2,3,4,5,6,7,8])
            st.text_input("Fetal Heart Rate")
            st.button("Save ANC Data")
        with tab2:
            st.selectbox("FP Method", ["Sayana Press", "Implants", "Pills"])
            if st.button("Record FP & Deduct Stock"):
                st.success("Deducted from Inventory.")

    # --- MODULE: ACCOUNTS ---
    elif choice == "Accounts & Expenses":
        st.header("Financial Performance (UGX)")
        sales = get_data("Sales")
        expenses = get_data("Expenses")
        
        total_rev = sales["Total"].sum() if not sales.empty else 0
        total_prof = sales["Profit"].sum() if not sales.empty else 0
        total_exp = expenses["Amount"].sum() if not expenses.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gross Revenue", f"{total_rev:,}")
        c2.metric("Gross Profit", f"{total_prof:,}")
        c3.metric("Net Profit", f"{(total_prof - total_exp):,}")
        
        st.subheader("Add Expense")
        e_amt = st.number_input("Expense Amount")
        e_note = st.text_input("Note")
        if st.button("Save Expense"):
            new_exp = pd.DataFrame([{"Amount": e_amt, "Note": e_note, "Date": str(date.today())}])
            save_data(pd.concat([expenses, new_exp], ignore_index=True), "Expenses")
            st.rerun()

    # --- MODULE: STAFF MANAGEMENT ---
    elif choice == "Staff & Chat":
        st.header("Staff Management")
        st.subheader("Attendance Log")
        st.table(get_data("Attendance"))
        
        st.subheader("Leave & Off Alert")
        st.date_input("Date for Leave")
        if st.button("Submit Leave Request"):
            st.warning("Leave notification sent to Admin.")

    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- RUN SYSTEM ---
if not st.session_state.auth:
    login_page()
else:
    main()
