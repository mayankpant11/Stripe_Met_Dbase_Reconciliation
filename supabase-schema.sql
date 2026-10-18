-- Current relational schema for the demo. Tables are created empty.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;

create table if not exists public.metronome_contracts (
    id text primary key,
    customer text,
    status text,
    billing_cycle text,
    commit_amount numeric,
    commit_consumed numeric,
    commit_remaining numeric,
    credit_balance numeric,
    currency text,
    stripe_currency text,
    rated_usage_amount numeric,
    rated_at timestamptz,
    true_up_rule text,
    tax_amount numeric,
    tax_behavior text,
    tax_rate numeric,
    duplicate_event_count integer,
    duplicate_event_ids text[] not null default '{}',
    note text,
    raw_payload jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists public.stripe_invoices (
    id text primary key,
    metronome_contract_id text references public.metronome_contracts(id),
    customer text,
    status text,
    amount numeric,
    currency text,
    subsidiary_currency text,
    created_at timestamptz,
    finalized_at timestamptz,
    batch_scenario text,
    error text,
    expected_commit_coverage numeric,
    raw_payload jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists public.stripe_invoice_lines (
    id bigint generated always as identity primary key,
    stripe_invoice_id text not null references public.stripe_invoices(id) on delete cascade,
    description text,
    amount numeric,
    raw_payload jsonb not null default '{}'::jsonb
);

create table if not exists public.metronome_contract_events (
    id bigint generated always as identity primary key,
    metronome_contract_id text not null references public.metronome_contracts(id) on delete cascade,
    event_type text,
    quantity numeric,
    occurred_at timestamptz,
    raw_payload jsonb not null default '{}'::jsonb
);

create index if not exists stripe_invoices_contract_id_idx
    on public.stripe_invoices(metronome_contract_id);
create index if not exists stripe_invoice_lines_invoice_id_idx
    on public.stripe_invoice_lines(stripe_invoice_id);
create index if not exists metronome_contract_events_contract_id_idx
    on public.metronome_contract_events(metronome_contract_id);

create table if not exists public.docs (
    id text primary key,
    title text not null,
    content text not null,
    keywords jsonb not null default '[]'::jsonb,
    embedding extensions.vector(384),
    updated_at timestamptz not null default now()
);

create index if not exists docs_embedding_hnsw_idx
    on public.docs using hnsw (embedding extensions.vector_cosine_ops)
    where embedding is not null;

alter table public.stripe_invoices enable row level security;
alter table public.stripe_invoice_lines enable row level security;
alter table public.metronome_contracts enable row level security;
alter table public.metronome_contract_events enable row level security;
alter table public.docs enable row level security;
