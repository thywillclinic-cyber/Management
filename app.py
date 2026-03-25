import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- NEW: CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Function to load data from Sheets
def load_data(worksheet_name):
    return conn.read(worksheet=worksheet_name)

# Function to save data to Sheets
def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- MODIFIED INITIALIZATION ---
# Instead of st.session_state.db, we now pull from Google Sheets
if 'init' not in st.session_state:
    try:
        st.session_state.patients_df = load_data("Patients")
        st.session_state.inventory_df = load_data("Inventory")
        st.session_state.sales_df = load_data("Sales")
        st.session_state.init = True
    except:
        st.error("Please set up Google Sheets secrets first!")

# --- EXAMPLE: SAVING A NEW PATIENT ---
# When you click "Register" in your Reception module:
def register_patient(name, phone, age):
    new_data = pd.DataFrame([{"Name": name, "Phone": phone, "Age": age, "RegDate": date.today()}])
    # Combine old data with new data
    updated_df = pd.concat([st.session_state.patients_df, new_data], ignore_index=True)
    # Save to Google Sheets permanently
    save_data(updated_df, "Patients")
    st.session_state.patients_df = updated_df
    st.success("Patient saved to Google Sheets!")

# ... (Continue with the rest of your app logic using these DataFrames)
