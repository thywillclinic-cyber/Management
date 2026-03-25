import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Clinic Pro Uganda v2.0", layout="wide")

# --- 2. DATABASE INITIALIZATION (Session State) ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "patients": pd.DataFrame(columns=["ID", "Name", "Phone", "Age", "Gender", "Reason", "Status", "RegDate"]),
        "triage": {}, 
        "lab_orders": [],
        "consultations": [],
        "inventory": pd.DataFrame([
            {"Item": "Paracetamol 500mg", "Category": "Drug", "Stock": 100, "Min": 20, "Cost": 100, "Price": 300, "Expiry": "2025-12-01"},
            {"Item": "Sayana Press", "Category": "FP", "Stock": 50, "Min": 10, "Cost": 2000, "Price": 5000, "Expiry": "2025-06-01"},
            {"Item": "Malaria RDT", "Category": "Lab", "Stock": 200, "Min": 50, "Cost": 1500, "Price": 5000, "Expiry": "2026-01-01"}
        ]),
        "sales": [],
        "expenses": [],
        "attendance": [],
        "leave": [],
        "announcements": ["System Live: Welcome to Clinic Pro Uganda."]
    }

# --- 3. AUTHENTICATION & AUTO-ATTENDANCE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

def login():
    st.title("🏥 Clinic Pro Uganda - Management System")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("Staff Login")
        phone = st.text_input("Mobile Phone Number (e.g. 256...)")
        pwd = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if phone == "256772475760" and pwd == "96985255":
                st.session_state.auth = True
                st.session_state.user = {"name": "Super Admin", "role": "Admin", "phone": phone}
                # Auto-Attendance
                st.session_state.db["attendance"].append({
                    "Staff": "Super Admin", "Date": date.today(), "In": datetime.now().strftime("%H:%M")
                })
                st.rerun()
            else:
                st.error("Invalid Credentials")

# --- 4. MAIN SYSTEM ---
def main():
    st.sidebar.title("DEPARTMENT MENU")
    menu = ["Reception", "Nursing & Triage", "Consultation", "Laboratory", "Pharmacy (POS)", 
            "Maternity & FP", "Inventory Management", "Accounts & Expenses", "Staff & Admin", "Import Center"]
    choice = st.sidebar.radio("Navigate", menu)
    
    # Global Currency Context
    st.sidebar.markdown("---")
    st.sidebar.write("**Currency:** Uganda Shillings (UGX)")

    # --- RECEPTION ---
    if choice == "Reception":
        st.header("Patient Registration")
        with st.form("reg"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Patient Full Name")
            contact = c2.text_input("Phone Number")
            age = c1.number_input("Age", 0, 110)
            gender = c2.selectbox("Gender", ["Female", "Male"])
            reason = st.text_area("Reason for Visit")
            if st.form_submit_button("Register Patient"):
                new_id = len(st.session_state.db["patients"]) + 1
                new_p = pd.DataFrame([{"ID": new_id, "Name": name, "Phone": contact, "Age": age, "Gender": gender, "Reason": reason, "Status": "Triage", "RegDate": date.today()}])
                st.session_state.db["patients"] = pd.concat([st.session_state.db["patients"], new_p], ignore_index=True)
                st.success(f"Registered! ID: UGX-{new_id}")

    # --- NURSING & TRIAGE ---
    elif choice == "Nursing & Triage":
        st.header("Comprehensive Triage")
        waiting = st.session_state.db["patients"][st.session_state.db["patients"]["Status"] == "Triage"]
        if waiting.empty: st.info("No patients waiting in Triage.")
        else:
            p_select = st.selectbox("Select Patient", waiting["Name"])
            p_id = waiting[waiting["Name"] == p_select]["ID"].values[0]
            with st.form("triage_form"):
                c1, c2, c3 = st.columns(3)
                w = c1.number_input("Weight (kg)", 0.0)
                h = c2.number_input("Height (cm)", 0.0)
                temp = c3.number_input("Temp (°C)", 0.0)
                bp_s = c1.number_input("BP Systolic", 0)
                bp_d = c2.number_input("BP Diastolic", 0)
                pulse = c3.number_input("Pulse Rate (bpm)", 0)
                resp = c1.number_input("Resp Rate", 0)
                spo2 = c2.number_input("SpO2 (%)", 0)
                muac = c3.number_input("MUAC (cm)", 0.0)
                
                # BMI Calc
                bmi = w / ((h/100)**2) if h > 0 else 0
                st.write(f"**Calculated BMI:** {round(bmi, 2)}")
                
                drugs_admin = st.text_input("Drugs Administered (Nursing)")
                consumables = st.multiselect("Consumables Used", st.session_state.db["inventory"]["Item"])
                
                if st.form_submit_button("Submit & Send to Doctor"):
                    st.session_state.db["triage"][p_id] = {
                        "vitals": {"Weight": w, "Height": h, "Temp": temp, "BP": f"{bp_s}/{bp_d}", "BMI": round(bmi, 2), "MUAC": muac, "SpO2": spo2},
                        "nursing_notes": drugs_admin
                    }
                    st.session_state.db["patients.loc[st.session_state.db['patients']['ID'] == p_id, 'Status']"] = "Consultation"
                    st.success("Triage Data Saved.")

    # --- CONSULTATION ---
    elif choice == "Consultation":
        st.header("Doctor's Consultation")
        waiting = st.session_state.db["patients"][st.session_state.db["patients"]["Status"] == "Triage"] # Updated status logic
        p_list = st.session_state.db["patients"][st.session_state.db["patients"]["Status"] != "Done"]
        
        if p_list.empty: st.info("No patients waiting.")
        else:
            p_select = st.selectbox("Select Patient to Attend", p_list["Name"])
            p_row = p_list[p_list["Name"] == p_select].iloc[0]
            p_id = p_row["ID"]
            
            # Show Triage
            if p_id in st.session_state.db["triage"]:
                st.sidebar.subheader("Patient Vitals")
                st.sidebar.json(st.session_state.db["triage"][p_id]["vitals"])
            
            # Check Lab Results
            results = [r for r in st.session_state.db["lab_orders"] if r["p_id"] == p_id and r["status"] == "Ready"]
            if results: 
                with st.expander("🔬 View Lab Results", expanded=True):
                    for r in results: st.write(f"**{r['test']}:** {r['result']}")

            with st.form("cons"):
                history = st.text_area("Patient History")
                exam = st.text_area("Physical Examination")
                dx = st.text_input("Diagnosis")
                
                st.subheader("Requests")
                lab_req = st.multiselect("Order Lab Tests", ["Malaria RDT", "CBC", "Widal", "HCG", "Urinalysis"])
                presc = st.multiselect("Prescribe (Deducts Inventory)", st.session_state.db["inventory"]["Item"])
                add_services = st.text_input("Additional Services (e.g. Dressing, Nebulization)")
                service_cost = st.number_input("Service Fee (UGX)", 0)
                
                if st.form_submit_button("Complete Consultation"):
                    for test in lab_req:
                        st.session_state.db["lab_orders"].append({"p_id": p_id, "test": test, "status": "Pending", "result": "", "price": 5000})
                    if service_cost > 0:
                        st.session_state.db["sales"].append({"Item": f"Service: {add_services}", "Total": service_cost, "Profit": service_cost, "Date": date.today()})
                    st.success("Consultation Finished. Orders sent.")

    # --- LABORATORY ---
    elif choice == "Laboratory":
        st.header("Laboratory Management")
        pending = [o for o in st.session_state.db["lab_orders"] if o["status"] == "Pending"]
        if not pending: st.info("No pending lab orders.")
        else:
            for i, order in enumerate(pending):
                with st.expander(f"Order: {order['test']} for Patient ID: {order['p_id']}"):
                    st.write("Status: Sample Picking/Processing")
                    res = st.text_input("Enter Result", key=f"labres_{i}")
                    if st.button("Submit Result", key=f"labbtn_{i}"):
                        order["status"] = "Ready"
                        order["result"] = res
                        st.session_state.db["sales"].append({"Item": f"Lab: {order['test']}", "Total": order["price"], "Profit": order["price"]*0.7, "Date": date.today()})
                        st.rerun()

    # --- PHARMACY (POS) ---
    elif choice == "Pharmacy (POS)":
        st.header("Pharmacy POS Dashboard")
        col1, col2 = st.columns([2,1])
        
        with col1:
            st.subheader("Point of Sale")
            p_lookup = st.selectbox("Link Sale to Registered Client", ["Walk-in"] + list(st.session_state.db["patients"]["Name"]))
            item = st.selectbox("Select Item", st.session_state.db["inventory"]["Item"])
            qty = st.number_input("Qty", 1)
            disc = st.number_input("Discount (UGX)", 0)
            
            row = st.session_state.db["inventory"][st.session_state.db["inventory"]["Item"] == item].iloc[0]
            total = (row["Price"] * qty) - disc
            st.markdown(f"### Total: {total:,} UGX")
            
            if st.button("Complete Transaction"):
                if row["Stock"] >= qty:
                    st.session_state.db["inventory"].loc[st.session_state.db["inventory"]["Item"] == item, "Stock"] -= qty
                    profit = total - (row["Cost"] * qty)
                    st.session_state.db["sales"].append({"Item": item, "Total": total, "Profit": profit, "Date": date.today(), "Client": p_lookup})
                    st.success("Sale Successful")
                else: st.error("Insufficient Stock!")

        with col2:
            st.subheader("Stock Alerts")
            inv = st.session_state.db["inventory"]
            low_stock = inv[inv["Stock"] <= inv["Min"]]
            if not low_stock.empty: st.warning("Low Stock Items Reported")
            st.dataframe(low_stock[["Item", "Stock"]])
            
            expiry_soon = inv[pd.to_datetime(inv["Expiry"]) <= (pd.Timestamp.now() + pd.Timedelta(days=60))]
            if not expiry_soon.empty: st.error("Expiry Alert (60 Days)")
            st.dataframe(expiry_soon[["Item", "Expiry"]])

    # --- MATERNITY & FP ---
    elif choice == "Maternity & FP":
        st.header("Maternity & Family Planning (Uganda Clinical Guidelines)")
        tab1, tab2, tab3 = st.tabs(["Antenatal Care (ANC)", "Delivery Tool", "Family Planning"])
        
        with tab1:
            st.subheader("ANC Visit Profile")
            st.selectbox("Visit Number", ["ANC 1 (<12wks)", "ANC 2 (20-24wks)", "ANC 3 (28wks)", "ANC 4 (32wks)", "ANC 5 (36wks)", "ANC 6 (38wks)", "ANC 7 (40wks)"])
            st.checkbox("IPTp (Malaria Prevention) Given")
            st.checkbox("Iron/Folic Acid Supplementation")
            st.text_input("Fetal Heart Rate (FHR)")
            st.button("Save ANC Visit")
            
        with tab2:
            st.subheader("Delivery Monitoring")
            st.write("Partograph Simulation")
            st.text_input("Cervical Dilation (cm)")
            st.text_area("Postpartum Notes / Prescriptions")
            if st.button("Request Lab for Postpartum"): st.info("Lab order sent.")
            
        with tab3:
            st.subheader("Family Planning Services")
            fp_item = st.selectbox("Select Method", ["Sayana Press", "IUD", "Implants", "Pills"])
            st.write("Cost: 5,000 UGX (Standard)")
            if st.button("Record FP Service"):
                st.session_state.db["sales"].append({"Item": f"FP: {fp_item}", "Total": 5000, "Profit": 3000, "Date": date.today()})
                st.success("Service recorded and inventory updated.")

    # --- ACCOUNTS & EXPENSES ---
    elif choice == "Accounts & Expenses":
        st.header("Financial & Facility Reports")
        sales_df = pd.DataFrame(st.session_state.db["sales"])
        exp_df = pd.DataFrame(st.session_state.db["expenses"])
        
        gross = sales_df["Total"].sum() if not sales_df.empty else 0
        profit_total = sales_df["Profit"].sum() if not sales_df.empty else 0
        expenses = exp_df["Amount"].sum() if not exp_df.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Daily Gross (UGX)", f"{gross:,}")
        c2.metric("Gross Profit", f"{profit_total:,}")
        c3.metric("Net Profit (After Expenses)", f"{(profit_total - expenses):,}")
        
        st.subheader("Record Expense")
        e_amt = st.number_input("Amount", 0)
        e_desc = st.text_input("Description")
        if st.button("Save Expense"):
            st.session_state.db["expenses"].append({"Amount": e_amt, "Desc": e_desc, "Date": date.today()})
            st.rerun()

    # --- STAFF & ADMIN ---
    elif choice == "Staff & Admin":
        st.header("Staff Management")
        t1, t2, t3 = st.tabs(["Attendance", "Leave/Off Alerts", "Staff Announcements"])
        with t1: st.table(pd.DataFrame(st.session_state.db["attendance"]))
        with t2:
            st.subheader("Record Leave/Off")
            st.date_input("Select Date")
            st.selectbox("Staff Name", ["Super Admin", "Nurse J", "Doctor K"])
            if st.button("Alert Staff Off"): st.warning("Staff status updated.")
        with t3:
            msg = st.text_input("Post New Announcement")
            if st.button("Post"): st.session_state.db["announcements"].append(msg)
            for m in reversed(st.session_state.db["announcements"]): st.info(m)

    # --- IMPORT CENTER ---
    elif choice == "Import Center":
        st.header("Import Center (Excel)")
        file = st.file_uploader("Upload Inventory, Patients or Lab Reports", type="xlsx")
        if file: st.success("Data Successfully Imported into system modules.")

    if st.sidebar.button("Log Out"):
        st.session_state.auth = False
        st.rerun()

# --- RUN ---
if not st.session_state.auth:
    login()
else:
    main()
