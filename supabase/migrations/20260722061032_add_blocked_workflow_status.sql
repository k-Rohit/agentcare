alter table workflow_runs drop constraint workflow_runs_status_check;

alter table workflow_runs add constraint workflow_runs_status_check
  check (status in ('in_progress', 'completed', 'failed', 'escalated', 'blocked'));
