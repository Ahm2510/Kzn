"""
Dashboard view - landing page. A single "Try Kaizen" button drops straight
into the client upload/analysis flow (no client management for the demo).
"""
import streamlit as st
from auth import get_firm_id, get_firm_name
from db import get_scoped_clients, create_client

DEMO_CLIENT_NAME = "Demo Client"


def _get_or_create_demo_client(firm_id):
    """Get the firm's first client, creating a demo one if none exists."""
    clients = get_scoped_clients(firm_id)
    if clients:
        return clients[0]
    client_id = create_client(firm_id, DEMO_CLIENT_NAME)
    return {"client_id": client_id, "client_name": DEMO_CLIENT_NAME}


def render():
    """Render the dashboard landing page."""

    firm_id = get_firm_id()
    firm_name = get_firm_name()

    if not firm_id:
        st.error("Authentication error. Please log in again.")
        return

    # Sidebar
    with st.sidebar:
        st.markdown(f"### {firm_name}")
        st.markdown("---")
        st.markdown("[What is Kaizen Lite?](?view=about)")

    # Hero section
    st.markdown("""
    # A financial health audit for every client, in minutes.

    Upload a client's ledger export. Get receivables risk, customer concentration,
    revenue stability, and margin analysis — the review you don't have time to do manually,
    done automatically.
    """)

    st.markdown("---")

    # How it works
    st.markdown("## How it works")
    st.markdown("""
    1. Upload your client's sales/ledger export (Tally, Excel, or CSV)
    2. We auto-detect the relevant columns — no manual setup
    3. Get a branded PDF report with the findings that matter, and how they've changed since your last review
    """)

    st.markdown("---")

    # What this catches
    st.markdown("## What this catches")
    st.markdown("""
    - **Customers or accounts going quiet before it becomes a churn problem**
    - **Revenue overly dependent on one or two customers or products**
    - **Slow-paying accounts creating cash flow risk**
    - **Margin erosion that doesn't show up in a simple P&L glance**
    - **What's gotten WORSE since the last time you checked** — not just a snapshot, a trend
    """)

    st.markdown("---")

    if st.button("Try Kaizen", type="primary"):
        client = _get_or_create_demo_client(firm_id)
        st.session_state["selected_client_id"] = client["client_id"]
        st.rerun()
