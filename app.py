import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

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
        elif username_input in ["alice", "bob"] and password_input == "password":
            st.session_state.user_role = "user"
            st.session_state.username = username_input
            st.rerun()
        elif username_input in df['borrowed_by'].dropna().astype(str).str.lower().unique() and password_input == "password":
            st.session_state.user_role = "user"
            st.session_state.username = username_input
            st.rerun()
        else:
            st.error("Invalid credentials. Use 'admin', 'alice', or 'bob'.")

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
        
        # --- FEATURE: CHECKOUT FORM ---
        st.subheader("📥 Issue & Checkout Desk")
        
        # Find books that are currently available
        available_books = df[df["status"] == "Available"]
        
        if not available_books.empty:
            with st.form("checkout_form", clear_on_submit=True):
                # Create dropdown option text: "Book Title (ID: 1)"
                book_options = available_books.apply(lambda row: f"{row['title']} (ID: {row['id']})", axis=1).tolist()
                selected_book_string = st.selectbox("Select Available Book", book_options)
                
                # Input student name
                borrower_name = st.text_input("Student Username (e.g., alice, bob)").lower().strip()
                
                # Set return date picker (defaults to 14 days from today)
                due_date_picker = st.date_input("Return Due Date", datetime.now() + timedelta(days=14))
                
                submit_checkout = st.form_submit_form_button = st.form_submit_button("🚀 Issue Book", use_container_width=True)
                
                if submit_checkout:
                    if borrower_name:
                        # Extract the numeric ID out of our bracket string
                        selected_id = int(selected_book_string.split("(ID: ")[1].replace(")", ""))
                        
                        payload = {
                            "id": selected_id,
                            "action": "checkout",
                            "borrowed_by": borrower_name,
                            "due_date": due_date_picker.strftime("%Y-%m-%d")
                        }
                        try:
                            response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                            st.toast("Book assigned successfully!")
                            st.rerun()
                        except:
                            st.rerun()
                    else:
                        st.error("Please provide a valid student username.")
        else:
            st.success("📚 All books are currently checked out!")
            
        st.markdown("---")

        # --- ACTIVE LOANS TRACKER ---
        st.subheader("📋 Active Loans & Statuses")
        borrowed_books = df[df["borrowed_by"].notna() & (df["borrowed_by"].astype(str).str.strip() != "") & (df["status"] != "Available")]
        
        if not borrowed_books.empty:
            for index, row in borrowed_books.iterrows():
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
                        if st.button("🚨 Request", key=f"req_{row['id']}", use_container_width=True):
                            payload = {"id": int(row['id']), "action": "request"}
                            try:
                                response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                                st.toast("Return requested!")
                                st.rerun()
                            except:
                                st.rerun()
                    else:
                        st.button("Alert Live!", key=f"pend_{row['id']}", disabled=True, use_container_width=True)
                    
                    if st.button("↩️ Return", key=f"ret_{row['id']}", use_container_width=True):
                        payload = {"id": int(row['id']), "action": "return"}
                        try:
                            response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                            st.toast("Book checked back in!")
                            st.rerun()
                        except:
                            st.rerun()
                st.markdown("---")
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
            st.success("You aren't holding onto any books right now! Enjoy your free time. 🎉")
