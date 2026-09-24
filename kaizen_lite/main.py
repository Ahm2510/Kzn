"""
Kaizen Lite - Streamlit entrypoint.
Demo mode: no auth. Routes straight into the dashboard / client detail view.
"""
import streamlit as st
from pathlib import Path

# Initialize database
from db import init_db
init_db()

# Import views
from views.dashboard import render as render_dashboard
from views.client_detail import render as render_client_detail
from views.admin import render as render_admin
from views.about import render as render_about
from auth import ensure_demo_firm


def main():
    """Main routing logic."""

    # Set page config
    st.set_page_config(
        page_title="Kaizen Lite",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Check for special views via query params
    query_params = st.query_params
    if "view" in query_params:
        if query_params["view"] == "admin":
            render_admin()
            return
        elif query_params["view"] == "about":
            render_about()
            return

    ensure_demo_firm()

    # Check if a client is selected
    if st.session_state.get("selected_client_id"):
        render_client_detail()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
