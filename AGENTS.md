# AGENTS.md

## Project overview

This repository is a small Python/FastAPI prototype for reconciling Stripe invoice data with Metronome contract data. It reads local JSON fixtures, ranks short runbook documents with a basic word-overlap cosine score, and returns a JSON explanation from the `/chat` endpoint. It does not call live Stripe or Metronome APIs and should not be described as a production integration.

## Repository map

- `app.py` — FastAPI application, `/` health route, `/chat` orchestration, document retrieval, response construction, idempotency cache, and best-effort JSONL logging.
- `tools.py` — JSON fixture loading and lookup helpers for invoices, contracts, and documentation.
- `eval_harness.py` — small golden-query retrieval/citation evaluation; run directly with Python.
- `stripe-invoices.json` — invoice fixtures (hyphenated filename is supported by `tools.load_json`).
- `metronome-contracts.json` — contract fixtures (hyphenated filename is supported by `tools.load_json`).
- `docs.json` — runbook documents used by retrieval.
- `README.md` — setup, API usage, examples, and project notes.

## Development and run commands

Install the runtime packages if they are not already available:

```bash
python -m pip install fastapi uvicorn
```

Start the API from the repository root:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Run the retrieval evaluation:

```bash
python eval_harness.py
```

The API provides `GET /` as a simple health check and `POST /chat` with a JSON body such as `{"query":"Why is invoice in_123 amount 0?"}`. FastAPI's interactive API page is available at `/docs` while the server is running.

## Code conventions and boundaries

- Keep fixture/data lookup in `tools.py`; keep request orchestration and response assembly in `app.py`.
- Resolve data files relative to `pathlib.Path(__file__).parent`, not the process working directory.
- Preserve the existing hyphen/underscore filename compatibility in `load_json` when changing fixture loading.
- Fixture records are plain JSON objects. Keep invoice and contract identifiers consistent across the fixture files and preserve the fields used by the response logic (`amount`, `finalized_at`, `currency`, `subsidiary_currency`, `metronome_contract_id`, `rated_usage_amount`, `rated_at`, `true_up_rule`, and `commit_remaining`).
- Retrieved documents need `id`, `title`, and `content`; answer branches in `app.py` currently use the document IDs `doc_metronome_delay`, `doc_commit_trueup`, and `doc_currency_mismatch`.
- Keep `/chat` responses JSON-compatible. The endpoint is used through FastAPI Swagger UI.
- Keep observability logging best-effort so a log-file write failure does not fail a chat request. The log is appended to `observability.jsonl` at runtime and is not a source fixture.
- The idempotency cache is in-memory and process-local with a 60-second lifetime. Do not represent it as durable or cross-worker idempotency.
- This code uses hand-written retrieval and deterministic response templates. Avoid implying it uses an LLM, embeddings, live provider APIs, or a general-purpose semantic search system unless those capabilities are implemented.

## Evaluation and changes

- When changing retrieval scoring, thresholds, document text, or the answer/citation mapping, update `GOLDEN_SET` in `eval_harness.py` when expected behavior changes.
- The eval harness checks top-document selection and whether unknown cases remain indeterminable. It does not exercise the FastAPI route, persistence, concurrency, or external integrations.
- Do not add dependencies or introduce a test framework without a concrete need; this repository currently has no dependency manifest or dedicated test suite.
- Do not commit runtime logs, local environment files, credentials, or generated artifacts as fixtures.
