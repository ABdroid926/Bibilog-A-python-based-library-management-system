import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="Library Portal", page_icon="📚", layout="centered")
st.title("📚 Community Library Portal")

# =====================================================================
# 1. SECURE DATA FETCHING
# =====================================================================
try:
    SHEET_URL = st.secrets["sheet_url"]
    SCRIPT_URL = st.secrets["script_url"]
    
    sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(csv_url)
except Exception as e:
    st.error("Security/Database configuration error. Check your Streamlit Secrets Dashboard.")
    st.stop()

# Initialize session states
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None

# --- LOGIN INTERFACE ---
if st.session_state.user_role is None:
    st.subheader("🔑 Member & Admin Login")
    
    username_input = st.text_input("Username").lower().strip()
    password_input = st.text_input("Password", type="password")
    
    if st.button("Log In", use_container_width=True):
        if username_input == "admin" and password_input == "admin123":
            st.session_state.user_role = "admin"
            st.session_state.username = "admin"
            st.rerun()
        elif username_input in df['borrowed_by'].dropna().astype(str).str.lower().unique() and password_input == "password":
            st.session_state.user_role = "user"
            st.session_state.username = username_input
            st.rerun()
        else:
            st.error("Invalid credentials.")

# --- LOGGED IN PORTALS ---
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username.capitalize()}**")
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.user_role == "admin":
        st.header("🛡️ Admin Dashboard")
        st.subheader("Current Book Loans & Statuses")
        
        borrowed_books = df[df["borrowed_by"].notna() & (df["borrowed_by"] != "")]
        
        if not borrowed_books.empty:
            for index, row in borrowed_books.iterrows():
                st.markdown("---")
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.write(f"📖 **{row['title']}**")
                    st.caption(f"Borrowed by: {str(row['borrowed_by']).capitalize()}")
                
                with col2:
                    status = row['status']
                    if status == "Return Requested":
                        st.markdown(f"Status: :orange[{status}]")
                    else:
                        st.markdown(f"Status: :green[{status}]")
                    st.caption(f"Due: {row['due_date']}")
                
                with col3:
                    if status != "Return Requested":
                        if st.button("🚨 Request Return", key=f"req_{row['id']}", use_container_width=True):
                            payload = {"id": int(row['id']), "status": "Return Requested"}
                            try:
                                # Send update to Google Apps Script
                                response = requests.post(SCRIPT_URL, data=json.dumps(payload))
                                if response.status_code == 200:
                                    st.toast("Notification updated live!")
                                    st.rerun()
                                else:
                                    st.error("Sheet rejected the update.")
                            except Exception as e:
                                st.error("Connection failed.")
                    else:
                        st.button("Alert Live!", key=f"pend_{row['id']}", disabled=True, use_container_width=True)
        else:
            st.info("🎉 All clear! No books are currently checked out.")

    # --- USER VIEW ---
    elif st.session_state.user_role == "user":
        current_user = st.session_state.username
        st.header(f"👋 Welcome back, {current_user.capitalize()}!")
        st.subheader("Your Checked Out Material")
        
        my_books = df[df["borrowed_by"].astype(str).str.lower() == current_user]
        
        if not my_books.empty:
            for index, row in my_books.iterrows():
                if row["status"] == "Return Requested":
                    st.error(f"⚠️ **⚠️ IMMEDIATE RETURN REQUESTED ⚠️**\n\nThe administration has flagged **{row['title']}** for return. Please hand it in.")
                else:
                    st.info(f"📖 **{row['title']}**\n\n* **Status:** {row['status']}\n* **Due Back:** {row['due_date']}")
        else:
            st.success("You aren't holding onto any books right now!")
