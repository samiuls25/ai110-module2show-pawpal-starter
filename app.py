import streamlit as st

# Import the logic layer
from pawpal_system import DailyPlan, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# Initialize session state
# st.session_state behaves like a dict that survives reruns.
# We only create the Owner once; every subsequent rerun finds it already there.
if "owner" not in st.session_state:
    st.session_state.owner = None          # set when the owner form is submitted


# ── Helper: short-hand to the owner stored in state ───────────────────────────
def owner() -> Owner | None:
    return st.session_state.owner


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Owner profile
# ══════════════════════════════════════════════════════════════════════════════
st.header("1. Owner profile")

if owner() is None:
    with st.form("owner_form"):
        name = st.text_input("Your name", value="Jordan")
        minutes = st.number_input(
            "Minutes available today", min_value=10, max_value=480, value=90, step=5
        )
        if st.form_submit_button("Save profile"):
            # ── Wire: create Owner and store it in session_state ──────────────
            st.session_state.owner = Owner(name=name, available_minutes=minutes)
            st.rerun()
else:
    o = owner()
    st.success(f"Owner: **{o.name}** — {o.available_minutes} min available today")
    if st.button("Edit profile"):
        st.session_state.owner = None
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Pets
# ══════════════════════════════════════════════════════════════════════════════
st.header("2. Pets")

if owner() is None:
    st.info("Set up your owner profile above first.")
else:
    o = owner()

    # Show existing pets
    if o.pets:
        for pet in o.pets:
            st.markdown(f"- **{pet.name}** ({pet.species}, age {pet.age})")
    else:
        st.caption("No pets added yet.")

    # Form to add a new pet
    with st.form("add_pet_form", clear_on_submit=True):
        st.subheader("Add a pet")
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Name", value="Mochi")
        with col2:
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        with col3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

        if st.form_submit_button("Add pet"):
            # ── Wire: call Owner.add_pet() with a new Pet instance ────────────
            o.add_pet(Pet(name=pet_name, species=species, age=age))
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Tasks
# ══════════════════════════════════════════════════════════════════════════════
st.header("3. Tasks")

if owner() is None or not owner().pets:
    st.info("Add at least one pet before adding tasks.")
else:
    o = owner()
    pet_names = [p.name for p in o.pets]
    selected_pet_name = st.selectbox("Select a pet to add tasks to", pet_names)
    selected_pet = next(p for p in o.pets if p.name == selected_pet_name)

    # Show that pet's current tasks
    pending = selected_pet.get_pending_tasks()
    if pending:
        st.markdown(f"**{selected_pet.name}'s current tasks:**")
        for t in pending:
            st.markdown(
                f"- `[{t.priority.upper()}]` {t.title} — {t.duration_minutes} min "
                f"({t.category}, {t.frequency})"
            )
    else:
        st.caption(f"No tasks for {selected_pet.name} yet.")

    # Form to add a task
    with st.form("add_task_form", clear_on_submit=True):
        st.subheader("Add a task")
        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            category = st.selectbox(
                "Category", ["walk", "feeding", "meds", "grooming", "enrichment", "other"]
            )
        with col2:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
            priority = st.selectbox("Priority", ["high", "medium", "low"])
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

        if st.form_submit_button("Add task"):
            # ── Wire: call Pet.add_task() with a new Task instance ────────────
            selected_pet.add_task(
                Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=priority,
                    category=category,
                    frequency=frequency,
                )
            )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Generate schedule
# ══════════════════════════════════════════════════════════════════════════════
st.header("4. Today's schedule")
st.divider()

if owner() is None or not owner().pets:
    st.info("Add an owner profile and at least one pet to generate a schedule.")
elif not owner().get_all_tasks():
    st.info("Add at least one task to a pet before generating a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        # ── Wire: Scheduler reads from Owner, produces DailyPlan ─────────────
        plan: DailyPlan = Scheduler(owner()).generate_plan()

        PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        st.subheader(f"Plan for {owner().name}")
        st.caption(
            f"Budget: {owner().available_minutes} min  |  "
            f"Used: {plan.total_duration} min  |  "
            f"Remaining: {owner().available_minutes - plan.total_duration} min"
        )

        if plan.scheduled_tasks:
            st.markdown("**Scheduled:**")
            for task in plan.scheduled_tasks:
                icon = PRIORITY_ICON.get(task.priority, "")
                st.markdown(
                    f"{icon} **{task.title}** — {task.duration_minutes} min "
                    f"| {task.category} | {task.frequency}"
                )
        else:
            st.warning("No tasks fit within today's time budget.")

        if plan.skipped_tasks:
            with st.expander("Skipped tasks"):
                for task in plan.skipped_tasks:
                    reason = plan.skip_reasons.get(task.title, "")
                    st.markdown(f"- ~~{task.title}~~ — {reason}")

        with st.expander("Full explanation"):
            st.text(plan.explain())
