create table doctors (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references profiles(id) on delete cascade,
    department_id uuid not null references departments(id) on delete restrict,
    name text not null,
    active boolean not null default true
);