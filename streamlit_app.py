"""AgentCare — visual demo frontend.

Drives the compiled agent graph (app/agents/graph.py) via .stream(), showing
each agent node's decision live, and handling the Appointment agent's slot
selection with a pause-and-resume.

Run:  uv run streamlit run streamlit_app.py
"""

import streamlit as st
from supabase import create_client

from config import get_settings
from app.agents.graph import agentcare_graph
from app.services.supabase.factory import get_supabase_client

st.set_page_config(page_title="AgentCare", page_icon=":material/local_hospital:", layout="centered")


@st.cache_resource
def auth_client():
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_publishable_key)


def get_reply(workflow_run_id: str) -> str | None:
    """Read the agent's final natural-language reply, stored on the workflow_run."""
    row = (
        get_supabase_client()
        .table("workflow_runs")
        .select("state")
        .eq("id", workflow_run_id)
        .single()
        .execute()
        .data
    )
    return (row.get("state") or {}).get("reply")


# ---------------------------------------------------------------- auth
def auth_view():
    st.title("AgentCare")
    st.caption("Your hospital administrative assistant.")

    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                try:
                    res = auth_client().auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state.user_id = res.user.id
                    st.session_state.email = email
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Login failed: {e}")

    with signup_tab:
        with st.form("signup"):
            name = st.text_input("Full name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_pw")
            if st.form_submit_button("Create account"):
                if not (name and email and password):
                    st.error("Please fill in name, email, and password.")
                else:
                    try:
                        res = auth_client().auth.sign_up({
                            "email": email,
                            "password": password,
                            "options": {"data": {"full_name": name}},
                        })
                        # role='patient' + name are set by the handle_new_user
                        # DB trigger, never by the client.
                        if res.session:
                            st.session_state.user_id = res.user.id
                            st.session_state.email = email
                            st.rerun()
                        else:
                            st.info(
                                "Account created. Please confirm your email, then log in. "
                                "(For the demo, an admin can disable email confirmation.)"
                            )
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Sign up failed: {e}")


# ---------------------------------------------------------------- graph run
def _render_step(node: str, update: dict, acc: dict):
    update = update or {}
    if node == "coordinator":
        st.write(f":material/travel_explore: **Coordinator** → hands off to *{acc.get('delegated_to')}*")
    elif node == "safety":
        status = update.get("status")
        if status == "blocked":
            st.write(":material/block: **Safety** → blocked (medical advice)")
        elif status == "escalated":
            st.write(":material/priority_high: **Safety** → escalated to a human")
        else:
            st.write(":material/verified: **Safety** → allowed")
    elif node == "routing":
        if update.get("status") == "escalated":
            st.write(":material/priority_high: **Routing** → no matching department, escalated")
        else:
            st.write(f":material/local_hospital: **Routing** → {acc.get('department')}")
    elif node == "appointment":
        if update.get("pending_options"):
            st.write(":material/event: **Appointment** → found open slots, awaiting your choice")
        elif acc.get("appointment_id"):
            st.write(":material/event_available: **Appointment** → booked")
        else:
            st.write(":material/event: **Appointment** → done")


def run_graph(state: dict) -> dict:
    """Stream the full graph, rendering each node as it completes. Returns the
    accumulated final state."""
    acc = dict(state)
    with st.status("Working through your request…", expanded=True) as status:
        for chunk in agentcare_graph.stream(state, stream_mode="updates"):
            for node, update in chunk.items():
                acc.update(update or {})
                _render_step(node, update, acc)
        status.update(label="Done", state="complete")
    return acc


def finish(final: dict):
    status = final.get("status")
    delegated = final.get("delegated_to")
    if status == "blocked":
        st.error(
            "I can't help with that — it's asking for medical advice. I can help "
            "with booking, documents, and appointment status."
        )
    elif status == "escalated":
        st.warning("This has been escalated to a staff member for review.")
    elif final.get("pending_options"):
        st.session_state.awaiting_slot = True
        st.session_state.pending_state = final
        st.session_state.pending_options = final["pending_options"]
        st.rerun()
    elif delegated == "escalate":
        st.info(
            "I couldn't match that to a booking, a document, or an appointment "
            "status check. Try rephrasing, e.g. 'book an appointment for …'."
        )
    elif delegated == "document":
        st.info("Document handling isn't wired up yet.")
    else:
        st.success(get_reply(final["workflow_run_id"]) or "Done.")


def new_state(raw_request: str) -> dict:
    return {
        "user_id": st.session_state.user_id,
        "patient_id": None,
        "workflow_run_id": None,
        "raw_request": raw_request,
        "department": None,
        "department_id": None,
        "slot_id": None,
        "appointment_id": None,
        "escalation_reason": None,
        "status": "in_progress",
        "delegated_to": None,
        "pending_options": None,
        "slot_choice": None,
    }


# ---------------------------------------------------------------- slot selection
def slot_selection_view():
    st.subheader("Choose a time")
    for opt in st.session_state.pending_options:
        if st.button(f"{opt['start']} → {opt['end']}", key=opt["slot_id"], width="stretch"):
            state = dict(st.session_state.pending_state)
            state["slot_choice"] = opt["slot_id"]
            final = run_graph(state)
            st.session_state.awaiting_slot = False
            st.session_state.pending_options = None
            st.session_state.pending_state = None
            st.success(get_reply(final["workflow_run_id"]) or "Booked!")


# ---------------------------------------------------------------- main
def main():
    if "user_id" not in st.session_state:
        auth_view()
        return

    with st.sidebar:
        st.header(":material/local_hospital: AgentCare")
        st.write(
            "An agentic assistant for hospital **administrative** tasks — "
            "booking, rescheduling, cancelling appointments, and coordinating "
            "documents. It does not give medical advice."
        )
        st.subheader("How it works")
        st.markdown(
            "Each request flows through specialised agents:\n"
            "- :material/travel_explore: **Coordinator** — understands intent\n"
            "- :material/verified: **Safety** — blocks medical advice, escalates emergencies\n"
            "- :material/local_hospital: **Routing** — picks the right department\n"
            "- :material/event: **Appointment** — finds slots, books, reschedules, cancels"
        )
        st.subheader("Try asking")
        st.markdown(
            "- *Book an appointment for my knee pain*\n"
            "- *I have a bad headache and want to see someone*\n"
            "- *Show my appointments*\n"
            "- *What medicine should I take?* (blocked)\n"
            "- *Chest pain, can't breathe* (escalated)"
        )
        st.divider()
        st.caption(f"Signed in as {st.session_state.email}")
        if st.button("Log out", width="stretch"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.title("AgentCare")
    st.caption("Describe what you need and watch the agents work.")

    if st.session_state.get("awaiting_slot"):
        slot_selection_view()
        return

    prompt = st.chat_input("What do you need? e.g. 'Book an appointment for my knee pain'")
    if prompt:
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            finish(run_graph(new_state(prompt)))


main()