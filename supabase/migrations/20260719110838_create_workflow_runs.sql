create table workflow_runs (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patient_profiles(id) on delete cascade,
    current_step text not null default 'started',
    state jsonb not null default '{}'::jsonb,
    status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'failed', 'escalated')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
