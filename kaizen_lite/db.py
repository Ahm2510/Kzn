"""
PostgreSQL database helper for Kaizen Lite (Streamlit Cloud).
All queries are scoped by firm_id to ensure tenant isolation.
"""
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_connection_string():
    """Get PostgreSQL connection string from Streamlit secrets, forced onto the psycopg3 driver."""
    conn_str = st.secrets.get("database_url")
    if conn_str and conn_str.startswith("postgresql://"):
        conn_str = "postgresql+psycopg://" + conn_str[len("postgresql://"):]
    return conn_str


def get_engine():
    """Get SQLAlchemy engine."""
    conn_str = get_connection_string()
    if not conn_str:
        raise ValueError("DATABASE_URL not set in Streamlit secrets")
    return create_engine(conn_str)


def get_session():
    """Get a database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database tables if they don't exist."""
    engine = get_engine()
    
    # Firms table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firms (
                firm_id SERIAL PRIMARY KEY,
                firm_name TEXT NOT NULL,
                contact_email TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP NOT NULL,
                logo_path TEXT
            )
        """))
        conn.commit()
    
    # Clients table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id SERIAL PRIMARY KEY,
                firm_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE (firm_id, client_name),
                FOREIGN KEY (firm_id) REFERENCES firms(firm_id)
            )
        """))
        conn.commit()
    
    # Reports table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL,
                uploaded_filename TEXT NOT NULL,
                generated_at TIMESTAMP NOT NULL,
                pdf_path TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients(client_id)
            )
        """))
        conn.commit()


def get_firm_by_email(email: str) -> Optional[Dict]:
    """Look up a firm by contact email."""
    session = get_session()
    result = session.execute(text("SELECT * FROM firms WHERE contact_email = :email"), {"email": email}).fetchone()
    session.close()
    return dict(result._mapping) if result else None


def get_firm_by_id(firm_id: int) -> Optional[Dict]:
    """Look up a firm by firm_id."""
    session = get_session()
    result = session.execute(text("SELECT * FROM firms WHERE firm_id = :firm_id"), {"firm_id": firm_id}).fetchone()
    session.close()
    return dict(result._mapping) if result else None


def create_firm(firm_name: str, contact_email: str, logo_path: Optional[str] = None) -> int:
    """Create a new firm and return the firm_id."""
    session = get_session()
    result = session.execute(
        text("INSERT INTO firms (firm_name, contact_email, created_at, logo_path) VALUES (:firm_name, :contact_email, :created_at, :logo_path) RETURNING firm_id"),
        {"firm_name": firm_name, "contact_email": contact_email, "created_at": datetime.now(), "logo_path": logo_path}
    )
    firm_id = result.fetchone()[0]
    session.commit()
    session.close()
    return firm_id


def get_scoped_clients(firm_id: int) -> List[Dict]:
    """Get all clients for a specific firm (scoped query)."""
    session = get_session()
    results = session.execute(
        text("SELECT * FROM clients WHERE firm_id = :firm_id ORDER BY created_at DESC"),
        {"firm_id": firm_id}
    ).fetchall()
    session.close()
    return [dict(r._mapping) for r in results]


def create_client(firm_id: int, client_name: str) -> int:
    """Create a new client for a firm and return client_id."""
    session = get_session()
    try:
        result = session.execute(
            text("INSERT INTO clients (firm_id, client_name, created_at) VALUES (:firm_id, :client_name, :created_at) RETURNING client_id"),
            {"firm_id": firm_id, "client_name": client_name, "created_at": datetime.now()}
        )
        client_id = result.fetchone()[0]
        session.commit()
    except Exception as e:
        session.close()
        if "unique" in str(e).lower():
            raise ValueError(f"Client '{client_name}' already exists for this firm.")
        raise
    session.close()
    return client_id


def get_client_by_id(client_id: int) -> Optional[Dict]:
    """Get a client by ID."""
    session = get_session()
    result = session.execute(text("SELECT * FROM clients WHERE client_id = :client_id"), {"client_id": client_id}).fetchone()
    session.close()
    return dict(result._mapping) if result else None


def get_scoped_reports(firm_id: int, client_id: int) -> List[Dict]:
    """Get all reports for a specific client (scoped by firm_id)."""
    session = get_session()
    results = session.execute(text("""
        SELECT r.* FROM reports r
        JOIN clients c ON r.client_id = c.client_id
        WHERE c.firm_id = :firm_id AND r.client_id = :client_id
        ORDER BY r.generated_at DESC
    """), {"firm_id": firm_id, "client_id": client_id}).fetchall()
    session.close()
    return [dict(r._mapping) for r in results]


def create_report(
    client_id: int,
    uploaded_filename: str,
    pdf_path: str,
    summary_json: str
) -> int:
    """Create a new report and return report_id."""
    session = get_session()
    result = session.execute(
        text("INSERT INTO reports (client_id, uploaded_filename, generated_at, pdf_path, summary_json) VALUES (:client_id, :uploaded_filename, :generated_at, :pdf_path, :summary_json) RETURNING report_id"),
        {"client_id": client_id, "uploaded_filename": uploaded_filename, "generated_at": datetime.now(), "pdf_path": pdf_path, "summary_json": summary_json}
    )
    report_id = result.fetchone()[0]
    session.commit()
    session.close()
    return report_id


def get_report_by_id(report_id: int) -> Optional[Dict]:
    """Get a report by ID."""
    session = get_session()
    result = session.execute(text("SELECT * FROM reports WHERE report_id = :report_id"), {"report_id": report_id}).fetchone()
    session.close()
    return dict(result._mapping) if result else None


def get_client_report_count(firm_id: int, client_id: int) -> int:
    """Get the number of reports for a client (scoped)."""
    session = get_session()
    result = session.execute(text("""
        SELECT COUNT(*) as count FROM reports r
        JOIN clients c ON r.client_id = c.client_id
        WHERE c.firm_id = :firm_id AND r.client_id = :client_id
    """), {"firm_id": firm_id, "client_id": client_id}).fetchone()
    session.close()
    return result[0] if result else 0


def get_client_last_report_date(firm_id: int, client_id: int) -> Optional[str]:
    """Get the date of the most recent report for a client (scoped)."""
    session = get_session()
    result = session.execute(text("""
        SELECT generated_at FROM reports r
        JOIN clients c ON r.client_id = c.client_id
        WHERE c.firm_id = :firm_id AND r.client_id = :client_id
        ORDER BY r.generated_at DESC
        LIMIT 1
    """), {"firm_id": firm_id, "client_id": client_id}).fetchone()
    session.close()
    return str(result[0]) if result else None


def get_client_last_two_reports(firm_id: int, client_id: int) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Get the two most recent reports for a client (for delta computation)."""
    reports = get_scoped_reports(firm_id, client_id)
    if len(reports) >= 2:
        return reports[0], reports[1]  # Most recent, then previous
    elif len(reports) == 1:
        return reports[0], None
    return None, None


def get_all_firms() -> List[Dict]:
    """Get all firms (for admin use only)."""
    session = get_session()
    results = session.execute(text("SELECT * FROM firms ORDER BY created_at DESC")).fetchall()
    session.close()
    return [dict(r._mapping) for r in results]
