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
