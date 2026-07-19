-- ============================================================
-- Local dev / demo seed data. Synthetic only — no real people.
-- Emails use the reserved .test TLD. Every seeded doctor/staff
-- account can log in with the password below (for demo/testing).
-- Run automatically by `supabase db reset`.
-- ============================================================

-- All seeded doctor/staff accounts use this password.
-- DEMO ONLY — never reuse a hardcoded password like this in production.
-- password: Password123!

-- ---------- Departments ----------
insert into departments (id, name, description, active) values
  ('d0000000-0000-0000-0000-000000000001', 'Cardiology', 'Heart and cardiovascular care', true),
  ('d0000000-0000-0000-0000-000000000002', 'Orthopedics', 'Bones, joints and muscles', true),
  ('d0000000-0000-0000-0000-000000000003', 'Dermatology', 'Skin, hair and nail care', true),
  ('d0000000-0000-0000-0000-000000000004', 'General Medicine', 'General checkups and common illnesses', true),
  ('d0000000-0000-0000-0000-000000000005', 'Pediatrics', 'Child healthcare', true);

-- ------------------------------------------------------------
-- Doctors
-- Each block: create a real auth.users + auth.identities row
-- (so the login actually works), which fires handle_new_user()
-- and creates a `profiles` row with role='patient' — then we
-- promote it to 'doctor' and add the doctors row, exactly like
-- an admin would do through the app.
-- ------------------------------------------------------------

-- Dr. Ananya Rao — Cardiology
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0000000-0000-0000-0000-000000000001',
  'authenticated', 'authenticated', 'doctor.rao@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Dr. Ananya Rao"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
  '{"sub":"a0000000-0000-0000-0000-000000000001","email":"doctor.rao@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'doctor' where id = 'a0000000-0000-0000-0000-000000000001';
insert into doctors (user_id, department_id, name, active) values
  ('a0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', 'Dr. Ananya Rao', true);

-- Dr. Vikram Sen — Orthopedics
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0000000-0000-0000-0000-000000000002',
  'authenticated', 'authenticated', 'doctor.sen@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Dr. Vikram Sen"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000002',
  '{"sub":"a0000000-0000-0000-0000-000000000002","email":"doctor.sen@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'doctor' where id = 'a0000000-0000-0000-0000-000000000002';
insert into doctors (user_id, department_id, name, active) values
  ('a0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000002', 'Dr. Vikram Sen', true);

-- Dr. Meera Iyer — Dermatology
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0000000-0000-0000-0000-000000000003',
  'authenticated', 'authenticated', 'doctor.iyer@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Dr. Meera Iyer"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000003',
  '{"sub":"a0000000-0000-0000-0000-000000000003","email":"doctor.iyer@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'doctor' where id = 'a0000000-0000-0000-0000-000000000003';
insert into doctors (user_id, department_id, name, active) values
  ('a0000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000003', 'Dr. Meera Iyer', true);

-- Dr. Farhan Khan — General Medicine
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0000000-0000-0000-0000-000000000004',
  'authenticated', 'authenticated', 'doctor.khan@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Dr. Farhan Khan"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000004',
  '{"sub":"a0000000-0000-0000-0000-000000000004","email":"doctor.khan@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'doctor' where id = 'a0000000-0000-0000-0000-000000000004';
insert into doctors (user_id, department_id, name, active) values
  ('a0000000-0000-0000-0000-000000000004', 'd0000000-0000-0000-0000-000000000004', 'Dr. Farhan Khan', true);

-- Dr. Priyanka Nair — Pediatrics
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0000000-0000-0000-0000-000000000005',
  'authenticated', 'authenticated', 'doctor.nair@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Dr. Priyanka Nair"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000005',
  '{"sub":"a0000000-0000-0000-0000-000000000005","email":"doctor.nair@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'doctor' where id = 'a0000000-0000-0000-0000-000000000005';
insert into doctors (user_id, department_id, name, active) values
  ('a0000000-0000-0000-0000-000000000005', 'd0000000-0000-0000-0000-000000000005', 'Dr. Priyanka Nair', true);

-- ------------------------------------------------------------
-- Staff (same auth pattern, promoted to 'staff' / 'admin' and
-- landing in staff_profiles instead of doctors)
-- ------------------------------------------------------------

-- Bootstrap admin — Rohit Kumar (oversees all departments, department_id left null)
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'b0000000-0000-0000-0000-000000000001',
  'authenticated', 'authenticated', 'admin@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Rohit Kumar"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'b0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001',
  '{"sub":"b0000000-0000-0000-0000-000000000001","email":"admin@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'admin' where id = 'b0000000-0000-0000-0000-000000000001';
insert into staff_profiles (user_id, department_id, job_title, employee_id) values
  ('b0000000-0000-0000-0000-000000000001', null, 'Hospital Administrator', 'EMP-0001');

-- Front-desk staff — Neha Verma, Cardiology
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'b0000000-0000-0000-0000-000000000002',
  'authenticated', 'authenticated', 'staff.verma@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Neha Verma"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'b0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002',
  '{"sub":"b0000000-0000-0000-0000-000000000002","email":"staff.verma@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'staff' where id = 'b0000000-0000-0000-0000-000000000002';
insert into staff_profiles (user_id, department_id, job_title, employee_id) values
  ('b0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000001', 'Front Desk Coordinator', 'EMP-0002');

-- Front-desk staff — Arjun Das, Orthopedics
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
  confirmation_token, email_change, email_change_token_new, recovery_token,
  created_at, updated_at
) values (
  '00000000-0000-0000-0000-000000000000',
  'b0000000-0000-0000-0000-000000000003',
  'authenticated', 'authenticated', 'staff.das@agentcare.test',
  extensions.crypt('Password123!', extensions.gen_salt('bf')),
  now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Arjun Das"}',
  '', '', '', '', now(), now()
);
insert into auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
values (gen_random_uuid(), 'b0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000003',
  '{"sub":"b0000000-0000-0000-0000-000000000003","email":"staff.das@agentcare.test"}', 'email', now(), now(), now());
update profiles set role = 'staff' where id = 'b0000000-0000-0000-0000-000000000003';
insert into staff_profiles (user_id, department_id, job_title, employee_id) values
  ('b0000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000002', 'Front Desk Coordinator', 'EMP-0003');
