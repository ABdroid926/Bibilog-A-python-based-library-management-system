import streamlit as st
import datetime

# 1. Mock Database (In real life, this would load from a CSV or Database)
# In Streamlit, we use st.session_state so data doesn't wipe on every click
if "books" not in st.session_state:
    st.session_state.books = [
        {"id": 1, "title": "The Hobbit", "borrowed_by": "alice", "due_date": datetime.date(2026, 6, 1), "status": "On Time"},
        {"id": 2, "title": "1984", "borrowed_by": "bob", "due_date": datetime.date(2026, 5, 20), "status": "Overdue"},
        {"id": 3, "title": "Dune", "borrowed_by": None, "due_date": None, "status": "Available"},
    ]

st.title("📚 Bibilog Library Portal")

# 2. Simple Login System
if "user_role" not in st.session_state:
    st.session_state.user_role = None
    st.session_state.username = None

if st.session_state.user_role is None:
    st.subheader("Login")
    username = st.text_input("Username").lower().strip()
    password = st.text_input("Password", type="password")
    
    if st.button("Log In"):
        if username == "admin" and password == "admin123":
            st.session_state.user_role = "admin"
            st.rerun()
        elif username in ["alice", "bob"] and password == "password":
            st.session_state.user_role = "user"
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid credentials")

# 3. Logged In Views
else:
    if st.sidebar.button("Log Out"):
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.user_role == "admin":
        st.header("Admin Dashboard")
        st.subheader("All Lent Books")
        
        for book in st.session_state.books:
            if book["borrowed_by"]:
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{book['title']}** — Borrowed by: *{book['borrowed_by']}*")
                col2.write(f"Status: {book['status']} (Due: {book['due_date']})")
                if col3.button("Request Return", key=book["id"]):
                    st.info(f"Return request sent to {book['borrowed_by']} for '{book['title']}'!")

    # --- USER VIEW ---
    elif st.session_state.user_role == "user":
        st.header(f"Welcome back, {st.session_state.username.capitalize()}!")
        st.subheader("Your Borrowed Books")
        
        user_books = [b for b in st.session_state.books if b["borrowed_by"] == st.session_state.username]
        
        if user_books:
            for book in user_books:
                st.info(f"📖 **{book['title']}** \n* Due Date: {book['due_date']} \n* Status: {book['status']}")
        else:
            st.write("You haven't borrowed any books yet.")
