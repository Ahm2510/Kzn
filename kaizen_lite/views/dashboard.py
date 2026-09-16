"""
Dashboard view - authenticated view showing all clients for a firm.
"""
import streamlit as st
from auth import is_logged_in, get_firm_id, get_firm_name, logout
from db import get_scoped_clients, create_client, get_client_report_count, get_client_last_report_date
from delta_computation import compute_client_risk_trend


def render():
    """Render the dashboard."""
    
    firm_id = get_firm_id()
    firm_name = get_firm_name()
    
    if not firm_id:
        st.error("Authentication error. Please log in again.")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### {firm_name}")
        logout()
        st.markdown("---")
        
        # About link
        st.markdown("[What is Kaizen Lite?](?view=about)")
        st.markdown("---")
        
        # Client navigation
        st.markdown("#### Clients")
        clients = get_scoped_clients(firm_id)
        
        if clients:
            for client in clients:
                client_name = client["client_name"]
                client_id = client["client_id"]
                if st.button(client_name, key=f"nav_client_{client_id}"):
                    st.session_state["selected_client_id"] = client_id
                    st.rerun()
        else:
            st.info("No clients yet")
    
    # Main area
    st.markdown("# Dashboard")
    
    # Add client
    st.markdown("### Add Client")
    with st.expander("Add new client", expanded=False):
        new_client_name = st.text_input("Client Name")
        if st.button("Add Client"):
            try:
                create_client(firm_id, new_client_name)
                st.success(f"Client '{new_client_name}' added successfully.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    
    st.markdown("---")
    
    # Clients table
    st.markdown("### Your Clients")
    
    if not clients:
        st.info("No clients yet. Add your first client above.")
    else:
        # Build table data
        table_data = []
        for client in clients:
            report_count = get_client_report_count(firm_id, client["client_id"])
            last_report_date = get_client_last_report_date(firm_id, client["client_id"])
            risk_trend = compute_client_risk_trend(firm_id, client["client_id"])
            
            table_data.append({
                "Client": client["client_name"],
                "Date Added": client["created_at"][:10],
                "Reports": report_count,
                "Last Report": last_report_date[:10] if last_report_date else "—",
                "Risk Trend": risk_trend,
            })
        
        # Display table
        st.dataframe(table_data, use_container_width=True)
        
        # Click to navigate to client detail
        st.markdown("*Click a client name in the sidebar to view their reports.*")
