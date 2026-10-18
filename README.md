# Stripe–Metronome Reconciliation Demo

A small FastAPI demo that uses local JSON fixtures and a simple document-ranking method to explain possible differences between Stripe invoices and Metronome usage records. It does not connect to live Stripe or Metronome APIs, and its explanations are examples rather than production financial advice.

The repository currently includes 58 invoice records, 57 contract records, and 6 runbook documents. The examples cover delayed usage rating, commit true-ups, currency differences, credits, tax, duplicate usage events, and an unknown invoice fee.

## Repository

GitHub: [mayankpant11/Stripe_Met_Dbase_Reconciliation](https://github.com/mayankpant11/Stripe_Met_Dbase_Reconciliation)

## Project files

- `app.py` — FastAPI health and chat endpoints, simple retrieval, response generation, in-memory idempotency cache, and best-effort logging.
- `tools.py` — Loads the local JSON files and looks up invoices and contracts.
- `stripe-invoices.json` — Stripe-style sample invoices. The filename uses a hyphen; the loader also supports underscore variants.
- `metronome-contracts.json` — Metronome-style sample contracts.
- `docs.json` — Runbook documents used for retrieval.
- `eval_harness.py` — Small evaluation of four expected document-retrieval outcomes.
- `AGENTS.md` — Guidance for contributors and coding agents working in this repository.

## Run locally

Use Python 3.9 or newer. From this folder, create and activate a virtual environment, then install the two runtime packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn
```

Start the API:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Keep that terminal open. Visit <http://127.0.0.1:8000/docs> in a browser, expand `POST /chat`, choose **Try it out**, enter a request body, and choose **Execute**. The health endpoint is <http://127.0.0.1:8000/>. Stop the server with **Ctrl+C**.

Example request:

```json
{
  "query": "Why is invoice in_123 amount 0?"
}
```

You can also send the request from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Why is invoice in_123 amount 0?"}'
```

To see the missing-invoice response, try `{"query":"Why is invoice in_abc amount 0?"}`. The app checks the invoice lookup result before trying to load its contract.

## Run the retrieval evaluation

With the virtual environment activated:

```bash
python eval_harness.py
```

The current golden set has four cases. It checks which runbook document ranks first and whether the unknown-fee example remains indeterminable. It does not test the HTTP server or every fixture record.

## How the demo works

`POST /chat` extracts an invoice ID from the query, looks up the invoice and its linked contract, ranks up to three runbook documents using word overlap, and returns a JSON response. The special answer templates cover delayed rating, commit true-up, and currency mismatch. Other matched documents use a generic match response.

Unknown invoice IDs return a “could not be found” answer. This is important because a valid fixture such as `in_123` also has an `error` field describing its zero-amount condition; the app checks for the specific not-found message rather than treating every `error` field as a missing invoice.

The idempotency cache is in memory and lasts 60 seconds per running process. `observability.jsonl` is best-effort runtime logging; a logging write failure does not fail a chat request.
