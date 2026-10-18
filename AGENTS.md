# Project guidance

## Overview

This is a small FastAPI demo backed by Supabase PostgreSQL. It uses sample Stripe-style invoices, Metronome-style contracts, and runbook documents. It does not call provider APIs, use an LLM, or generate embeddings. Retrieval uses word-overlap cosine scoring; answers use deterministic templates.

## Main files

- `app.py` — HTTP routes, request handling, response templates, idempotency, and best-effort logging.
- `tools.py` — Supabase configuration and invoice, contract, and runbook data access.
- `retrieval.py` — Shared runbook ranking for the API and evaluation harness.
- `eval_harness.py` — Four-case retrieval and citation evaluation.
- `supabase-schema.sql` — Database schema for a new project; tables are created empty.

## Data model and code boundaries

- Supabase is the only source for invoices, contracts, and runbooks. Do not add JSON fixture loading or fallback behavior.
- Invoice and contract fields use typed columns. Preserve the original invoice and contract record in `raw_payload`.
- Invoice lines belong in `stripe_invoice_lines`; contract usage events belong in `metronome_contract_events`. Keep their foreign keys linked to their parent rows.
- Keep Supabase access and row-to-response mapping in `tools.py`, retrieval in `retrieval.py`, and HTTP orchestration and answers in `app.py`.
- Preserve fields used by answer templates: invoice `amount`, `currency`, `subsidiary_currency`, and `finalized_at`; contract `rated_usage_amount`, `rated_at`, `true_up_rule`, and `commit_remaining`.
- Treat an invoice as missing only when its error equals `Invoice {invoice_id} not found`. A valid invoice may have another `error` value.
- Dedicated runbook response branches are `doc_metronome_delay`, `doc_commit_trueup`, and `doc_currency_mismatch`. Other matches use the generic response.

## Local operation

Use Python 3.9 or newer. Install dependencies with `python -m pip install -r requirements.txt`. Put `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the local `.env`; never commit or expose that file or key.

Start the API from the project root:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Run the retrieval evaluation with `python eval_harness.py`. It checks four retrieval cases only; it does not cover HTTP behavior or invoice and contract loading.

The idempotency cache is process-local, expires entries after 60 seconds, and is size-limited. Keep `observability.jsonl` logging best-effort; it is a runtime log, not application data.
