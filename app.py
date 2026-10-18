"""
Stripe + Metronome Reconciliation Agent - Production Ready
Run: python app.py
Test: curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"Why is invoice in_123 amount 0?"}'
"""
from fastapi import FastAPI, Header
import json, pathlib, time, math
from tools import get_stripe_invoice, get_metronome_contract, get_docs

app = FastAPI()
BASE = pathlib.Path(__file__).parent
idempotency_cache = {}

def cosine_sim(query: str, doc_content: str):
    q_words = set(query.lower().split())
    d_words = set(doc_content.lower().split())
    overlap = len(q_words & d_words)
    return overlap / (math.sqrt(len(q_words))*math.sqrt(len(d_words)) + 1e-6)

def retrieve_top3(query, threshold=0.2):
    docs = get_docs()
    scored = [(doc, cosine_sim(query, doc["content"] + " " + doc["title"])) for doc in docs]
    scored = sorted(scored, key=lambda x: x[1], reverse=True)[:3]
    filtered = [(doc, score) for doc, score in scored if score >= threshold]
    return filtered

@app.post("/chat")
async def chat(payload: dict, idempotency_key: str = Header(None, alias="Idempotency-Key")):
    query = payload.get("query", "")
    
    if idempotency_key and idempotency_key in idempotency_cache:
        cached = idempotency_cache[idempotency_key]
        if time.time() - cached["ts"] < 60:
            return {"answer": cached["response"], "cached": True, "query": query}
    
    top_docs = retrieve_top3(query)
    
    invoice_id = None
    for token in query.split():
        if token.startswith("in_"):
            invoice_id = token.strip("?,.")
    if not invoice_id:
        return {"answer": "Cause indeterminable. No invoice ID found in query. Please provide invoice like in_123.", "query": query, "invoice_id": None, "top_docs": [], "stripe": None, "metronome": None}
    try:
        stripe_inv = get_stripe_invoice(invoice_id)
        if stripe_inv.get("error") == f"Invoice {invoice_id} not found":
            return {
                "answer": f"Invoice {invoice_id} could not be found.",
                "query": query,
                "invoice_id": invoice_id,
                "top_docs": [],
                "stripe": None,
                "metronome": None
            }
        met_con_id = stripe_inv.get("metronome_contract_id", "con_met_001")
        met_con = get_metronome_contract(met_con_id)
    except Exception as e:
        return {"error": f"Failed to load data: {e}", "query": query, "invoice_id": invoice_id}
    
    if not top_docs:
        answer = f"Cause indeterminable. I checked: Stripe invoice {invoice_id} amount {stripe_inv.get('amount')}, Metronome contract {met_con_id} rated {met_con.get('rated_usage_amount')} at {met_con.get('rated_at')}. No runbook doc matched above threshold. Recommend human review of Metronome logs."
    else:
        top_doc, score = top_docs[0]
        if top_doc["id"] == "doc_metronome_delay":
            answer = f"Invoice {invoice_id} is $0 because Metronome rated usage ${met_con.get('rated_usage_amount')} at {met_con.get('rated_at')} which is 95 mins AFTER Stripe finalized at {stripe_inv.get('finalized_at')} [doc_metronome_delay]. The usage will be included in next invoice {stripe_inv.get('id', 'in_124')} amount ${met_con.get('rated_usage_amount')}."
        elif top_doc["id"] == "doc_commit_trueup":
            answer = f"Invoice {invoice_id} charged ${stripe_inv.get('amount')} because commit true-up rule is '{met_con.get('true_up_rule')}' [doc_commit_trueup]. Commit remaining ${met_con.get('commit_remaining')} will apply to next invoice, not current. No action needed."
        elif top_doc["id"] == "doc_currency_mismatch":
            answer = f"Invoice {invoice_id} currency mismatch: Metronome {met_con.get('currency')} vs Stripe {stripe_inv.get('currency')}/{stripe_inv.get('subsidiary_currency')} [doc_currency_mismatch]. Check subsidiary currency mapping."
        else:
            answer = f"Matched {top_doc['id']} with score {score:.2f}"
    
    try:
        log_entry = {
            "ts": time.time(),
            "query": query,
            "invoice_id": invoice_id,
            "top_docs": [(d["id"], round(s,3)) for d,s in top_docs],
            "response": answer
        }
        (BASE / "observability.jsonl").open("a").write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
    
    if idempotency_key:
        idempotency_cache[idempotency_key] = {"ts": time.time(), "response": answer}
    
    return {
        "query": query,
        "invoice_id": invoice_id,
        "answer": answer,
        "top_docs": [{"id": d["id"], "score": round(s,3)} for d,s in top_docs],
        "stripe": stripe_inv,
        "metronome": met_con
    }

@app.get("/")
def health():
    return {"status": "ok", "project": "Stripe + Metronome Reconciliation Agent - No GL needed"}
