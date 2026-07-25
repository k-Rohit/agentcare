-- A clean transcript of each conversation: exactly what the patient typed and
-- what the assistant replied. This is separate from the LangGraph checkpointer's
-- internal message channel (which holds ReAct plumbing — system prompts, tool
-- calls, tool results). It is the source of truth for the history view and for
-- the short-term memory fed back into the agents.
create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references workflow_runs(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

-- We always read a conversation's messages in chronological order.
create index if not exists idx_chat_messages_conversation
    on chat_messages (conversation_id, created_at);

alter table chat_messages enable row level security;
