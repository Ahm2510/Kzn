"""
Authentication module using streamlit-authenticator with Streamlit secrets.
Handles login, session state, and firm_id resolution.
"""
import streamlit as st
import streamlit_authenticator as stauth
from typing import Optional
def get_authenticator():
    """Initialize and return the streamlit-authenticator instance from secrets."""
    if "authenticator" in st.session_state:
        return st.session_state["authenticator"]

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
    st.session_state["authenticator"] = authenticator
    return authenticator


def login():
    """Handle login and set session state."""
    authenticator = get_authenticator()
    
    authenticator.login(location="main")
    
    name = st.session_state.get("name")
    authentication_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username")
    
    if authentication_status:
        # Resolve firm_id from email if missing
        if "firm_id" not in st.session_state:
            _resolve_firm_from_username(username)
    elif authentication_status is False:
        st.error("Username/password is incorrect")
    elif authentication_status is None:
        pass  # No login attempt yet
    
    return name, authentication_status, username


def logout():
    """Handle logout and clear session state."""
    authenticator = get_authenticator()
    authenticator.logout(location="main")
    
    # Clear session state
    for key in ["firm_id", "firm_name", "username", "authentication_status"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    """Check if user is logged in."""
    authenticator = get_authenticator()
    # In v0.4.x, login() handles cookie verification even if we don't render the form
    # but we must call it or check authentication_status
    if st.session_state.get("authentication_status"):
        # If logged in but firm_id missing (e.g., from cookie auto-login or rerun), resolve it
        if "firm_id" not in st.session_state:
            _resolve_firm_from_username(st.session_state.get("username"))
        return st.session_state.get("authentication_status") is True
    return False


def _resolve_firm_from_username(username):
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


def get_firm_id() -> Optional[int]:
    """Get the current firm_id from session state."""
    return st.session_state.get("firm_id")


def get_firm_name() -> Optional[str]:
    """Get the current firm_name from session state."""
    return st.session_state.get("firm_name")
