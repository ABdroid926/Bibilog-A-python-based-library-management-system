import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Bibilog", page_icon="📚", layout="centered")
st.title("📚 Bibilog Library Portal")


try:
    SHEET_URL = st.secrets["sheet_url"]
    SCRIPT_URL = st.secrets["script_url"]
    
    sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    
  
    csv_url_books = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(csv_url_books)
    
    
    csv_url_users = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=users"
    dfusers = pd.read_csv(csv_url_users)
    dfusers['username'] = dfusers['username'].astype(str).str.lower().str.strip()
except Exception as e:
    st.error("Database connection configuration error!")
    st.stop()


if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None


if st.session_state.user_role is None:
    menu_tab = st.radio("Choose Action", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    if menu_tab == "Login":
        st.subheader("🔑 Login!")
        username_input = st.text_input("Username").lower().strip()
        password_input = st.text_input("Password", type="password")
        
        if st.button("Log In", use_container_width=True):
            if username_input == st.secrets["admin"]and password_input == st.secrets["admin_pass"]:
                st.session_state.user_role = "admin"
                st.session_state.username = "admin"
                st.rerun()
            elif username_input in dfusers['username'].values:
                correct_password = str(dfusers[dfusers['username'] == username_input].iloc[0]['password']).strip()
                if str(password_input).strip() == correct_password:
                    st.session_state.user_role = "user"
                    st.session_state.username = username_input
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Username not found. Please sign up below!")

    else:
        st.subheader("📝 Sign Up!")
        new_user = st.text_input("Choose Username").lower().strip()
        new_pass = st.text_input("Choose Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        
        if st.button("Register Account", use_container_width=True):
            if not new_user or not new_pass:
                st.error("Please fill in all blanks.")
            elif new_user == st.secrets["admin"]:
                st.error("Username is reserved!")
            elif " " in new_user:
                st.error("Usernames cannot contain spaces!")
            elif new_pass != confirm_pass:
                st.error("Your Passwords do not match!")
            elif not any(char.isalpha() for in confirm_pass) : 
                st.error("Your Password must contain atleast one letter!")
             
            else:
                payload = {"action": "register", "username": new_user, "password": new_pass}
                try:
                    response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                    if "User Exists" in response.text:
                        st.error("That username is already taken!")
                    else:
                        st.success("Account created successfully! Click 'Existing Member Login' to sign in.")
                except:
                    st.error("Registration failed. Try again.")


else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username.capitalize()}**")
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()

   
    if st.session_state.user_role == "admin":
        st.space("large")
        st.header("🛡️ Admin Dashboard")
        
       
        st.subheader("📥 Issue & Checkout Desk")
        
        book_id_input = st.text_input("Enter Numeric Book ID Only")
        
       
        book_is_valid = False
        target_row = None
        
        if book_id_input:
            if not book_id_input.isdigit():
                st.error("❌ Invalid input. Please enter numbers only.")
            else:
               
                matched_book = df[df["id"].astype(str) == book_id_input]
                
                if matched_book.empty:
                    st.warning("🔍 No book matches this ID number yet!")
                else:
                    target_row = matched_book.iloc[0]
                    book_title = target_row["title"]
                    book_status = target_row["status"]
                    
                    if book_status != "Available":
                        st.error(f"📖 **Book Found:** '{book_title}' — ❌ Currently checked out to {str(target_row['borrowed_by']).capitalize()}")
                    else:
                        st.success(f"📖 **Book Found:** '{book_title}' — ✅ Available for Loan")
                        book_is_valid = True
                        
        
        with st.form("checkout_form", clear_on_submit=True):
            borrower_name = st.text_input("Student Username").lower().strip()
            loan_days = st.number_input("Loan Period (Days)", min_value=1, max_value=90, value=7, step=1)
            submit_checkout = st.form_submit_button("🚀 Issue Book", use_container_width=True)
            
            if submit_checkout:
                if not book_id_input or not borrower_name:
                    st.error("Please fill out both the Book ID and Student Username fields.")
                elif not book_is_valid:
                    st.error("Cannot issue book. Ensure the ID matches an 'Available' library item.")
                else:
                    calculated_due_date = datetime.now() + timedelta(days=int(loan_days))
                    payload = {
                        "id": int(target_row["id"]),
                        "action": "checkout",
                        "borrowed_by": borrower_name,
                        "due_date": calculated_due_date.strftime("%Y-%m-%d")
                    }
                    try:
                        response = requests.post(SCRIPT_URL, data=json.dumps(payload), timeout=10)
                        st.toast(f"Checked out '{target_row['title']}' successfully!")
                        st.rerun()
                    except:
                        st.rerun()
            
        st.markdown("---")

      
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

   
    elif st.session_state.user_role == "user":
        current_user = st.session_state.username
        st.header(f"👋 Welcome back, {current_user.capitalize()}!")
        st.subheader("Your Checked Out Material")
        
        my_books = df[df["borrowed_by"].astype(str).str.lower() == current_user]
        
        if not my_books.empty:
            for index, row in my_books.iterrows():
                if row["status"] == "Return Requested":
                    st.error(f"⚠️ **⚠️ IMMEDIATE RETURN REQUESTED ⚠️**\n\nThe librarian has flagged **{row['title']}** for return. Please hand it in.")
                else:
                    st.info(f"📖 **{row['title']}**\n\n* **Status:** {row['status']}\n* **Due Back:** {row['due_date']}")
        else:
            st.success("You aren't holding onto any books right now! Why not check out the library? 🎉")
