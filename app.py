"""FastAPI demo that explains sample Stripe and Metronome record differences."""

import json
import pathlib
import time
from typing import Any, Optional

from fastapi import FastAPI, Header

from retrieval import retrieve_top3
from tools import get_metronome_contract, get_stripe_invoice

app = FastAPI(
    title="Stripe–Metronome Reconciliation Demo",
    description="Example reconciliation answers using Supabase records and runbooks.",
)
BASE = pathlib.Path(__file__).parent
IDEMPOTENCY_TTL_SECONDS = 60
MAX_IDEMPOTENCY_KEYS = 1_000
idempotency_cache: dict[str, dict[str, Any]] = {}


def _extract_invoice_id(query: str) -> Optional[str]:
    for token in query.split():
        if token.startswith("in_"):
            return token.strip("?,.")
    return None


def _build_answer(invoice_id: str, invoice: dict, contract: dict, docs: list) -> str:
    if not docs:
        return (
            f"Cause indeterminable. I checked: Stripe invoice {invoice_id} amount "
            f"{invoice.get('amount')}, Metronome contract {contract.get('id')} rated "
            f"{contract.get('rated_usage_amount')} at {contract.get('rated_at')}. "
            "No runbook doc matched above threshold. Recommend human review of "
            "Metronome logs."
        )

    doc, score = docs[0]
    if doc["id"] == "doc_metronome_delay":
        return (
            f"Invoice {invoice_id} is $0 because Metronome rated usage "
            f"${contract.get('rated_usage_amount')} at {contract.get('rated_at')} "
            f"which is 95 mins AFTER Stripe finalized at {invoice.get('finalized_at')} "
            f"[doc_metronome_delay]. The usage will be included in next invoice "
            f"{invoice.get('id', 'in_124')} amount "
            f"${contract.get('rated_usage_amount')}."
        )
    if doc["id"] == "doc_commit_trueup":
        return (
            f"Invoice {invoice_id} charged ${invoice.get('amount')} because commit "
            f"true-up rule is '{contract.get('true_up_rule')}' [doc_commit_trueup]. "
            f"Commit remaining ${contract.get('commit_remaining')} will apply to "
            "next invoice, not current. No action needed."
        )
    if doc["id"] == "doc_currency_mismatch":
        return (
            f"Invoice {invoice_id} currency mismatch: Metronome "
            f"{contract.get('currency')} vs Stripe "
            f"{invoice.get('currency')}/{invoice.get('subsidiary_currency')} "
            "[doc_currency_mismatch]. Check subsidiary currency mapping."
        )
    return f"Matched {doc['id']} with score {score:.2f}"


def _write_log(query: str, invoice_id: str, docs: list, answer: str) -> None:
    entry = {
        "ts": time.time(),
        "query": query,
        "invoice_id": invoice_id,
        "top_docs": [(doc["id"], round(score, 3)) for doc, score in docs],
        "response": answer,
    }
    try:
        with (BASE / "observability.jsonl").open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry) + "\n")
    except OSError:
        # Logging is best-effort and must not fail a chat request.
        pass


@app.post("/chat")
def chat(payload: dict, idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    query = str(payload.get("query") or "")
    now = time.monotonic()

    if idempotency_key:
        cached = idempotency_cache.get(idempotency_key)
        if cached and now - cached["ts"] < IDEMPOTENCY_TTL_SECONDS:
            return {"answer": cached["response"], "cached": True, "query": query}
        idempotency_cache.pop(idempotency_key, None)

    invoice_id = _extract_invoice_id(query)
    if not invoice_id:
        return {
            "answer": "Cause indeterminable. No invoice ID found in query. "
            "Please provide invoice like in_123.",
            "query": query,
            "invoice_id": None,
            "top_docs": [],
            "stripe": None,
            "metronome": None,
        }

    try:
        invoice = get_stripe_invoice(invoice_id)
        if invoice.get("error") == f"Invoice {invoice_id} not found":
            return {
                "answer": f"Invoice {invoice_id} could not be found.",
                "query": query,
                "invoice_id": invoice_id,
                "top_docs": [],
                "stripe": None,
                "metronome": None,
            }

        contract_id = invoice.get("metronome_contract_id", "con_met_001")
        contract = get_metronome_contract(contract_id)
        top_docs = retrieve_top3(query)
    except Exception as error:
        return {"error": f"Failed to load data: {error}", "query": query, "invoice_id": invoice_id}

    answer = _build_answer(invoice_id, invoice, contract, top_docs)
    _write_log(query, invoice_id, top_docs, answer)

    if idempotency_key:
        idempotency_cache[idempotency_key] = {
            "ts": time.monotonic(),
            "response": answer,
        }
        if len(idempotency_cache) > MAX_IDEMPOTENCY_KEYS:
            oldest_key = min(idempotency_cache, key=lambda key: idempotency_cache[key]["ts"])
            idempotency_cache.pop(oldest_key, None)

    return {
        "query": query,
        "invoice_id": invoice_id,
        "answer": answer,
        "top_docs": [{"id": doc["id"], "score": round(score, 3)} for doc, score in top_docs],
        "stripe": invoice,
        "metronome": contract,
    }


@app.get("/")
def health():
    return {"status": "ok", "project": "Stripe–Metronome Reconciliation Demo"}
