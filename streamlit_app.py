"""AgentCare — visual demo frontend.

Runs the agent pipeline (Coordinator → Safety → Routing → Appointment) step by
step, showing each agent's decision and the tools it calls live, and streaming
the appointment agent's slot selection with an interrupt for the patient to pick.

Run:  uv run streamlit run streamlit_app.py
"""

import streamlit as st
from supabase import create_client

from config import get_settings
from app.agents.coordinator import coordinator_node
from app.agents.safety import safety_node
from app.agents.routing import routing_node
from app.agents.appointment import appointment_graph
from app.agents.prompts import APPOINTMENT_AGENT_PROMPT
from langgraph.types import Command

st.set_page_config(page_title="AgentCare", page_icon="🏥", layout="centered")


@st.cache_resource
def auth_client():
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_publishable_key)


# ---------------------------------------------------------------- auth
def login_view():
    st.title("🏥 AgentCare")
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
                        # role='patient' + name are set automatically by the
                        # handle_new_user DB trigger — never by the client.
                        if res.session:
                            st.session_state.user_id = res.user.id
                            st.session_state.email = email
                            st.rerun()
                        else:
                            st.info(
                                "Account created. Please check your email to confirm "
                                "it, then log in. (For local/demo, ask an admin to "
                                "disable email confirmation.)"
                            )
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Sign up failed: {e}")


# ---------------------------------------------------------------- appointment stage
def run_appointment(state: dict, resume_choice: str | None = None):
    """Drive the appointment ReAct graph, showing tool calls live. Returns the
    interrupt options (list) if it paused for a slot choice, else None."""
    cfg = {"configurable": {"thread_id": state["workflow_run_id"]}}
    if resume_choice is not None:
        stream_input = Command(resume=resume_choice)
    else:
        context = (
            f"patient_id: {state['patient_id']}\n"
            f"department_id: {state['department_id']}\n"
            f"Patient request: {state['raw_request']}"
        )
        stream_input = {"messages": [("system", APPOINTMENT_AGENT_PROMPT), ("human", context)]}

    pending_options = None
    for chunk in appointment_graph.stream(stream_input, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            pending_options = chunk["__interrupt__"][0].value.get("options", [])
            st.write("⏸️ Waiting for you to choose a slot…")
            continue
        for node, update in chunk.items():
            if node == "agent":
                msg = update["messages"][-1]
                for tc in getattr(msg, "tool_calls", []) or []:
                    st.write(f"🔧 calling `{tc['name']}`")
                if getattr(msg, "content", None) and not getattr(msg, "tool_calls", None):
                    st.session_state.last_reply = msg.content
            elif node == "tools":
                for m in update["messages"]:
                    st.write(f"↳ `{m.name}` returned")
    return pending_options


# ---------------------------------------------------------------- pipeline
def run_pipeline(raw_request: str):
    state = {
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

    with st.status("🧭 Coordinator — understanding your request", expanded=True) as s:
        state.update(coordinator_node(state))
        st.write(f"Hands off to: **{state['delegated_to']}**")
        s.update(label="🧭 Coordinator ✓", state="complete")

    with st.status("🛡️ Safety & Escalation check", expanded=True) as s:
        state.update(safety_node(state))
        if state["status"] == "blocked":
            s.update(label="🛡️ Blocked", state="error")
            st.error("I can't help with that — it asks for medical advice. I can only help with scheduling and documents.")
            return
        if state["status"] == "escalated":
            s.update(label="🛡️ Escalated to a human", state="error")
            st.warning("This has been escalated to a staff member for review.")
            return
        st.write("Allowed ✓")
        s.update(label="🛡️ Safety ✓", state="complete")

    if state["delegated_to"] == "routing":
        with st.status("🏥 Routing to a department", expanded=True) as s:
            state.update(routing_node(state))
            if state["status"] == "escalated":
                s.update(label="🏥 Escalated", state="error")
                st.warning("Couldn't confidently match a department — escalated for review.")
                return
            st.write(f"Department: **{state['department']}**")
            s.update(label=f"🏥 Routed → {state['department']} ✓", state="complete")

    if state["delegated_to"] == "appointment":
        with st.status("📅 Appointment agent", expanded=True):
            options = run_appointment(state)
        if options:
            # pause for slot selection across a Streamlit rerun
            st.session_state.awaiting_slot = True
            st.session_state.pending_state = state
            st.session_state.pending_options = options
            st.rerun()
        else:
            st.success(st.session_state.get("last_reply", "Done."))
    elif state["delegated_to"] == "document":
        st.info("Document handling isn't wired up yet.")
    elif state["delegated_to"] == "escalate":
        st.warning("Sent to a human for review.")


# ---------------------------------------------------------------- slot selection view
def slot_selection_view():
    st.subheader("Choose a time")
    options = st.session_state.pending_options
    for opt in options:
        label = f"{opt['start']} → {opt['end']}"
        if st.button(label, key=opt["slot_id"], use_container_width=True):
            state = st.session_state.pending_state
            with st.status("📅 Booking your slot", expanded=True):
                run_appointment(state, resume_choice=opt["slot_id"])
            st.session_state.awaiting_slot = False
            st.success(st.session_state.get("last_reply", "Booked!"))
            # keep the confirmation on screen; clear the pending flags
            st.session_state.pending_options = None
            st.session_state.pending_state = None


# ---------------------------------------------------------------- main
def main():
    if "user_id" not in st.session_state:
        login_view()
        return

    st.title("🏥 AgentCare")
    st.caption(f"Logged in as {st.session_state.email}")
    if st.sidebar.button("Log out"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    if st.session_state.get("awaiting_slot"):
        slot_selection_view()
        return

    prompt = st.chat_input("What do you need? e.g. 'Book an appointment for my knee pain'")
    if prompt:
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            run_pipeline(prompt)


main()