"""
About page - explains what Kaizen Lite does, why it's needed, and its importance.
"""
import streamlit as st


def render():
    """Render the about page."""
    
    st.markdown("# About Kaizen Lite")
    
    st.markdown("---")
    
    # What is Kaizen Lite
    st.markdown("## What is Kaizen Lite?")
    
    st.markdown("""
    Kaizen Lite is a **financial health audit tool** designed specifically for Chartered Accountant (CA) firms. 
    It automates the analysis of client ledger exports to provide actionable insights that would otherwise 
    require hours of manual review.
    
    **In simple terms:** Upload your client's sales/ledger data, and within minutes get a comprehensive report 
    highlighting risks, trends, and areas that need attention — complete with period-over-period comparisons 
    showing what's changed since your last review.
    """)
    
    st.markdown("---")
    
    # Why is it needed
    st.markdown("## Why is this needed?")
    
    st.markdown("""
    ### The Problem CA Firms Face
    
    CA firms manage dozens or hundreds of clients. Each client generates financial data — sales ledgers, 
    receivables reports, transaction histories. Reviewing this data manually to identify risks and trends is:
    
    - **Time-consuming**: A thorough review of a single client's ledger can take hours
    - **Error-prone**: Manual analysis misses subtle patterns and trends
    - **Inconsistent**: Different reviewers focus on different metrics
    - **Reactive**: Problems are often discovered after they've become serious
    - **Scalability bottleneck**: As client count grows, review quality suffers
    
    ### The Gap
    
    Most CA firms have two extremes:
    1. **No review at all** — Just file the returns, move to the next client
    2. **Deep manual review** — Only possible for a few high-value clients
    
    There's no middle ground for **consistent, automated, value-add reviews** for every client.
    """)
    
    st.markdown("---")
    
    # Why it's important
    st.markdown("## Why is this important?")
    
    st.markdown("""
    ### For CA Firms
    
    **Value-Add Service**
    - Move beyond compliance work to advisory services
    - Proactively identify client issues before they become crises
    - Differentiate your practice from competitors
    
    **Efficiency**
    - Reduce review time from hours to minutes
    - Standardize analysis across all clients
    - Scale your advisory capacity without hiring
    
    **Risk Management**
    - Identify churn-risk clients early
    - Spot concentration risks before they impact revenue
    - Flag receivables issues affecting cash flow
    
    ### For Your Clients
    
    **Financial Visibility**
    - Understand their business health beyond just tax compliance
    - See trends over time (not just snapshots)
    - Get actionable insights, not just data dumps
    
    **Proactive Problem Solving**
    - Address issues before they become serious
    - Make informed business decisions
    - Improve cash flow and profitability
    
    **Peace of Mind**
    - Know their CA is watching their back
    - Get regular check-ins without scheduling meetings
    - Feel supported, not just serviced
    """)
    
    st.markdown("---")
    
    # What it catches
    st.markdown("## What does Kaizen Lite catch?")
    
    st.markdown("""
    ### 1. Receivables Risk
    - Customers with overdue payments
    - Aging analysis of outstanding amounts
    - Cash flow impact of slow payers
    
    ### 2. Customer Concentration Risk
    - Revenue dependency on single customers
    - HHI (Herfindahl-Hirschman Index) calculation
    - Warning when concentration is unhealthy
    
    ### 3. Revenue Stability
    - Revenue volatility over time
    - Seasonality detection
    - Trend analysis (growing, stable, declining)
    
    ### 4. Margin Analysis
    - Gross margin trends
    - Product-level profitability
    - Margin erosion detection
    
    ### 5. Churn & Quiet Accounts
    - Customers reducing purchase frequency
    - Accounts going silent before churn
    - Early warning for customer retention
    
    ### 6. Period-over-Period Deltas
    - What's worsened since last review
    - What's improved since last review
    - Plain-language explanations of changes
    """)
    
    st.markdown("---")
    
    # How it works
    st.markdown("## How it works?")
    
    st.markdown("""
    1. **Upload** — Export your client's sales/ledger data (Tally, Excel, CSV)
    2. **Auto-Detect** — Kaizen Lite automatically identifies relevant columns
    3. **Analyze** — Run comprehensive financial health analysis
    4. **Compare** — Compare with previous reports (if available)
    5. **Report** — Get a white-labeled PDF with findings and action items
    6. **Track** — All reports saved for historical comparison
    
    **Time required:** 5-10 minutes per client
    **Technical knowledge:** None — upload and go
    """)
    
    st.markdown("---")
    
    # What it's not
    st.markdown("## What this is NOT")
    
    st.markdown("""
    Kaizen Lite is **not**:
    
    - ❌ A bookkeeping or accounting software
    - ❌ A tax filing or compliance tool
    - ❌ A replacement for your existing systems
    - ❌ A live data integration platform
    - ❌ A general-purpose business intelligence tool
    
    Kaizen Lite **is**:
    
    - ✅ A periodic audit tool for financial health
    - ✅ An automated review layer on top of existing data
    - ✅ A value-add service for CA firms
    - ✅ A way to scale advisory capacity
    - ✅ A tool for proactive client management
    """)
    
    st.markdown("---")
    
    # Target audience
    st.markdown("## Who is this for?")
    
    st.markdown("""
    **Primary Users:**
    - CA firms managing multiple clients
    - Practicing CAs looking to add advisory services
    - Firms wanting to scale client review capacity
    
    **Ideal Client Size:**
    - SMBs with ₹10L - ₹50L annual revenue
    - Businesses with 50-500 customers
    - Companies with transaction volume suitable for ledger analysis
    
    **Not ideal for:**
    - Very small businesses (minimal transaction data)
    - Large enterprises (require custom solutions)
    - Non-distributor business models
    """)
    
    st.markdown("---")
    
    # Data privacy
    st.markdown("## Data Privacy & Security")
    
    st.markdown("""
    - **Tenant Isolation**: Each firm's data is completely isolated
    - **No Data Sharing**: Your client data is never shared with other firms
    - **Secure Storage**: All data stored in encrypted cloud storage
    - **Access Control**: Only authenticated users can access their data
    - **No Training on Your Data**: Analysis is done in-process, no data leaves your control
    """)
    
    st.markdown("---")
    
    # Getting started
    st.markdown("## Getting Started")
    
    st.markdown("""
    1. **Contact us** to request access
    2. **Receive credentials** for your firm account
    3. **Log in** and add your first client
    4. **Upload** a ledger export
    5. **Review** the generated report
    6. **Share** insights with your client
    
    For deployment information, see the [README](README.md).
    """)
    
    st.markdown("---")
    
    # Contact
    st.markdown("## Questions?")
    
    st.info("""
    If you have questions about Kaizen Lite, deployment, or how it can help your practice, 
    contact the Kaizen Lite team.
    """)
