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
