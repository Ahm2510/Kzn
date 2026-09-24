"""
Demo mode: authentication disabled.
Every session is auto-attached to a single demo firm so client data and
reports stay scoped to one tenant in the DB.
"""
import streamlit as st
from typing import Optional

DEMO_FIRM_NAME = "Test1"
DEMO_FIRM_EMAIL = "ayman@kaizenx.in"


def ensure_demo_firm():
    """Attach the current session to the demo firm, creating it if needed."""
    if "firm_id" in st.session_state:
        return

    from db import get_firm_by_email, create_firm

    firm = get_firm_by_email(DEMO_FIRM_EMAIL)
    if not firm:
        firm_id = create_firm(DEMO_FIRM_NAME, DEMO_FIRM_EMAIL)
        firm = {"firm_id": firm_id, "firm_name": DEMO_FIRM_NAME}

    st.session_state["firm_id"] = firm["firm_id"]
    st.session_state["firm_name"] = firm["firm_name"]


def get_firm_id() -> Optional[int]:
    """Get the current firm_id from session state."""
    return st.session_state.get("firm_id")


def get_firm_name() -> Optional[str]:
    """Get the current firm_name from session state."""
    return st.session_state.get("firm_name")
