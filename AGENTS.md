# AGENTS.md

## Project overview

`Stripe_Met_Dbase_Reconciliation` is a local-data FastAPI demo for explaining possible mismatches between Stripe-style invoices and Metronome-style usage contracts. It does not call live provider APIs. Retrieval is a small word-overlap cosine calculation over local runbook text, and answers are deterministic templates. Do not describe the project as a production integration or as using an LLM, embeddings, or live Stripe/Metronome APIs.

## Repository map

- `app.py` — FastAPI endpoints, query handling, retrieval, response templates, 60-second in-memory idempotency cache, and best-effort JSONL logging.
- `tools.py` — JSON file loading and invoice, contract, and documentation lookup helpers.
- `stripe-invoices.json` — 58 sample invoice records; the hyphenated filename is intentional and supported by the loader.
- `metronome-contracts.json` — 57 sample contract records.
- `docs.json` — 6 runbook documents. Each document has `id`, `title`, `content`, and `keywords` fields.
- `eval_harness.py` — Four-case retrieval/citation evaluation; it does not exercise the HTTP endpoint.
- `README.md` — Setup and usage instructions.

Invoice records link to contracts through `metronome_contract_id`. Keep IDs and customer references consistent when editing sample records. Preserve fields read by the response templates, including invoice `amount`, `currency`, `subsidiary_currency`, and `finalized_at`, plus contract `rated_usage_amount`, `rated_at`, `true_up_rule`, and `commit_remaining` where applicable.

## Local development

Run from the repository root. Create a virtual environment and install the runtime dependencies with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn
```

Start the API with:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Run the retrieval evaluation with:

```bash
python eval_harness.py
```

The API has `GET /` for health and `POST /chat` for chat. Keep responses JSON-compatible for FastAPI Swagger UI at `/docs`.

## Implementation guidance

- Keep data loading and lookup in `tools.py`; keep request orchestration and response generation in `app.py`.
- Resolve fixture paths relative to `pathlib.Path(__file__).parent`, not the current working directory.
- Preserve hyphen/underscore filename compatibility in `load_json`.
- When checking invoice lookup errors, compare against the specific not-found message, such as `Invoice {invoice_id} not found`. Do not check only whether the invoice dictionary has an `error` key: the valid `in_123` fixture uses that key to describe its zero-amount condition.
- The runbook IDs with dedicated response branches are `doc_metronome_delay`, `doc_commit_trueup`, and `doc_currency_mismatch`. Other matched documents currently receive a generic match response. Keep documentation and README claims aligned with that behavior.
- Keep logging best-effort so a failure to append to `observability.jsonl` does not fail a request. Do not treat that runtime log as fixture data.
- The idempotency cache is process-local and in-memory; it is not durable or shared between workers.

## Evaluation and fixture changes

- If retrieval behavior, thresholds, runbook content, or citation mappings change, update `GOLDEN_SET` in `eval_harness.py` when expected outcomes change.
- The harness checks four retrieval cases only. It does not verify the API route, logging, idempotency, concurrency, or every sample record.
- Keep JSON valid and use unique invoice, contract, and document IDs.
- Do not add credentials, environment files, local editor metadata, or runtime logs as fixture data.
