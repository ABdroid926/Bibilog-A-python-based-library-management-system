import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd


st.set_page_config(page_title="Library Portal", page_icon="📚", layout="centered")

st.title("📚 CBibilog Portal")

# GSHEETS PLUG IN 
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except Exception as e:
    st.error("Database connection failed. Check your secrets configuration.")
    st.stop()

#  who is logged in across page reruns
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None

# 3. LOGIN INTERFACE

if st.session_state.user_role is None:
    st.subheader("Login")
    
    username_input = st.text_input("Username").lower().strip()
    password_input = st.text_input("Password", type="password")
    
    if st.button("Log In", use_container_width=True):
        # Admin Credentials
        if username_input == "admin" and password_input == "admin123":
            st.session_state.user_role = "admin"
            st.session_state.username = "admin"
            st.success("Logged in as Admin!")
            st.rerun()
            
        # User Credentials (Checks if user exists in the Sheet data)
        elif username_input in df['borrowed_by'].dropna().unique() and password_input == "password":
            st.session_state.user_role = "user"
            st.session_state.username = username_input
            st.success(f"Welcome back, {username_input.capitalize()}!")
            st.rerun()
        else:
            st.error("Invalid username or password. (Try 'admin'/'admin123' or a borrower name/'password')")


# 4. LOGGED IN DASHBOARDS

else:
    # Sidebar Logout Button available to everyone logged in
    st.sidebar.write(f"Logged in as: **{st.session_state.username.capitalize()}**")
    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()

    # -----------------------------------------------------------------
    # ADMIN VIEW
    # -----------------------------------------------------------------
    if st.session_state.user_role == "admin":
        st.header("🛡️ Admin Dashboard")
        st.subheader("Current Book Loans & Statuses")
        
        # Filter data to show only books currently borrowed
        borrowed_books = df[df["borrowed_by"].notna() & (df["borrowed_by"] != "")]
        
        if not borrowed_books.empty:
            for index, row in borrowed_books.iterrows():
               
                st.markdown("---")
                
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.write(f"📖 **{row['title']}**")
                    st.caption(f"Borrowed by: {row['borrowed_by'].capitalize()} | ID: {row['id']}")
                
                with col2:
                   \
                    status = row['status']
                    if status == "Overdue":
                        st.markdown(f"Status: :red[{status}]")
                    elif status == "Return Requested":
                        st.markdown(f"Status: :orange[{status}]")
                    else:
                        st.markdown(f"Status: :green[{status}]")
                        
                    st.caption(f"Due: {row['due_date']}")
                
                with col3:
              
                    if status != "Return Requested":
                        if st.button("🚨 Request Return", key=f"req_{row['id']}", use_container_width=True):
                            
                            df.at[index, "status"] = "Return Requested"
                           
                            conn.update(data=df)
                            st.toast(f"Request sent for {row['title']}!")
                            st.rerun()
                    else:
                        st.button("Alert Pending", key=f"pend_{row['id']}", disabled=True, use_container_width=True)
        else:
            st.info("🎉 All clear! No books are currently checked out.")

    # -----------------------------------------------------------------
    # USER VIEW
    # -----------------------------------------------------------------
    elif st.session_state.user_role == "user":
        current_user = st.session_state.username
        st.header(f"👋 Welcome back, {current_user.capitalize()}!")
        st.subheader("Your Checked Out Material")
        
        # Filter the system data to isolate this specific user's book list
        my_books = df[df["borrowed_by"] == current_user]
        
        if not my_books.empty:
            for index, row in my_books.iterrows():
                # Throw a bright red error alert banner if the admin flagged it
                if row["status"] == "Return Requested":
                    st.error(
                        f"⚠️ **⚠️ IMMEDIATE RETURN REQUESTED ⚠️**\n\n"
                        f"The librarian has flagged **{row['title']}** for return. "
                        f"Please submit it back to the library immediately. (Original Due Date: {row['due_date']})"
                    )
                else:
                 
                    st.info(
                        f"📖 **{row['title']}**\n\n"
                        f"* **Status:** {row['status']}\n"
                        f"* **Due Back By:** {row['due_date']}"
                    )
        else:
            st.success("You aren't holding onto any books right now. Happy reading!")

   
