"""
Authentication module using streamlit-authenticator with Streamlit secrets.
Handles login, session state, and firm_id resolution.
"""
import streamlit as st
import streamlit_authenticator as stauth
from typing import Optional

_authenticator_instance = None

def reset_authenticator():
    """Reset the authenticator instance for the current rerun."""
    global _authenticator_instance
    _authenticator_instance = None


def get_authenticator():
    """Initialize and return the streamlit-authenticator instance from secrets."""
    global _authenticator_instance
    if _authenticator_instance is not None:
        return _authenticator_instance

    import json
    # Convert secrets to a standard Python dictionary to prevent item assignment errors
    secrets_dict = st.secrets.to_dict()
    credentials = secrets_dict.get("credentials", {"usernames": {}})
    
    # Get cookie secret from secrets
    cookie_secret = st.secrets.get("cookie_secret")
    if not cookie_secret:
        raise ValueError("COOKIE_SECRET not set in Streamlit secrets")
    
    # Build config
    config = {
        "credentials": credentials,
        "cookie": {
            "name": "kaizen_lite_auth",
            "key": cookie_secret,
            "expiry_days": 7
        }
    }
    
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        auto_hash=True,
    )
    _authenticator_instance = authenticator
    return authenticator


def login():
    """Handle login natively without stauth."""
    import bcrypt
    
    name = st.session_state.get("name")
    authentication_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username")
    
    if authentication_status is None or authentication_status is False:
        with st.form("native_login_form"):
            st.subheader("Login")
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                # Check credentials from secrets
                secrets_dict = st.secrets.to_dict()
                credentials = secrets_dict.get("credentials", {"usernames": {}})
                usernames = credentials.get("usernames", {})
                
                if user_input in usernames:
                    stored_pass = usernames[user_input].get("password", "")
                    
                    is_valid = False
                    if stored_pass.startswith("$2b$"):
                        try:
                            is_valid = bcrypt.checkpw(pass_input.encode('utf-8'), stored_pass.encode('utf-8'))
                        except Exception:
                            is_valid = False
                    else:
                        is_valid = (pass_input == stored_pass)
                        
                    if is_valid:
                        st.session_state["authentication_status"] = True
                        st.session_state["username"] = user_input
                        st.session_state["name"] = usernames[user_input].get("name", "")
                        st.rerun()
                    else:
                        st.session_state["authentication_status"] = False
                        st.error("Username/password is incorrect")
                else:
                    st.session_state["authentication_status"] = False
                    st.error("Username/password is incorrect")
                    
    elif authentication_status is True:
        # Resolve firm_id from email if missing
        if "firm_id" not in st.session_state:
            _resolve_firm_from_username(username)
            if "firm_id" in st.session_state:
                st.rerun()
            
    return name, authentication_status, username


def logout():
    """Handle user logout natively."""
    if st.sidebar.button("Logout"):
        for key in ["firm_id", "firm_name", "username", "authentication_status", "name"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def is_logged_in() -> bool:
    """Check if user is logged in."""
    # We don't call get_authenticator() here to avoid StreamlitDuplicateElementKey
    if st.session_state.get("authentication_status"):
        # If logged in but firm_id missing (e.g., from cookie auto-login or rerun), resolve it
        if "firm_id" not in st.session_state:
            _resolve_firm_from_username(st.session_state.get("username"))
        return st.session_state.get("authentication_status") is True
    return False


def _resolve_firm_from_username(username):
    try:
        if not username:
            return
        from db import get_firm_by_email
        import json
        secrets_dict = st.secrets.to_dict()
        credentials = secrets_dict.get("credentials", {"usernames": {}})
        user_config = credentials.get("usernames", {}).get(username)
        if user_config:
            email = user_config.get("email")
            firm = get_firm_by_email(email)
            if firm:
                st.session_state["firm_id"] = firm["firm_id"]
                st.session_state["firm_name"] = firm["firm_name"]
                st.session_state["username"] = username
            else:
                st.error("Firm account not found in database. Contact support.")
                st.session_state["authentication_status"] = False
        else:
            st.error("User configuration error.")
            st.session_state["authentication_status"] = False
    except Exception as e:
        st.error(f"FATAL ERROR inside _resolve_firm_from_username: {e}")


def get_firm_id() -> Optional[int]:
    """Get the current firm_id from session state."""
    return st.session_state.get("firm_id")


def get_firm_name() -> Optional[str]:
    """Get the current firm_name from session state."""
    return st.session_state.get("firm_name")
