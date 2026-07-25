# The `/chat` Endpoint — How It Works

This document explains the full request flow of `POST /agentcare/api/v1/chat`, the
single endpoint that powers the whole patient conversation. It lives in
[`app/api/routes/requests.py`](../app/api/routes/requests.py).

---

## 1. What this endpoint is responsible for

`/chat` is the **only** endpoint the chat UI talks to. Every message the patient
sends — and every slot they pick — is one POST to `/chat`. On each call it does
exactly three things, in order:

1. **Run the agent graph** — either start a fresh run (`invoke`) or continue a
   paused one (`resume`).
2. **Translate** the graph's raw output into a clean response the UI understands
   (`_to_response`).
3. **Save** the turn to the conversation transcript (`add_chat_message`).

That's the whole job: **run → translate → save.**

---

## 2. The one fork that splits everything

A booking is a *two-step* conversation:

> type "book me with Cardio" → **pause** so the patient picks a slot → resume

So `/chat` has to handle two kinds of input, and it tells them apart with a
single check:

```python
if request.resume_value is not None:
    # RESUME — the patient answered a pause (e.g. clicked a slot button)
else:
    # FRESH — the patient typed a new message
```

- `resume_value` is set **only** when the patient clicks a slot. It carries the
  chosen `slot_id`.
- Everything else (typing a message, a suggestion chip) is a **fresh** message.

---

## 3. Key concepts

### `conversation_id`
A stable id for one conversation. It is used as **three things at once**:
- the LangGraph `thread_id` (so the checkpointer can pause/resume the run),
- the `workflow_runs.id` (the DB record of the run),
- the `conversation_id` on every `chat_messages` row.

For a brand-new conversation the frontend sends no id, so the endpoint mints one
with `uuid4()`.

### Two message stores (don't confuse them)

| | `messages` (in the graph) | `chat_messages` (the DB table) |
|---|---|---|
| Contains | ReAct plumbing: system prompts, tool calls, tool results | Clean transcript: only what the patient typed + what we replied |
| Managed by | LangGraph checkpointer | this endpoint (`add_chat_message`) |
| Reset each turn? | Yes (coordinator clears it) | No — it accumulates permanently |
| Used for | the agents' tool-calling loop | history view + short-term memory |

### `history` — short-term memory
Before running the graph on a fresh message, we load the last `HISTORY_LIMIT`
(10) lines of the transcript and pass them into the state as `history`. This is
what lets the agents understand follow-ups like *"cancel the second one"* or
*"what's the doctor's name?"*.

---

## 4. Path A — a fresh message

Triggered when `resume_value` is `None`.

```python
conversation_id = request.conversation_id or str(uuid4())          # 1
history = get_chat_messages(conversation_id, limit=HISTORY_LIMIT) \
          if request.conversation_id else []                        # 2
state = { ... "raw_request": request.message, "history": history, ... }  # 3
result = agentcare.invoke(state=state, thread_id=conversation_id)    # 4
response = _to_response(conversation_id, result)                     # 5
add_chat_message(conversation_id, "user", request.message)          # 6
assistant_line = response.get("reply") or response.get("department_message")
if assistant_line:
    add_chat_message(conversation_id, "assistant", assistant_line)   # 7
return response
```

1. Use the existing conversation id, or create a new one.
2. Load recent transcript as memory. **Empty** for a brand-new conversation
   (there's nothing yet, and no `workflow_run` row to reference).
3. Build the initial state — the patient's message plus blanks the agents fill in.
4. **Run the graph.** This walks coordinator → safety → routing → appointment, etc.
5. **Translate** the raw result (see §6).
6. Save the patient's message.
7. Save the assistant's line. Note the `or`: when a booking **pauses** for slot
   selection, there is no final `reply` yet — but there *is* the routing
   announcement (`department_message`, e.g. *"let's find you an opening in
   Cardiology"*), so we save that instead.

> **Ordering gotcha:** the transcript is saved *after* `invoke`, never before.
> `chat_messages.conversation_id` is a foreign key to `workflow_runs`, and that
> row isn't created until the coordinator runs *inside* `invoke`. Saving first
> would violate the FK on a brand-new conversation.

---

## 5. Path B — a resume (slot pick)

Triggered when `resume_value` is set.

```python
if not request.conversation_id:
    raise HTTPException(400, "conversation_id is required to resume")
result = agentcare.resume(request.resume_value, request.conversation_id)  # 1
response = _to_response(request.conversation_id, result)                  # 2
if request.resume_label:
    add_chat_message(request.conversation_id, "user", request.resume_label)  # 3
if response["reply"]:
    add_chat_message(request.conversation_id, "assistant", response["reply"])  # 4
return response
```

1. **Continue the same paused graph** from where it interrupted, feeding in the
   chosen `slot_id`. The appointment agent now books it.
2. Translate — this time the run finishes, so `status="completed"` with a reply.
3. Save the patient's choice as a user line. The frontend sends `resume_label`
   (a human-readable version like *"Friday, Jul 24, 3:30 PM"*) because the
   backend only receives the raw `slot_id`, which isn't nice to display.
4. Save the confirmation reply.

---

## 6. The helpers

### `_to_response(conversation_id, result)`
The graph returns a raw state dict. This normalizes it into one of **four**
shapes the UI knows how to render:

| Situation | Detected by | Response `status` | Extra fields |
|---|---|---|---|
| Paused for slot pick | `"__interrupt__" in result` | `awaiting_input` | `interrupt` (slots), `department`, `department_message` |
| Medical-advice request | `result["status"] == "blocked"` | `blocked` | static refusal `reply` |
| Emergency / out of scope | `result["status"] == "escalated"` | `escalated` | static escalation `reply` |
| Anything else | (default) | `completed` | `reply` from `_reply(...)` |

### `_reply(messages)`
For a completed turn, joins **every** assistant line produced that turn:

```python
parts = [m.content for m in messages
         if isinstance(m, AIMessage) and m.content and not m.tool_calls]
return "\n\n".join(parts) if parts else None
```

This is why a booking shows **both** the confirmation (doctor + time) **and** the
reminder note — not just the last one. It filters out tool-call messages (empty
content) and tool results.

---

## 7. Full booking, end-to-end

| # | Patient action | Path | Graph call | Saved to transcript |
|---|---|---|---|---|
| 1 | types "book me with Cardio" | A | `invoke` → **pauses** | user: *"book me with Cardio"* · assistant: *"let's find you an opening in Cardiology"* |
| 2 | clicks "Fri 3:30 PM" | B | `resume` → **books** | user: *"Friday, Jul 24, 3:30 PM"* · assistant: *"Booked with Dr… + reminder set"* |
| 3 | reloads the page | — | — | all 4 lines replay from `chat_messages` |

---

## 8. What replays on reload — and what doesn't

On reload, the frontend restores the active `conversation_id` (from
`localStorage`) and calls `GET /conversations/{id}/messages`, which returns the
`chat_messages` transcript.

**Replays:** the patient's message, the routing announcement, the picked slot
label, the booking confirmation + reminder — i.e. all the *text*.

**Does not replay:** the interactive **slot picker** itself. Those are live
buttons for a choice already made (and the slots are now booked), so there's
nothing meaningful to click. Only its text outcome is preserved.

---

## 9. Related files

| File | Role |
|---|---|
| [`app/api/routes/requests.py`](../app/api/routes/requests.py) | this endpoint |
| [`app/tools/chat_messages.py`](../app/tools/chat_messages.py) | `add_chat_message` / `get_chat_messages` |
| [`app/agents/graph.py`](../app/agents/graph.py) | `agentcare.invoke` / `agentcare.resume` |
| [`app/api/routes/patient.py`](../app/api/routes/patient.py) | `GET /conversations/{id}/messages` (reload) |
| [`app/schemas/requests.py`](../app/schemas/requests.py) | `SubmitRequest` (incl. `resume_value`, `resume_label`) |
