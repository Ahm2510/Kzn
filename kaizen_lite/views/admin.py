"""
Admin view - add firm accounts (replaces add_firm.py CLI).
Protected by admin secret.
"""
import streamlit as st
import secrets
import string
import streamlit_authenticator as stauth

from db import init_db, create_firm, get_firm_by_email


def render():
    """Render the admin view."""
    st.markdown("# Admin - Add Firm Account")
    
    # Admin secret check
    admin_secret = st.text_input("Enter admin secret", type="password")
    expected_secret = st.secrets.get("admin_secret")
    
    if not expected_secret:
        st.error("ADMIN_SECRET not configured in Streamlit secrets")
        return
    
    if admin_secret != expected_secret:
        st.warning("Enter the admin secret to access this page")
        return
    
    st.success("Admin access granted")
    st.markdown("---")
    
    # Initialize database
    init_db()
    
    # Add firm form
    st.markdown("## Add New Firm")
    
    firm_name = st.text_input("Firm Name")
    contact_email = st.text_input("Contact Email")
    username = st.text_input("Username")
    
    password_option = st.radio("Password", ["Generate automatically", "Set manually"])
    
    if password_option == "Set manually":
        password = st.text_input("Password", type="password")
    else:
        password = None
    
    if st.button("Create Firm Account"):
        if not firm_name or not contact_email or not username:
            st.error("Please fill in all required fields")
            return
        
        if password_option == "Set manually" and not password:
            st.error("Please provide a password")
            return
        
        # Generate password if needed
        if password is None:
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            st.info(f"Generated password: `{password}`")
        
        # Hash password
        hashed_password = stauth.Hasher.hash(password)
        
        # Check if email already exists
        existing = get_firm_by_email(contact_email)
        if existing:
            st.error(f"A firm with email '{contact_email}' already exists")
            return
        
        # Add to database
        try:
            firm_id = create_firm(firm_name, contact_email)
            st.success(f"Firm account created successfully!")
            st.markdown(f"""
            **Firm Details:**
            - Firm ID: {firm_id}
            - Firm Name: {firm_name}
            - Contact Email: {contact_email}
            - Username: {username}
            - Password: `{password}`
            
            **Next Steps:**
            1. Copy the following TOML block and add it to your Streamlit Cloud Secrets:
            ```toml
            [credentials.usernames.{username}]
            email = "{contact_email}"
            name = "{firm_name}"
            password = "{hashed_password}"
            ```
            2. Share the username (`{username}`) and plaintext password (`{password}`) with the firm so they can log in.
            """)
        except Exception as e:
            st.error(f"Failed to create firm: {str(e)}")
    
    st.markdown("---")
    
    # Show existing firms
    st.markdown("## Existing Firms")
    from db import get_all_firms
    firms = get_all_firms()
    
    if firms:
        for firm in firms:
            st.markdown(f"""
            **{firm['firm_name']}** (ID: {firm['firm_id']})
            - Email: {firm['contact_email']}
            - Created: {firm['created_at']}
            """)
    else:
        st.info("No firms created yet")
