"""
Client detail view - upload ledger, view results, download PDF, see history.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

from auth import get_firm_id, get_firm_name
from db import (
    get_client_by_id,
    get_scoped_reports,
    create_report,
    get_client_last_two_reports,
)
from analysis_engine import analyze_ledger, generate_pdf
from delta_computation import compute_deltas
from storage import upload_file, download_file, generate_pdf_key


def render():
    """Render the client detail view."""
    # Get client_id from session state or redirect
    client_id = st.session_state.get("selected_client_id")
    if not client_id:
        st.warning("Select a client from the sidebar to view their reports.")
        return
    
    firm_id = get_firm_id()
    client = get_client_by_id(client_id)
    
    if not client or client["firm_id"] != firm_id:
        st.error("Client not found or access denied.")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### {get_firm_name()}")
        st.markdown("---")
        if st.button("← Back to Dashboard"):
            st.session_state.pop("selected_client_id", None)
            st.rerun()
        st.markdown("---")
        st.markdown("[What is Kaizen Lite?](?view=about)")
        st.markdown("---")
        st.markdown(f"**Client:** {client['client_name']}")
    
    # Main area
    st.markdown(f"# {client['client_name']}")
    
    # Upload section
    st.markdown("## Upload Ledger")
    uploaded_file = st.file_uploader(
        "Upload client ledger (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        key=f"upload_{client_id}"
    )
    
    if uploaded_file:
        with st.spinner("Processing ledger..."):
            try:
                # Read file
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Run analysis
                firm_name = get_firm_name()
                analysis_result = analyze_ledger(df, firm_name)
                
                # Get previous report for deltas
                current, previous = get_client_last_two_reports(firm_id, client_id)
                
                # Compute deltas if previous exists
                deltas = []
                if previous:
                    previous_summary = json.loads(previous["summary_json"])
                    current_summary = analysis_result["summary"]
                    deltas = compute_deltas(current_summary, previous_summary)
                
                # Generate PDF (returns bytes)
                pdf_bytes = generate_pdf(analysis_result, "", firm_name)
                
                # Upload PDF to S3
                pdf_filename = f"report_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_key = generate_pdf_key(firm_id, client_id, pdf_filename)
                upload_file(pdf_bytes, pdf_key, content_type="application/pdf")
                
                # Save to database (store S3 key instead of local path)
                create_report(
                    client_id=client_id,
                    uploaded_filename=uploaded_file.name,
                    pdf_path=pdf_key,
                    summary_json=json.dumps(analysis_result["summary"])
                )
                
                st.success("Analysis complete!")
                st.rerun()
                
            except ValueError as e:
                st.error(f"Analysis failed: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
    
    st.markdown("---")
    
    # Show latest report results
    reports = get_scoped_reports(firm_id, client_id)
    
    if reports:
        latest_report = reports[0]
        latest_summary = json.loads(latest_report["summary_json"])
        
        st.markdown("## Latest Report")
        
        # Delta section (if not first report)
        if len(reports) > 1:
            previous_report = reports[1]
            previous_summary = json.loads(previous_report["summary_json"])
            deltas = compute_deltas(latest_summary, previous_summary)
            
            st.markdown("### What changed since last time")
            
            # Show worsened deltas prominently
            worsened = [d for d in deltas if d["direction"] == "worsened"]
            if worsened:
                st.error("⚠️ **Needs your attention:**")
                for delta in worsened[:3]:
                    st.markdown(f"- {delta['description']}")
            
            # Show improved deltas
            improved = [d for d in deltas if d["direction"] == "improved"]
            if improved:
                st.success("✓ **Improvements:**")
                for delta in improved[:3]:
                    st.markdown(f"- {delta['description']}")
            
            st.markdown("---")
        else:
            st.info("First report for this client — future uploads will show trends.")
            st.markdown("---")
        
        # Executive Summary
        st.markdown("### Executive Summary")
        # For now, show summary metrics
        st.json(latest_summary)
        
        st.markdown("---")
        
        # Download PDF button
        pdf_key = latest_report["pdf_path"]
        try:
            pdf_bytes = download_file(pdf_key)
            st.download_button(
                label="Download Report (PDF)",
                data=pdf_bytes,
                file_name=pdf_key.split("/")[-1],
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Could not download PDF: {str(e)}")
        
        st.markdown("---")
        
        # Report history
        st.markdown("## Report History")
        
        history_data = []
        for report in reports:
            summary = json.loads(report["summary_json"])
            history_data.append({
                "Date": report["generated_at"][:19].replace("T", " "),
                "File": report["uploaded_filename"],
                "Receivables Risk": summary.get("receivables_risk_score", "N/A"),
                "Concentration HHI": summary.get("concentration_hhi", "N/A"),
                "Revenue Stability": summary.get("revenue_stability_score", "N/A"),
                "Margin %": summary.get("margin_pct", "N/A"),
                "Download": report["pdf_path"],
            })
        
        st.dataframe(history_data, use_container_width=True)
        
        # Re-download from history
        st.markdown("### Re-download a previous report")
        report_to_download = st.selectbox(
            "Select report",
            options=reports,
            format_func=lambda r: f"{r['generated_at'][:19].replace('T', ' ')} - {r['uploaded_filename']}"
        )
        
        if report_to_download:
            pdf_key = report_to_download["pdf_path"]
            try:
                pdf_bytes = download_file(pdf_key)
                st.download_button(
                    label="Download Selected Report",
                    data=pdf_bytes,
                    file_name=pdf_key.split("/")[-1],
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Could not download PDF: {str(e)}")
    else:
        st.info("No reports yet. Upload a ledger to get started.")
