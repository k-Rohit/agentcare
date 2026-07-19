create table patient_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references profiles(id) on delete cascade,
    date_of_birth date,
    phone text,
    preferred_language text,
    emergency_contact text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
