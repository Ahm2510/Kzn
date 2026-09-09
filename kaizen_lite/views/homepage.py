"""
Homepage view - shown when user is not logged in.
Contains hero, how it works, what this catches, and login.
"""
import streamlit as st


def render():
    """Render the homepage."""
    
    # About link at top
    st.markdown("[What is Kaizen Lite? →](?view=about)")
    
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
    
    # What this is not
    st.markdown("## What this is not")
    st.markdown("""
    This is not a bookkeeping or filing tool. It doesn't replace compliance work. 
    It sits on top of data you already have and works as a periodic check even without 
    connecting live to your systems.
    """)
    
    st.markdown("---")
    
    # Request access info
    st.markdown("## Request Access")
    st.info("To request access, contact the Kaizen Lite team. They will provide login credentials.")
    
    st.markdown("---")
    
    # Login for existing firms
    st.markdown("## Already have an account?")
    
    with st.expander("Log in", expanded=False):
        from auth import login
        login()
