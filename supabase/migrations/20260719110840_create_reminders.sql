create table reminders (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patient_profiles(id) on delete cascade,
    appointment_id uuid references appointments(id) on delete cascade,
    reminder_type text not null check (reminder_type in ('appointment', 'follow_up', 'document_pending')),
    scheduled_at timestamptz not null,
    status text not null default 'pending' check (status in ('pending', 'sent', 'cancelled'))
);
