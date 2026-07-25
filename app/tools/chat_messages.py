from app.services.supabase.factory import get_supabase_client


def add_chat_message(conversation_id: str, role: str, content: str) -> None:
    """Append one line to a conversation's clean transcript.

    role is "user" or "assistant". Called from the /chat endpoint after each
    turn — never from inside the graph, so the transcript stays free of ReAct
    plumbing (system prompts, tool calls, tool results).
    """
    if not content:
        return
    get_supabase_client().table("chat_messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }).execute()


def get_chat_messages(conversation_id: str, limit: int | None = None) -> list[dict]:
    """Return a conversation's transcript in chronological order.

    Pass a limit to fetch only the most recent messages (for short-term memory);
    omit it to fetch the whole thing (for the history view).
    """
    query = (
        get_supabase_client()
        .table("chat_messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=limit is not None)  # newest-first only when limiting
    )
    if limit is not None:
        query = query.limit(limit)
    rows = query.execute().data
    return list(reversed(rows)) if limit is not None else rows
