
"""Supabase accessors that return app-shaped invoice, contract, and doc records.

Invoice and contract fields come from relational columns. Line items and usage
events are fetched from their linked tables and assembled into response records.
"""
import os
import pathlib

BASE = pathlib.Path(__file__).parent

_supabase = None

def load_environment():
    """Load simple KEY=VALUE entries from the project-local .env file."""
    env_path = BASE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


load_environment()

def get_supabase():
    """Return the configured server-side Supabase client or explain what's missing."""
    global _supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL is missing. Add it to the project .env file.")
    if not key:
        raise RuntimeError("SUPABASE_SECRET_KEY is missing. Add it to the project .env file.")
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(url, key)
    return _supabase

def get_stripe_invoice(invoice_id: str):
    """Load typed invoice fields and its linked lines in one request."""
    client = get_supabase()
    result = client.table("stripe_invoices").select(
        "id,metronome_contract_id,customer,status,amount,currency,subsidiary_currency,"
        "created_at,finalized_at,batch_scenario,error,expected_commit_coverage,"
        "stripe_invoice_lines(description,amount)"
    ).eq("id", invoice_id).limit(1).execute()
    if not result.data:
        return {"error": f"Invoice {invoice_id} not found", "id": invoice_id}

    invoice = result.data[0]
    invoice["lines"] = invoice.pop("stripe_invoice_lines", [])
    return invoice

def get_metronome_contract(contract_id: str):
    """Load typed contract fields and its linked events in one request."""
    client = get_supabase()
    result = client.table("metronome_contracts").select(
        "id,customer,status,billing_cycle,commit_amount,commit_consumed,commit_remaining,"
        "credit_balance,currency,stripe_currency,rated_usage_amount,rated_at,true_up_rule,"
        "tax_amount,tax_behavior,tax_rate,duplicate_event_count,duplicate_event_ids,note,"
        "metronome_contract_events(event_type,quantity,occurred_at)"
    ).eq("id", contract_id).limit(1).execute()
    if not result.data:
        return {"error": f"Contract {contract_id} not found", "id": contract_id}

    contract = result.data[0]
    contract["events"] = [
        {"type": event["event_type"], "quantity": event["quantity"], "timestamp": event["occurred_at"]}
        for event in contract.pop("metronome_contract_events", [])
    ]
    return contract

def get_docs():
    """Load runbook documents used by retrieval and evaluation."""
    client = get_supabase()
    result = client.table("docs").select("id,title,content,keywords").execute()
    return result.data
