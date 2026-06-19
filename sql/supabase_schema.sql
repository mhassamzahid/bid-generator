create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;

create table if not exists public.jobs (
    id uuid primary key default gen_random_uuid(),
    title varchar(500) not null,
    description text not null,
    budget varchar(200),
    skills jsonb,
    client_info jsonb,
    embedding vector(1024),
    created_at timestamptz not null default now()
);

create table if not exists public.bids (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs(id) on delete cascade,
    bid_text text not null,
    is_manual boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists jobs_created_at_idx
    on public.jobs (created_at desc);

create index if not exists bids_job_id_created_at_idx
    on public.bids (job_id, created_at desc);

create index if not exists jobs_embedding_cosine_idx
    on public.jobs
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100)
    where embedding is not null;
