create table patient_documents (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patient_profiles(id) on delete cascade,
    document_type text not null check (document_type in ('lab_report', 'ecg', 'imaging', 'prescription', 'discharge_summary', 'referral', 'other')),
    file_path text not null,
    document_date date,
    created_at timestamptz not null default now()
);
