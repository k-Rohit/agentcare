create table escalations (
    id uuid primary key default gen_random_uuid(),
    workflow_run_id uuid not null references workflow_runs(id) on delete cascade,
    reviewed_by uuid references profiles(id) on delete set null,
    reason text not null,
    status text not null default 'pending' check (status in ('pending', 'reviewed', 'resolved', 'rejected')),
    created_at timestamptz not null default now()
);
