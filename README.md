# Stripe–Metronome Reconciliation Demo

A small FastAPI demo that reads invoice, contract, and runbook records from Supabase PostgreSQL. It ranks runbooks using word overlap and returns deterministic example explanations. It does not call live Stripe or Metronome APIs, use an LLM, or generate embeddings.

## How it works

1. `app.py` receives a question at `POST /chat` and finds an invoice ID.
2. `tools.py` loads the invoice and its linked lines, then the related contract and its usage events.
3. `retrieval.py` loads runbooks from Supabase and ranks them against the question.
4. `app.py` returns the records, runbook match scores, and an example explanation.

The database uses typed columns for invoice and contract fields. Invoice lines live in `stripe_invoice_lines`; usage events live in `metronome_contract_events`. Both are linked to their parent records. The original invoice and contract records are retained in `raw_payload`. Runbooks are stored in `docs`.

## Run locally

Use Python 3.9 or newer. Create a `.env` file in the project folder with the project URL and a server-side key:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SECRET_KEY=your-secret-key
```

Keep `.env` private; Git ignores it. Install dependencies and start the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/docs>, expand **POST /chat**, and try:

```json
{"query": "Why is invoice in_123 amount 0?"}
```

`GET /` is the health endpoint. Stop the server with **Ctrl+C**. `supabase-schema.sql` creates the tables for a new project; it does not populate sample data.

## Retrieval evaluation

With the virtual environment active, run:

```bash
python eval_harness.py
```

The four-case evaluation checks runbook ranking and citations using the same retrieval code as the API. It does not test the HTTP route or invoice and contract lookups.

## Project files

- `app.py` — API, response templates, short-lived idempotency cache, and best-effort request logging.
- `tools.py` — Supabase connection and record loading.
- `retrieval.py` — Shared runbook ranking.
- `eval_harness.py` — Four-case retrieval evaluation.
- `supabase-schema.sql` — Current database schema, including an unused pgvector column reserved for future work.
- `AGENTS.md` — Contributor and coding-agent guidance.

The idempotency cache is in memory and limited to the current process. `observability.jsonl` is a best-effort runtime log, not application data.
