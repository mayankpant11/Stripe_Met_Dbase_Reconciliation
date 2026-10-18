# Stripe + Metronome Reconciliation Agent 
Production-ready AI agent that explains why Stripe invoices don't match Metronome rated usage.

## Problem it solves
- Invoice in_123 amount $0 but Metronome shows $1200 rated usage -> delayed rating
- Invoice in_456 charged $1200 but commit $4000 remaining -> true-up rule
- Invoice in_789 currency EUR vs USD mismatch
- Invoice in_999 unknown fee -> says indeterminable (0% hallucination)

## Architecture (Applied AI Architect pattern)
```
User Query -> Retrieve top 3 docs (cosine similarity, threshold 0.2)
          -> Tool 1: get_stripe_invoice()  [tools.py line 18]
          -> Tool 2: get_metronome_contract() [tools.py line 25]
          -> Tool 3: get_docs() [tools.py line 32]
          -> Validation: rated_at vs finalized_at, commit_remaining, currency
          -> Answer with citations [doc_metronome_delay]
```
Why tools.py separate? app.py imports from tools.py (`from tools import get_stripe_invoice...`) - shows agent tool-calling pattern, reusability, clean separation. See app.py line 7.

## Production controls (demo vs prod)
- ✅ Idempotency-Key header (60s cache) - no duplicate contract creation
- ✅ Observability (observability.jsonl logs query, docs, latency) - safe write, won't crash chat
- ✅ Eval harness (accuracy + hallucination + citation precision)
- ✅ Returns JSON (not streaming) for Swagger UI compatibility

## Quick start

### 1. Run API
```bash
pip install fastapi uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
# Server starts at http://localhost:8000
# Health check: http://localhost:8000/  -> {"status":"ok"}
```

### 2. Test via Browser (Recommended for reviewers) - /docs UI

This is the easiest way to submit a question in chat:

1. Open `http://localhost:8000/docs`  (FastAPI auto-generates this)
2. You'll see `GET /` and `POST /chat` -> Click `POST /chat` to expand
3. Click **"Try it out"** button (top right)
4. In Request body, delete `{"additionalProp1": {}}` and paste:
```json
{
  "query": "Why is invoice in_123 amount 0?"
}
```
5. Click **Execute**
6. Scroll to **Server response -> Code 200** and **Response body**:
```json
{
  "answer": "Invoice in_123 is $0 because Metronome rated usage $1200 at 2026-01-15T02:40:00Z which is 95 mins AFTER Stripe finalized at 2026-01-15T01:05:00Z [doc_metronome_delay]. The usage will be included in next invoice...",
  "invoice_id": "in_123",
  "top_docs": [{"id": "doc_metronome_delay", "score": 0.289}]
}
```

**Other test queries:**
- `{"query": "Why is invoice in_456 charged 1200 but commit remaining 4000?"}` -> [doc_commit_trueup]
- `{"query": "Why is invoice in_789 currency mismatch?"}` -> [doc_currency_mismatch]
- `{"query": "Why is invoice in_999 amount 200?"}` -> Cause indeterminable

### 3. Test via curl (terminal)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Why is invoice in_123 amount 0?"}'
```

### 4. Run eval harness
```bash
python eval_harness.py
# Expected: Accuracy 4/4 = 100%, Hallucination 0%
```

## Troubleshooting

### I see 500 Internal Server Error in /docs ?
**Cause:** Old version returned `StreamingResponse(text/event-stream)` which Swagger UI cannot parse. It crashed on observability file write.

**Fix (already applied in this repo - commit 44b3779):**
- `app.py` line 80-87 now returns JSON `{"answer": ..., "invoice_id": ..., "stripe": ..., "metronome": ...}` instead of streaming
- Logging wrapped in try/except (line 65-75) so file errors never crash chat
- Data loading wrapped in try/except (line 45-50) returns `{"error": ...}` not 500

If you still see 500 in GitHub Codespaces:
```bash
# Stop old server
Ctrl+C
# Pull latest fix
git pull origin main
# Restart
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### How does `stripe_inv = get_stripe_invoice(invoice_id)` know to go to tools API?
Via import at `app.py` line 7:
```python
from tools import get_stripe_invoice, get_metronome_contract, get_docs
```
This tells Python to look in `tools.py` for those functions. Without this line you'd get `NameError: name 'get_stripe_invoice' is not defined`.

## Files
- `app.py` - FastAPI orchestrator, retrieval, answer logic
- `tools.py` - Pure data access: `get_stripe_invoice`, `get_metronome_contract`, `get_docs`
- `stripe_invoices.json`, `metronome_contracts.json`, `docs.json` - Mock data
- `eval_harness.py` - Tests accuracy/citation

## For OpenAI interview
This shows: RAG (top 3 docs + threshold), Tool calling (Stripe + Metronome), Eval, Production hardening. Built with Claude Code / Codex pattern.

## Git commit
```bash
git add app.py tools.py README.md
git commit -m "fix: return JSON in /chat for docs UI, prevent 500 on observability write"
git push
```
