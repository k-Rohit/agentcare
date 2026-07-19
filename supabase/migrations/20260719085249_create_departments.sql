create table departments (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  active boolean not null default true
);
