import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# --- Session state initialization ---
# Streamlit reruns this file on every interaction, so we guard each key with
# "if not in" to ensure objects are created only once per browser session.
if "owner" not in st.session_state:
    st.session_state.owner = None

if "pet" not in st.session_state:
    st.session_state.pet = None

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None

# -------------------------------------------------------------------------
# Section 1: Owner + Pet setup
# -------------------------------------------------------------------------
st.title("PawPal+")
st.subheader("Step 1: Tell us about you and your pet")

with st.form("setup_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
        available_minutes = st.number_input(
            "Time available today (minutes)", min_value=10, max_value=480, value=60
        )
    with col2:
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
        breed = st.text_input("Breed", value="Mixed")
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

    submitted = st.form_submit_button("Save owner & pet")

if submitted:
    # Create real Owner and Pet objects and wire them together
    pet = Pet(name=pet_name, species=species, breed=breed, age=age)
    owner = Owner(name=owner_name, available_minutes=int(available_minutes))
    owner.add_pet(pet)                          # Owner.add_pet() links them
    scheduler = Scheduler(owner)                # Scheduler takes the owner

    st.session_state.owner = owner
    st.session_state.pet = pet
    st.session_state.scheduler = scheduler
    st.success(f"Saved! {owner.name}'s pet {pet.name} is ready.")

# Show current owner/pet summary if they exist
if st.session_state.owner:
    st.caption(f"Current profile: {st.session_state.owner}")

st.divider()

# -------------------------------------------------------------------------
# Section 2: Add tasks to the pet
# -------------------------------------------------------------------------
st.subheader("Step 2: Add care tasks")

PRIORITY_MAP = {"High (1)": 1, "Medium (2)": 2, "Low (3)": 3}
CATEGORY_OPTIONS = ["walk", "feed", "meds", "grooming", "enrichment", "other"]
FREQUENCY_OPTIONS = ["daily", "weekly", "as-needed"]

with st.form("task_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        task_name = st.text_input("Task name", value="Morning walk")
        category = st.selectbox("Category", CATEGORY_OPTIONS)
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        frequency = st.selectbox("Frequency", FREQUENCY_OPTIONS)
    with col3:
        priority_label = st.selectbox("Priority", list(PRIORITY_MAP.keys()))

    add_task = st.form_submit_button("Add task")

if add_task:
    if st.session_state.pet is None:
        st.warning("Save your owner and pet profile first (Step 1).")
    else:
        task = Task(
            name=task_name,
            category=category,
            duration_minutes=int(duration),
            priority=PRIORITY_MAP[priority_label],
            frequency=frequency,
        )
        st.session_state.pet.add_task(task)     # Pet.add_task() stores it
        st.success(f"Added task: {task.name}")

# Display current task list
if st.session_state.pet and st.session_state.pet.get_tasks():
    st.write(f"**{st.session_state.pet.name}'s tasks:**")
    rows = [
        {
            "Task": t.name,
            "Category": t.category,
            "Minutes": t.duration_minutes,
            "Priority": f"P{t.priority}",
            "Frequency": t.frequency,
            "Done": t.completed,
        }
        for t in st.session_state.pet.get_tasks()
    ]
    st.table(rows)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# -------------------------------------------------------------------------
# Section 3: Generate the daily schedule
# -------------------------------------------------------------------------
st.subheader("Step 3: Generate today's schedule")

if st.button("Generate schedule"):
    owner = st.session_state.owner
    pet = st.session_state.pet
    scheduler = st.session_state.scheduler

    if not owner or not pet:
        st.warning("Complete Step 1 before generating a schedule.")
    elif not pet.get_pending_tasks():
        st.warning("Add at least one task in Step 2 before generating a schedule.")
    else:
        plan = scheduler.generate_plan(pet)     # Scheduler.generate_plan() does the work

        st.success(
            f"Scheduled {len(plan)} task(s) using "
            f"{scheduler.get_total_duration()} of {owner.available_minutes} available minutes."
        )

        if plan:
            st.write("**Scheduled tasks:**")
            schedule_rows = [
                {
                    "Task": t.name,
                    "Category": t.category,
                    "Minutes": t.duration_minutes,
                    "Priority": f"P{t.priority}",
                }
                for t in plan
            ]
            st.table(schedule_rows)

        if scheduler.skipped_tasks:
            st.warning(
                f"{len(scheduler.skipped_tasks)} task(s) skipped — not enough time remaining:"
            )
            for t in scheduler.skipped_tasks:
                st.write(f"- {t.name} ({t.duration_minutes} min)")

        with st.expander("Why this plan?"):
            st.text(scheduler.explain_plan())   # Scheduler.explain_plan() gives the reasoning
