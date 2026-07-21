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
