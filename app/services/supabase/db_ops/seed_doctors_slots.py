"""Seed synthetic doctors + appointment slots into the (production) database.

For every active department, tops up to DOCTORS_PER_DEPT doctors (real auth
accounts, provisioned the same way the admin flow does), and gives each newly
created doctor a set of open 30-minute slots over the next few days.

Idempotent: re-running only creates doctors for departments that are short,
and only adds slots for doctors it creates in this run.

Run:  uv run python -m app.services.supabase.db_ops.seed_doctors_slots
"""

from collections import Counter
from datetime import date, timedelta

from app.services.supabase.factory import get_supabase_client
from app.services.supabase.auth_ops import create_auth_account

DOCTORS_PER_DEPT = 2
SLOT_DAYS_AHEAD = 7  # how many upcoming days to open slots for
SLOT_TIMES = [  # (start_h, start_m, end_h, end_m)
    (10, 0, 10, 30),
    (10, 30, 11, 0),
    (11, 0, 11, 30),
    (14, 0, 14, 30),
]


def _upcoming_days() -> list[str]:
    """The next SLOT_DAYS_AHEAD calendar days, starting tomorrow (always future)."""
    today = date.today()
    return [(today + timedelta(days=i + 1)).isoformat() for i in range(SLOT_DAYS_AHEAD)]

DOCTOR_NAMES = [
    "Dr. Aarav Sharma", "Dr. Vivaan Reddy", "Dr. Aditya Nair", "Dr. Diya Mehta",
    "Dr. Ananya Iyer", "Dr. Kabir Singh", "Dr. Ishaan Rao", "Dr. Riya Kapoor",
    "Dr. Arjun Menon", "Dr. Saanvi Gupta", "Dr. Vihaan Joshi", "Dr. Aisha Khan",
    "Dr. Rohan Das", "Dr. Myra Pillai", "Dr. Kiara Bose", "Dr. Advait Kulkarni",
    "Dr. Anaya Verma", "Dr. Reyansh Shetty", "Dr. Sara Thomas", "Dr. Dhruv Malhotra",
    "Dr. Ira Chatterjee", "Dr. Krishna Menon", "Dr. Naina Sharma", "Dr. Yuvraj Sinha",
    "Dr. Zara Ahmed", "Dr. Aryan Bhat", "Dr. Kavya Nambiar", "Dr. Neel Desai",
    "Dr. Prisha Rao", "Dr. Veer Chauhan",
]


def _email_for(name: str) -> str:
    slug = name.lower().replace("dr. ", "").replace(" ", ".")
    return f"{slug}@agentcare.test"


def _make_slots(client, doctor_id: str) -> int:
    """Open upcoming slots for a doctor, skipping any start time already on file
    (so re-running just fills the gaps instead of duplicating)."""
    existing = {
        r["start_time"]
        for r in client.table("appointment_slots").select("start_time").eq("doctor_id", doctor_id).execute().data
    }
    rows = []
    for day in _upcoming_days():
        for sh, sm, eh, em in SLOT_TIMES:
            start = f"{day}T{sh:02d}:{sm:02d}:00+00:00"
            if start in existing:
                continue
            rows.append({
                "doctor_id": doctor_id,
                "start_time": start,
                "end_time": f"{day}T{eh:02d}:{em:02d}:00+00:00",
            })
    if rows:
        client.table("appointment_slots").insert(rows).execute()
    return len(rows)


def main() -> None:
    client = get_supabase_client()

    departments = client.table("departments").select("id, name").eq("active", True).execute().data
    existing = client.table("doctors").select("department_id").execute().data
    have = Counter(d["department_id"] for d in existing)

    name_iter = iter(DOCTOR_NAMES)
    created_doctors = 0
    created_slots = 0

    for dept in departments:
        needed = max(0, DOCTORS_PER_DEPT - have[dept["id"]])
        for _ in range(needed):
            name = next(name_iter, None)
            if name is None:
                print("Ran out of names — add more to DOCTOR_NAMES.")
                break
            email = _email_for(name)
            try:
                user_id, _ = create_auth_account(email, name)
            except Exception as e:  # noqa: BLE001 - e.g. email already exists; skip
                print(f"  skip {name} ({email}): {e}")
                continue

            client.table("profiles").update({"role": "doctor"}).eq("id", user_id).execute()
            doctor = client.table("doctors").insert({
                "user_id": user_id,
                "department_id": dept["id"],
                "name": name,
                "active": True,
            }).execute().data[0]

            created_doctors += 1
            print(f"  + {name} in {dept['name']}")

    # Open upcoming slots for EVERY active doctor (newly created + existing), so
    # re-running tops up next week's availability without duplicating.
    all_doctors = client.table("doctors").select("id, name").eq("active", True).execute().data
    for d in all_doctors:
        n = _make_slots(client, d["id"])
        created_slots += n
        if n:
            print(f"  ~ {d['name']}: +{n} upcoming slots")

    print(f"\nDone. Created {created_doctors} doctors; opened {created_slots} upcoming slots across {len(all_doctors)} doctors.")


if __name__ == "__main__":
    main()