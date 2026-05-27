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
        
        # --- FEATURE: CHECKOUT FORM WITH TEXT ENTRY ---
        st.subheader("📥 Issue & Checkout Desk")
        
        with st.form("checkout_form", clear_on_submit=True):
            # Admin types ID number or book title
            book_search = st.text_input("Enter Book ID or Title").strip()
            
            # Input student name
            borrower_name = st.text_input("Student Username (e.g., alice, bob)").lower().strip()
            
            # Input loan duration period in days
            loan_days = st.number_input("Loan Period (Days)", min_value=1, max_value=90, value=14, step=1)
            
            submit_checkout = st.form_submit_button("🚀 Issue Book", use_container_width=True)
            
            if submit_checkout:
                if not book_search or not borrower_name:
                    st.error("Please fill out both the Book search field and Student Username field.")
                else:
                    # Search logic: check if entry matches an ID number or part of a title
                    matched_book = pd.DataFrame()
                    
                    if book_search.isdigit():
                        matched_book = df[df["id"].astype(str) == book_search]
                    else:
                        matched_book = df[df["title"].astype(str).str.lower().str.contains(book_search.lower())]
                    
                    # Validate match outcomes
                    if matched_book.empty:
                        st.error(f"Could not find any book matching '{book_search}'.")
                    elif matched_book.iloc[0]["status"] != "Available":
                        st.error(f"❌ '{matched_book.iloc[0]['title']}' is already checked out to {str(matched_book.iloc[0]['borrowed_by']).capitalize()}!")
                    else:
                        # Success match found
                        target_row = matched_book.iloc[0]
                        calculated_due_date = datetime.now() + timedelta(days=int(loan_days))
                        
                        payload = {
                            "id": int(target_row["id"]),
                            "action": "checkout",
                            "borrowed_by": borrower_name,
                            "due_date": calculated_due_date.strftime("%Y-%m-%d")
                        }
                        try:
                            response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                            st.toast(f"Success! Checked out '{target_row['title']}' to {borrower_name.capitalize()}.")
                            st.rerun()
                        except:
                            st.rerun()
            
        st.markdown("---")

        # --- ACTIVE LOANS TRACKER ---
        st.subheader("📋 Active Loans & Statuses")
        borrowed_books = df[df["borrowed_by"].notna() & (df["borrowed_by"].astype(str).str.strip() != "") & (df["status"] != "Available")]
        
        if not borrowed_books.empty:
            for index, row in borrowed_books.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.write(f"📖 **{row['title']}** (ID: {row['id']})")
                    st.caption(f"Borrowed by: {str(row['borrowed_by']).capitalize()}")
                
                with col2:
                    status = row['status']
                    if status == "Return Requested":
                        st.markdown(f"Status: :orange[{status}]")
                    else:
                        st.markdown(f"Status: :green[{status}]")
                    st.caption(f"Due: {row['due_date']}")
                
                with col3:
                    # BUTTON 1: REQUEST RETURN
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
