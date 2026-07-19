create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  name text,
  email text not null,
  role text not null default 'patient',
  created_at timestamptz not null default now()
);

create function public.handle_new_user()
returns trigger 
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, name, role)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name', 'patient');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
