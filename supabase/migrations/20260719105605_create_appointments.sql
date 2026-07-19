create table appointments (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patient_profiles(id) on delete cascade,
    doctor_id uuid not null references doctors(id) on delete restrict,
    slot_id uuid not null unique references appointment_slots(id) on delete restrict,
    status text not null default 'pending' check (status in ('pending', 'confirmed', 'cancelled', 'completed', 'rescheduled')),
    reason text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
