import os
from datetime import date

import streamlit as st

from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

DATA_FILE = "data.json"


def _save() -> None:
    """Persist the current owner profile to data.json."""
    if st.session_state.owner:
        st.session_state.owner.save_to_json(DATA_FILE)


# --- Session state initialization ---
# On the very first run of a browser session, try to restore from data.json.
# After that, session_state already has the objects so we skip the load.
if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            owner = Owner.load_from_json(DATA_FILE)
            st.session_state.owner = owner
            st.session_state.pet = owner.get_pets()[0] if owner.get_pets() else None
            st.session_state.scheduler = Scheduler(owner)
        except Exception:
            # Corrupted file — start fresh
            st.session_state.owner = None
            st.session_state.pet = None
            st.session_state.scheduler = None
    else:
        st.session_state.owner = None
        st.session_state.pet = None
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
    pet = Pet(name=pet_name, species=species, breed=breed, age=age)
    owner = Owner(name=owner_name, available_minutes=int(available_minutes))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    st.session_state.owner = owner
    st.session_state.pet = pet
    st.session_state.scheduler = scheduler
    _save()
    st.success(f"Saved! {owner.name}'s pet {pet.name} is ready. (Profile written to {DATA_FILE})")

if st.session_state.owner:
    task_count = sum(len(p.get_tasks()) for p in st.session_state.owner.get_pets())
    st.caption(
        f"Current profile: {st.session_state.owner} | "
        f"{task_count} task(s) loaded from {DATA_FILE}"
        if os.path.exists(DATA_FILE) and not submitted
        else f"Current profile: {st.session_state.owner}"
    )

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
        start_time_input = st.text_input(
            "Start time (HH:MM, optional)",
            value="",
            placeholder="e.g. 08:00",
            help="Leave blank if you don't need time-based sorting or conflict detection.",
        )

    add_task = st.form_submit_button("Add task")

if add_task:
    if st.session_state.pet is None:
        st.warning("Save your owner and pet profile first (Step 1).")
    else:
        # Validate the optional HH:MM field before creating the task
        parsed_time = None
        if start_time_input.strip():
            parts = start_time_input.strip().split(":")
            if (
                len(parts) == 2
                and parts[0].isdigit()
                and parts[1].isdigit()
                and 0 <= int(parts[0]) <= 23
                and 0 <= int(parts[1]) <= 59
            ):
                parsed_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            else:
                st.error("Start time must be in HH:MM format (e.g. 08:30). Task not added.")
                st.stop()

        task = Task(
            name=task_name,
            category=category,
            duration_minutes=int(duration),
            priority=PRIORITY_MAP[priority_label],
            frequency=frequency,
            start_time=parsed_time,
            due_date=date.today(),
        )
        st.session_state.pet.add_task(task)
        _save()
        st.success(f"Added: **{task.name}** ({task.duration_minutes} min, {frequency})")

# --- Task list with sort and filter controls ---
if st.session_state.pet and st.session_state.pet.get_tasks():
    tasks_all = st.session_state.pet.get_tasks()

    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        filter_cat = st.selectbox(
            "Filter by category",
            ["All"] + CATEGORY_OPTIONS,
            key="filter_cat",
        )
    with fc2:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Completed"],
            key="filter_status",
        )
    with fc3:
        sort_order = st.selectbox(
            "Sort by",
            ["Time (earliest first)", "Priority (highest first)"],
            key="sort_order",
        )

    # Apply filters
    filtered = Scheduler.filter_tasks(
        tasks_all,
        category=None if filter_cat == "All" else filter_cat,
        completed=None if filter_status == "All" else (filter_status == "Completed"),
    )

    # Apply sort
    if sort_order == "Time (earliest first)":
        display_tasks = Scheduler.sort_by_time(filtered)
    else:
        display_tasks = sorted(filtered, key=lambda t: t.priority)

    st.write(f"**{st.session_state.pet.name}'s tasks** ({len(display_tasks)} shown):")
    if display_tasks:
        rows = [
            {
                "Task": t.name,
                "Category": t.category,
                "Start": t.start_time or "--",
                "Minutes": t.duration_minutes,
                "Priority": f"P{t.priority}",
                "Frequency": t.frequency,
                "Done": "Yes" if t.completed else "No",
            }
            for t in display_tasks
        ]
        st.table(rows)
    else:
        st.info("No tasks match the current filters.")
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
        plan = scheduler.generate_plan(pet)

        # --- Conflict warnings — shown BEFORE the plan so the owner sees them first ---
        conflict_warnings = Scheduler.warn_conflicts(
            [t for t in plan if t.start_time is not None],
            label=pet.name,
        )
        if conflict_warnings:
            st.warning(
                f"**{len(conflict_warnings)} scheduling conflict(s) detected.** "
                "Two or more tasks overlap in time. Consider adjusting their start times."
            )
            for w in conflict_warnings:
                # Strip the leading "WARNING: " prefix — Streamlit's orange banner already signals it
                st.warning(w.replace("WARNING: ", ""))

        # --- Schedule summary ---
        if plan:
            st.success(
                f"Scheduled **{len(plan)} task(s)** — "
                f"{scheduler.get_total_duration()} of {owner.available_minutes} minutes used."
            )

            # Sort the scheduled tasks by time for display
            sorted_plan = Scheduler.sort_by_time(plan)
            schedule_rows = [
                {
                    "Task": t.name,
                    "Category": t.category,
                    "Start": t.start_time or "--",
                    "Minutes": t.duration_minutes,
                    "Priority": f"P{t.priority}",
                    "Frequency": t.frequency,
                }
                for t in sorted_plan
            ]
            st.table(schedule_rows)
        else:
            st.error("No tasks could be scheduled within the available time.")

        # --- Skipped tasks ---
        if scheduler.skipped_tasks:
            st.warning(
                f"**{len(scheduler.skipped_tasks)} task(s) skipped** — not enough time remaining:"
            )
            for t in scheduler.skipped_tasks:
                st.write(f"- {t.name} ({t.duration_minutes} min, P{t.priority})")

        # --- Reasoning expander ---
        with st.expander("Why this plan?"):
            st.text(scheduler.explain_plan())

        # --- Auto-assign times expander ---
        untimed_in_plan = [t for t in plan if t.start_time is None]
        if untimed_in_plan:
            with st.expander(f"Auto-assign start times ({len(untimed_in_plan)} untimed task(s))"):
                st.write(
                    "These tasks have no start time. PawPal+ can slot them "
                    "sequentially in priority order starting from a chosen time."
                )
                auto_start = st.text_input(
                    "Day start time (HH:MM)", value="08:00", key="auto_start"
                )
                if st.button("Assign times", key="btn_auto"):
                    assigned = Scheduler.auto_assign_times(plan, day_start=auto_start)
                    st.success("Suggested timeline (no overlaps guaranteed):")
                    st.table([
                        {
                            "Task": t.name,
                            "Suggested start": t.start_time,
                            "Duration": f"{t.duration_minutes} min",
                            "Priority": f"P{t.priority}",
                        }
                        for t in assigned
                    ])

st.divider()

# -------------------------------------------------------------------------
# Section 4: Find the next free slot
# -------------------------------------------------------------------------
st.subheader("Step 4: Find a free slot")
st.caption("Find out when you can fit a new task into today's existing schedule.")

if st.session_state.pet and st.session_state.pet.get_tasks():
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        slot_duration = st.number_input(
            "Task duration (minutes)", min_value=1, max_value=240, value=20, key="slot_dur"
        )
    with sc2:
        slot_day_start = st.text_input("Day start (HH:MM)", value="08:00", key="slot_ds")
    with sc3:
        slot_day_end = st.text_input("Day end (HH:MM)", value="22:00", key="slot_de")

    if st.button("Find next free slot"):
        slot = Scheduler.find_next_slot(
            st.session_state.pet.get_tasks(),
            duration_minutes=int(slot_duration),
            day_start=slot_day_start,
            day_end=slot_day_end,
        )
        if slot:
            end_min = Scheduler._to_minutes(slot) + int(slot_duration)
            st.success(
                f"Next available **{slot_duration}-minute** slot: "
                f"**{slot}** to **{end_min // 60:02d}:{end_min % 60:02d}**."
            )
        else:
            st.warning(
                f"No {slot_duration}-minute gap available between {slot_day_start} "
                f"and {slot_day_end}. Try shortening the task or extending the day window."
            )
else:
    st.info("Add tasks in Step 2 to use the free-slot finder.")
