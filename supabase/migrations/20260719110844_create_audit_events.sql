create table audit_events (
    id uuid primary key default gen_random_uuid(),
    actor_id uuid references profiles(id) on delete set null,
    action text not null,
    entity_type text not null,
    entity_id uuid not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
