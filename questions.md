# AgentCare — Auth & Access Notes (Q&A)

A self-test reference for the authentication/authorization design. Try answering before reading the explanation.

---

**Q: Why does `profiles.id` have the same value as `auth.users.id`, instead of its own generated UUID?**

`auth.users` (Supabase's own table) already uniquely identifies a person. Instead of inventing a second, separate ID and having to track "which profiles row maps to which auth row," `profiles.id` *is* that same ID, enforced by a foreign key. One ID per person, everywhere.

---

**Q: How does a `profiles` row actually get created when someone signs up?**

A Postgres trigger (`on_auth_user_created`) fires automatically after every insert into `auth.users`. It runs a function (`handle_new_user()`) that inserts a matching `profiles` row, copying the id/email and hardcoding `role = 'patient'`.

---

**Q: Why does that trigger function need `security definer`?**

The insert into `auth.users` happens inside Supabase's Auth service, which doesn't have permission to write into your `public.profiles` table. `security definer` makes the function run with the permissions of whoever *owns* the function, not whoever triggered it — so the insert is allowed regardless of who caused the trigger to fire.

---

**Q: If the trigger always hardcodes `role = 'patient'`, how does a doctor or staff account ever get a different role?**

It doesn't happen through the trigger at all. An already-authenticated admin action (backend code, using the service role key) creates the account via Supabase's admin API, then *explicitly* runs `update profiles set role = 'doctor'` and creates the matching `doctors`/`staff_profiles` row — a separate, privileged step that a public signup form has no path to reach.

---

**Q: Why can't a patient just sign up claiming `role = 'staff'`?**

Because the public signup endpoint's trigger never reads a `role` field from the client at all — it's hardcoded. There is no code path where a self-service signup can influence `profiles.role`.

---

**Q: If only an admin can create staff/doctor accounts, who creates the first admin?**

Nobody, through the app. It's a one-time bootstrap step done outside the normal flow (a seed script or a manual one-off action), not something the "admin-only" rule has an exception for.

---

**Q: Why does the backend's Supabase client use the `service_role` key instead of the `publishable` (anon) key?**

Because authorization in this app is enforced in Python backend code (`get_current_user`/`require_role`), not by database-level RLS policies. The service role key gives the backend full access so *your code* decides what's allowed — RLS is a second layer underneath, not the primary gate.

---

**Q: Every table has RLS enabled with no policies written yet. Doesn't that break the app?**

No — RLS-enabled-with-no-policies only locks out the `publishable` key (deny by default). The backend never uses that key for data access; it always uses `service_role`, which bypasses RLS entirely regardless of policies. The frontend only ever uses the publishable key for Supabase Auth itself (login/signup), never for querying tables directly.

---

**Q: There seem to be three keys floating around — publishable, anon, service_role, secret. What's the actual difference?**

Only two keys exist, not three or four — Supabase just renamed both of them at some point, so old and new names show up mixed together:

- `anon` and `publishable` are the *same key*, just renamed. This is the public-safe one — fine to expose in a browser. Its access is governed entirely by RLS (currently locked out of every table, since RLS is on with no policies). The only thing this project uses it for is Auth calls (signup/login) — those requests come from someone who isn't logged in yet, so there's no alternative.
- `service_role` and `secret` are the *same key*, also just renamed. This is the privileged one — full access, bypasses RLS entirely, must never appear anywhere a browser could see it. Every table query in this backend, and every Admin API call (`create_user`, `update_user_by_id`, etc.), uses this key exclusively.

The simple rule: anything simulating "what a browser/frontend would do" (every login/signup `curl` we've run) → publishable/anon. Anything that's "our backend doing something" → service_role/secret, always. The two never mix in this codebase.

---

**Q: Does `create_client(url, key)` actually connect to Supabase when it's called?**

No. It's a local, synchronous call that just builds a configured object (base URL + key stored as headers) — no network request happens. Proven by calling it against a completely unresolvable fake hostname: it returned instantly with no error. The first real network call happens later, the moment you call something like `.table(...).execute()`.

---

**Q: In `get_current_user`, why look up `role` from the `profiles` table instead of reading it out of the JWT?**

The JWT proves *identity* (who successfully logged in) — it doesn't carry your app's hospital-specific role. Even if it did, trusting a role embedded in a token the client possesses is exactly the kind of thing an attacker could try to tamper with. The database is the one source of truth for authorization; the token is only ever used to establish identity.

---

**Q: What's the practical difference between `get_current_user` failing and `require_role` failing?**

`get_current_user` failing means "I don't know who you are" → 401 Unauthorized (bad/missing/expired token, or no profile at all). `require_role` failing means "I know exactly who you are, and you're not allowed here" → 403 Forbidden (valid person, wrong role for this specific route).

---

**Q: Where does the actual RBAC enforcement happen — frontend or backend?**

Backend, exclusively. `require_role(...)` is a FastAPI dependency that runs *before* a route's own code, on the server, checking the database-backed role on every single request — regardless of what any frontend button does or doesn't show.

---

**Q: Why does `/register-doctor` return `{"user_id": ..., "temporary_password": ...}` in the response?**

Because of the account-creation flow we chose (admin sets a temp password, not an email invite), the response is the *only* place that password ever exists. It's never saved to `profiles`, never written to `audit_events`, never logged — so if it weren't returned here, it would vanish the instant the function finished, and the new doctor account would be permanently unusable (no password anyone knows, and no "forgot password" recovery built). The admin is expected to copy it once, from this response, and hand it off out of band — not store it anywhere themselves either. `user_id` is returned separately just so the caller knows which account was created.

---

## Python Imports & Running Modules

**Q: What's the actual difference between `python some/file.py` and `python -m some.dotted.path`?**

They're two completely different ways of telling Python where to find code, not two spellings of the same thing.

- `-m some.dotted.path` is a *mailing address*, written from one fixed reference point (your project root). Python starts at your current folder, then walks down through it using the dots as folder separators, expecting to find `some/dotted/path.py`. This only works if you run it *from the project root* — that's the fixed point the address assumes.
- `python some/file.py` hands Python one loose sheet of paper and says "just run this." Python opens that single file in isolation — it has no idea the file is part of a bigger package (`app`, with folders like `services`, `supabase` inside it). So any line in that file saying "import something from `app.xyz`" fails, because as far as this mode is concerned, there is no `app` — just the one file.

---

**Q: Why does `-m` use dots and no `.py`, while running a file directly uses slashes and `.py`?**

Because they're not the same kind of input. A file path (`app/services/supabase/factory.py`) describes a location on disk. A dotted module path (`app.services.supabase.factory`) describes a position in Python's *package* system — which happens to mirror the folder structure, but is resolved differently (by searching `sys.path`, matching folders that are packages), not by opening a literal disk path.

---

**Q: When can I use relative imports (`.` / `..`) and when can't I?**

Relative imports mean "relative to my own package location" — `.` = same folder, `..` = one folder up. They only make sense if Python already knows it's standing *inside* a package, which only happens when a file is reached via a real dotted address (`-m`, or by being imported by something else that was itself launched that way). If you try to run a file that uses `.`/`..` directly — even with `-m`, if it's the literal thing you're running as the entry point — Python often still resolves it fine when invoked correctly via `-m` from the root; but running it as a bare file path (`python some/file.py`) will fail immediately with "attempted relative import with no known parent package," no matter what directory you're standing in.

---

**Q: Why did `from config import get_settings` work from `client.py`, but the same style of unqualified import failed elsewhere?**

It only worked because `config.py` sits at the project root, and Python automatically adds the current working directory to its search path when you run something with `-m` from that same root. It was never a general solution — it happened to work for one specific file location (the root) and broke the moment a file lived somewhere else (e.g. three folders deep in `services/supabase/`). This is exactly why absolute imports (`from app.services.supabase.factory import ...`) are more robust than unqualified ones: they don't depend on which folder happens to be "current."

---

**Q: What's the one rule that avoids almost all of this confusion?**

Use full dotted imports everywhere (`from app.services.supabase.factory import ...`), never relative (`.`/`..`), for any file you might want to run directly. Always run things with `uv run python -m <dotted.path>` from the repo root — never a file path, never a `.py` extension on the command line.

---

## Tools, Data Shapes & Testing

**Q: What does `response.data` actually look like after a Supabase query?**

For a normal query (no `.single()`), it's a **list of dicts**, one per row, keys matching the columns you selected — an empty list `[]` if nothing matched, not `None`. `.single()` is different: it's a promise ("I'm certain exactly one row exists"), so it unwraps to one dict directly — but if that promise turns out wrong (zero rows), it doesn't return `None`, it **raises `APIError`** immediately. This actually broke real code once: `auth.py` had `if not profile.data:` after a `.single()` call, which could never run for the "no profile" case, since the exception fired before that line was ever reached. Fixed by wrapping the `.single()` call in `try/except APIError` instead of checking the result afterward.

---

**Q: In `get_available_slots`, why collect *all* doctor ids in a department instead of just one?**

A department can have multiple doctors. An earlier draft grabbed only `response.data[0]["id"]` (the first doctor found) and queried slots for just that one — silently making every other doctor's availability invisible. The fix: collect every active doctor's id into a list, then use `.in_("doctor_id", doctor_ids)` to fetch slots across all of them in one query.

---

**Q: In `book_appointment`, how does the code know which doctor to book — does it choose one?**

It never chooses — the doctor comes for free with whichever slot is picked, since every slot belongs to exactly one doctor already. An earlier draft tried `random.choice()` on what it thought was a list of doctors, but was actually a single doctor-id *string* — `random.choice()` on a string picks a random **character**, not a valid id at all. The fix: find the matching slot dict for the given `slot_id` in the already-fetched `available_slots` list, and read `doctor_id` straight off of it.

---

**Q: What actually stops two people from booking the same appointment slot at the same instant?**

A real database constraint, not application logic: `appointments.slot_id` has a `unique` constraint. If two bookings race, the second `insert` fails outright with `APIError` regardless of any "check if available" logic in Python — because a check-then-act pattern alone can't close that race window, only a DB-level guarantee can. `book_appointment` just needs to catch that failure cleanly, not prevent the race itself.

---

**Q: Why doesn't `book_appointment` set a start/end time on the appointment?**

Because `appointments` has no `start_time`/`end_time` columns at all — that data lives entirely on `appointment_slots`, found via `slot_id`. The slot's time gets fixed once, when the slot itself is created (`create_appointment_slot`, a doctor/staff action), never by the booking step.

---

**Q: What do `get_appointment_details`/`get_patient_appointments` return, given they show the doctor's name and slot time — where does that come from?**

PostgREST's relationship-embedding: `.select("id, status, doctors(name), appointment_slots(start_time, end_time)")` joins across the foreign keys in one query. Confirmed empirically that the embedded keys are the **table names** (`"doctors"`, `"appointment_slots"`), not singular aliases — e.g. `{"doctors": {"name": "Dr. Sharma"}, "appointment_slots": {"start_time": "...", "end_time": "..."}}`.

---

**Q: Is the overlap check in `create_appointment_slot` as airtight as the booking unique constraint?**

No, and that's a known, accepted limitation — it's a "look, then insert" check (query for overlapping slots, then insert if none found), which has a small race-condition window, unlike `book_appointment`'s unique-constraint backstop. A fully airtight version would need a Postgres `EXCLUDE` constraint on the time range. For a doctor/staff member manually adding one slot at a time, the practical risk is negligible — but it's not the same category of guarantee as the booking case.

---

**Q: Where do the actual document files get stored — is `file_path` the file itself?**

No, `file_path` is only a pointer. Actual file bytes live in **Supabase Storage**, in a private bucket (`patient-documents`, `public: false`, created via a migration so it's reproducible like everything else). `upload_document` puts the real bytes there and returns the storage path; `store_document` only ever saves that path as metadata. Viewing a file later requires `get_document_url`, which generates a temporary signed URL — there's no permanent public link, since the bucket is private.

---

**Q: Does the agent decide the `file_path` passed into `store_document`?**

No — it's mechanically produced by `upload_document` (`f"{patient_id}/{filename}"`) and just relayed forward. The two calls always happen together, in order: `upload_document` first (to get a real path pointing at real uploaded bytes), then `store_document` with that exact path. An agent-invented path with no matching upload would make `get_document_url` fail later with "file not found."

---

## Agent Architecture

**Q: If there are no subgraphs, how does the Coordinator "delegate to specialized agents, combine outputs, track completion/failure"?**

Each part is satisfied differently than a literal "coordinator manually calls each agent" pattern would suggest:
- **Delegates** — the graph's edges *are* the delegation, defined once when wiring the `StateGraph`; LangGraph's runtime invokes each node in sequence, not the Coordinator's own code.
- **Combines outputs** — automatic, because every node reads/writes the *same* shared state the whole time; nothing was ever separate, so there's nothing to combine after the fact.
- **Tracks completion/failure** — a `try/except` wrapped around the whole graph invocation at the call site (catches any node's failure), plus the conditional edges already built for Safety/Routing to route to "escalate" instead of continuing.

---

**Q: When do you actually need a LangGraph subgraph instead of a plain node function?**

Only when *one agent's own internal logic* needs real multi-step branching or an open-ended loop — not just "does more than one thing in sequence." Concretely: genuine ReAct-style looping (try a tool, evaluate, decide whether to retry, repeat an unknown number of times), needing a human-in-the-loop pause *inside* one agent's reasoning (not just between agents), reusing the same multi-step logic as a self-contained unit across different parent graphs, or an "agent" that's actually a small multi-agent system itself. None of AgentCare's six agents need this — each is one LLM call plus a couple of fixed tool calls, fully expressible as a plain function.

---

## Tool Calling — What the LLM Actually Does

**Q: Does the LLM execute the function when it "calls a tool"?**

No — it can't. An LLM is a text model with no interpreter, no database connection, no filesystem. What it actually does is *decide* and *emit a structured request*: "I want `escalate_request` called with `reason='...'`". That request (`response.tool_calls`) is not a call — nothing has run, nothing is in the database yet. Something else in your process has to read that request and actually run the function. The LLM's genuine job is the judgment (which tool, what arguments); the execution is always done by code, never the model.

---

**Q: Then why does my code have the line `escalate_request(**call["args"])` — isn't that me overriding the LLM?**

The opposite — it's *honoring* the LLM's decision. The LLM said "please call escalate_request with this reason"; that line is the code obeying it. Analogy: the LLM is a doctor writing a prescription (the decision), and this line is the nurse administering it (the execution). The doctor made the call; they just don't have hands in the pharmacy. `if call["name"] == "escalate_request"` means "the model chose escalation, so now run what it chose" — if it had chosen `RoutingDecision` instead, the other branch runs.

---

**Q: But in my MCP expense tracker, I just gave Claude instructions and it executed them — no manual code. How?**

The same two-party thing happened; the second half was just invisible. When you said "add a ₹500 expense," (1) Claude *decided* and emitted a tool-call request — and stopped there. (2) **Claude Desktop (the MCP host)** — a separate program — received that request and actually executed `create_expense` against your MCP server. (3) The result went back to Claude. (4) Claude wrote you a friendly confirmation. You only saw steps 1 and 4, so it felt direct — but the host was the "nurse" doing the execution. MCP is literally a protocol for that hand-off. In a hand-built LangChain/LangGraph app, *you* are the host, which is why you write the execution line yourself.

---

**Q: `ToolNode`, tool, function calling, tool calling — are these all different things?**

Two of them are the same; the rest are different layers:
- **function calling = tool calling** — identical, just renamed over time (OpenAI's old name vs. the current name). This is the *model's capability* to request a call instead of replying with plain text.
- **tool** — the actual function being called (e.g. `search_tool`, `escalate_request`). Just a function with a name/docstring/typed args so the model knows how to request it.
- **ToolNode** — one specific LangGraph class that *executes* the tool-call requests and loops results back. It's the pre-written "nurse." Runs in your process, not the model — it didn't move execution into the LLM, it just saved you from hand-writing the dispatch loop.
- **bind_tools** — the step that tells the model *which tools exist* ("here's the menu"). Doesn't execute anything, doesn't force a call.

In one line: `bind_tools` = here's the menu; tool calling = model orders off it; a tool = the dish ordered; `ToolNode` = the kitchen that actually makes it. The "executor" slot (ToolNode / hand-written dispatch / an MCP host) is interchangeable.

---

**Q: Why does `routing.py` dispatch tools manually instead of using `ToolNode`?**

Two reasons specific to routing. (1) `ToolNode`'s pattern is a *loop* — execute tool, feed result back to the LLM, keep reasoning (`tools → chat_node`). Routing isn't a loop; it makes one decision and the graph should then *branch differently* based on which tool was chosen (`escalate_request` → end as escalated; `RoutingDecision` → go to appointment) and map results into state fields like `department`/`delegated_to` — none of which `ToolNode` does. (2) `RoutingDecision` isn't an executable tool anyway — it has no side effect, it's structured output wearing a tool's clothes so the model can pick between "decide" and "escalate." `ToolNode` genuinely fits where there's a real ReAct loop with side-effecting tools whose results feed back — which is exactly what the Appointment Agent will be, so it belongs there, not here.

---

## Database

**Q: What is a database index, and why add one on `audit_events.workflow_run_id`?**

An index is like the index at the back of a textbook. Without it, to find every mention of "photosynthesis" you'd read all 800 pages; with it, you flip to the back, find the page numbers, and jump straight there. A database index is the same — without one, `select * from audit_events where workflow_run_id = X` makes Postgres do a **full table scan** (check every row); with an index it's a separate sorted structure (a B-tree) mapping `workflow_run_id` values → row locations, so the DB jumps straight to the matches. Fine to scan 50 rows, slow at 500,000.

Why here: the whole point of `workflow_run_id` on `audit_events` is to query "give me every step of this conversation" (`where workflow_run_id = X`), and `audit_events` is append-only so it grows forever — exactly where a full scan degrades. The index keeps that lookup fast regardless of size.

The trade-off (why not index everything): indexes cost extra storage and slightly slow down writes (every insert must also update the index). So you index the columns you frequently filter/join by, not all of them. Primary keys (like `id`) get an index automatically, which is why you don't add one for those.

---

## Agents vs. deterministic code (the recurring principle)

**Q: When should the LLM do something vs. plain Python?**

LLM only for **genuine judgment over open-ended language** (classify intent, pick a department from a description, decide book/reschedule/cancel, classify a document type). Plain Python for anything **mechanical or fixed** (booking a chosen slot, scheduling a reminder, sending an email, writing an audit row, formatting a confirmation). Rule of thumb: if the answer is always the same given the inputs, it's not a judgment — don't put an LLM on it. Wrapping deterministic steps in LLM calls just adds cost, latency, and a chance to hallucinate, for zero benefit.

---

**Q: Isn't logging/auditing something the LLM should do, since it's "doing the reasoning"?**

No — that's the trap. If audit logging were a *tool the LLM calls*, logging would depend on the model *remembering* to call it (unreliable), and it's not a reasoning decision anyway ("should I record that a booking happened? — always yes"). So audit/workflow updates are done by **deterministic Python that observes what the LLM did**. In the Appointment node that's the `appointment_finalize` node: it reads the tool results out of `messages` after the loop and logs the audit itself. LLM reasons; code bookkeeps.

---

**Q: Why is the Document node structured output, but the Appointment node a ToolNode ReAct loop?**

Because their shapes differ. Appointment genuinely *chooses among* actions (book/reschedule/cancel/status) and may loop → a real ReAct loop, so `ToolNode`. Document has exactly **one** judgment (what *type* is this file?) inside a **fixed** pipeline (upload → classify → store → check) → that's a single `with_structured_output` classification call, no loop, no ToolNode. Not every agent is a ReAct loop; match the machinery to whether there's actually iterative tool choice.

---

**Q: Why can't the Document agent upload the file itself?**

The LLM cannot handle raw file **bytes** — it can't receive or pass them as tool arguments. So the actual upload (`upload_document`, bytes → Supabase Storage) happens in the **UI**, which then passes the resulting `document_path` into the graph state. The Document node only ever deals with the *pointer* (`document_path`) + the classification — it records **metadata** (`store_document`), never the bytes. Bytes live at the UI/storage layer; metadata lives at the node/DB layer.

---

## Interrupts & the checkpointer

**Q: How does `interrupt()` pause and resume — one line behaving two ways?**

`choice = interrupt(payload)` runs differently across two invocations. **First run (pause):** it does NOT return — LangGraph saves the whole graph state to Postgres (the checkpointer) and *halts*; the code after it never runs, and `.invoke()` returns with a `"__interrupt__"` marker carrying the payload. **Second run (resume):** you call the graph again with `Command(resume=value)` on the **same `thread_id`**; LangGraph reloads the saved state, re-runs the paused node, and this time `interrupt()` *returns* `value`, so `choice = value` and execution continues. Requires a checkpointer (to save the pause) and a `thread_id` (to find it again). The pause and resume are the *same line* executed at two different moments, with Postgres holding everything in between.

---

**Q: Why does the reminder Follow-up node not send the email itself, 24h before?**

Because a graph node runs **once, synchronously**, at booking time — it can't "wait" until 24h before the appointment (which may be days away). So the node only **schedules**: it creates a `reminders` row with `scheduled_at = start − 24h`, status `pending`. A **separate background process** (`reminder_sender.py`, run on a cron/timer) is what actually acts later — it wakes up, finds reminders whose time has come, sends the email, marks them sent. Scheduling and sending are two different jobs, done by two different things. (And sending is deterministic — the email is a fixed template, not LLM-generated.)

---

## Identity: the two patient IDs

**Q: `profiles.id` vs `patient_profiles.id` — why do audit/FK bugs keep coming from this?**

A patient has **two** different ids: `profiles.id` (their *login identity*, = `auth.users.id` = `state["user_id"]`) and `patient_profiles.id` (the id of their *medical-record row*). Same person, two numbers, two purposes — like a passport number vs. a hospital chart number. `audit_events.actor_id` is a foreign key to `profiles(id)` ("who did this"), so it needs `state["user_id"]`; passing `patient_profiles.id` there fails the FK. Rule: "who is this person / who did this" → `state["user_id"]`; "which patient record / whose appointments" → `patient_profiles.id`.

---

## One conversation, one workflow id

**Q: Why is the checkpointer `thread_id` the conversation id, not `patient_id`?**

Goal: memory *within* a conversation, but a *fresh* conversation each new session. The checkpointer thread IS the memory store — keying it by `patient_id` would make one permanent memory blob per patient forever, so a returning user would resume old state (the opposite of "fresh each time"). Keying it by a per-conversation id (generated once per session, used as BOTH the `thread_id` and the `workflow_run.id`) gives memory within and fresh across. `patient_id` stays a *column* so you can still list a patient's past conversations (`workflow_runs where patient_id = X`). The Coordinator `get_or_create`s that one workflow_run so all steps of a conversation share it; every node's audit rows carry the same `workflow_run_id`.

---

## Type errors

**Q: Why so many red squiggles / type errors when the code runs fine?**

They're the editor's **static type checker** (Pylance/pyright), not runtime errors — Python doesn't enforce type hints at runtime, so none of them stop the app. Most come from `WorkflowState` fields typed `str | None` (they start None, get filled as the graph runs) being passed to functions wanting `str` — the checker can't *prove* they're set by then, even though they always are. Others come from loosely-typed Supabase `.data` and LangChain's flexible `config`/message args. Fix: set `"python.analysis.typeCheckingMode": "basic"` in `.vscode/settings.json` — it drops the "can't prove not-None" noise while still catching genuine mistakes (undefined names, real crashes). Type errors ≠ bugs; they're "the checker can't verify this."
