alter table audit_events
  add column workflow_run_id uuid references workflow_runs(id) on delete set null;

create index audit_events_workflow_run_id_idx on audit_events(workflow_run_id);