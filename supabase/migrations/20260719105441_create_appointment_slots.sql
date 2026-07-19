create table appointment_slots (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references doctors(id) on delete cascade,
    start_time timestamptz not null,
    end_time timestamptz not null,
    status text not null default 'available' check (status in ('available', 'booked', 'cancelled')),
    check (end_time > start_time)
);
