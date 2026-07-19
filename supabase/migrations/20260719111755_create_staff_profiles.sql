create table staff_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references profiles(id) on delete cascade,
    department_id uuid references departments(id) on delete set null,
    job_title text,
    employee_id text unique,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
