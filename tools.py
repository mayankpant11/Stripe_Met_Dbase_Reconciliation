
import json, pathlib
BASE = pathlib.Path(__file__).parent

def load_json(name):
    # Try underscore, hyphen, and exact name for robustness
    candidates = [name, name.replace("_", "-"), name.replace("-", "_")]
    for cand in candidates:
        p = BASE / cand
        if p.exists():
            return json.loads(p.read_text())
    # Also try listing files case-insensitive
    for f in BASE.iterdir():
        if f.name.lower() == name.lower():
            return json.loads(f.read_text())
    raise FileNotFoundError(f"Could not find {name} (tried {candidates})")

def get_stripe_invoice(invoice_id: str):
    invoices = load_json("stripe_invoices.json")
    for inv in invoices:
        if inv["id"] == invoice_id:
            return inv
    return {"error": f"Invoice {invoice_id} not found", "id": invoice_id}

def get_metronome_contract(contract_id: str):
    contracts = load_json("metronome_contracts.json")
    for con in contracts:
        if con["id"] == contract_id:
            return con
    return {"error": f"Contract {contract_id} not found", "id": contract_id}

def get_docs():
    return load_json("docs.json")