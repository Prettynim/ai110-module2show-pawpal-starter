from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def print_separator(char="=", width=50):
    print(char * width)


def print_schedule(owner: Owner, scheduler: Scheduler, pet: Pet):
    print_separator()
    print(f"  PAWPAL+ - TODAY'S SCHEDULE")
    print_separator()
    print(f"  Owner : {owner.name}")
    print(f"  Pet   : {pet}")
    print(f"  Budget: {owner.available_minutes} min available")
    print_separator()

    plan = scheduler.generate_plan(pet)

    if not plan:
        print("  No tasks could be scheduled today.")
    else:
        print(f"  {'#':<3} {'Task':<22} {'Category':<12} {'Min':>4}  {'Priority':>8}")
        print_separator("-")
        for i, task in enumerate(plan, 1):
            print(f"  {i:<3} {task.name:<22} {task.category:<12} {task.duration_minutes:>4}  P{task.priority:>7}")
        print_separator("-")
        print(f"  {'TOTAL':<37} {scheduler.get_total_duration():>4} min")

    if scheduler.skipped_tasks:
        print()
        print("  Skipped (did not fit in time budget):")
        for task in scheduler.skipped_tasks:
            print(f"    x  {task.name} ({task.duration_minutes} min, P{task.priority})")

    print_separator()
    print()


def end_time(start_hhmm: str, duration_minutes: int) -> str:
    """Compute end time given a start "HH:MM" string and a duration in minutes."""
    h, m = map(int, start_hhmm.split(":"))
    total = h * 60 + m + duration_minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def demo_sort_by_time(buddy: Pet):
    """Phase 4 — Algorithm 1: Sort tasks by 'HH:MM' start_time string.

    Tasks are added to Buddy out of order; sorted() with a lambda key
    puts them in chronological order. Untimed tasks fall to the bottom.
    """
    print_separator()
    print("  DEMO 1: Sort by Time  (tasks were added out of order)")
    print_separator()
    print("  As added:")
    for t in buddy.get_tasks():
        print(f"    {t.start_time or 'no time':>8}  {t.name}")
    print()
    print("  After sort_by_time():")
    for t in Scheduler.sort_by_time(buddy.get_tasks()):
        print(f"    {t.start_time or 'no time':>8}  {t.name}")
    print()


def demo_filter_tasks(owner: Owner, buddy: Pet):
    """Phase 4 — Algorithm 2: Filter by category, status, and pet name."""
    print_separator()
    print("  DEMO 2: Filter Tasks")
    print_separator()

    # Filter by category
    meds = Scheduler.filter_tasks(buddy.get_tasks(), category="meds")
    print(f"  Buddy's meds tasks ({len(meds)} found):")
    for t in meds:
        print(f"    - {t.name}")

    # Filter by completion status
    buddy.get_tasks()[0].mark_complete()   # mark Morning walk done for demo
    pending = Scheduler.filter_tasks(buddy.get_tasks(), completed=False)
    done    = Scheduler.filter_tasks(buddy.get_tasks(), completed=True)
    print(f"\n  Pending: {len(pending)}  |  Completed: {len(done)}")
    for t in done:
        print(f"    [x] {t.name} [done]")
    for t in pending:
        print(f"    [ ] {t.name} [pending]")

    # Filter by pet name (across the whole owner household)
    print(f"\n  filter_by_pet(owner, 'Luna'):")
    luna_tasks = Scheduler.filter_by_pet(owner, "Luna")
    for t in luna_tasks:
        print(f"    - {t.name} ({t.category})")
    print()


def demo_recurring_tasks(buddy: Pet):
    """Phase 4 — Algorithm 3: Recurring task logic by day of week."""
    print_separator()
    print("  DEMO 3: Recurring Tasks (day filtering)")
    print_separator()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in [0, 2]:  # Monday and Wednesday to show contrast
        due = Scheduler.get_due_tasks(buddy, day_of_week=day)
        print(f"  {day_names[day]}: {len(due)} task(s) due")
        for t in due:
            print(f"    - {t.name} ({t.frequency})")
    print()


def demo_recurring_completion(scheduler: Scheduler, buddy: Pet):
    """Phase 4 — Step 3: Mark tasks complete and auto-create next occurrences.

    Calls mark_task_complete(name, pet) so the scheduler can call
    next_occurrence() and add the new Task to the pet automatically.
    """
    print_separator()
    print("  DEMO 5: Recurring Task Auto-Scheduling")
    print_separator()

    # Re-generate Buddy's plan so scheduled_tasks is populated
    scheduler.generate_plan(buddy)

    tasks_before = len(buddy.get_tasks())
    print(f"  Buddy's tasks before completion: {tasks_before}")
    for t in buddy.get_tasks():
        due = f"  (due {t.due_date})" if t.due_date else ""
        print(f"    [{'+' if t.completed else ' '}] {t.name} ({t.frequency}){due}")

    # Complete two recurring tasks — daily and weekly
    scheduler.mark_task_complete("Morning walk", pet=buddy)
    scheduler.mark_task_complete("Heartworm med", pet=buddy)
    # Complete an as-needed-equivalent task without a pet to show no recurrence
    scheduler.mark_task_complete("Fetch session")

    print(f"\n  After completing 'Morning walk' (daily), 'Heartworm med' (weekly),")
    print(f"  and 'Fetch session' (daily, no pet passed - no auto-recur):")
    print(f"  Buddy's tasks now: {len(buddy.get_tasks())}  (+{len(buddy.get_tasks()) - tasks_before} new)")
    for t in buddy.get_tasks():
        due = f"  (due {t.due_date})" if t.due_date else ""
        tag = "[x]" if t.completed else "[NEW]" if t not in buddy.get_tasks()[:tasks_before] else "   "
        print(f"    {tag} {t.name} ({t.frequency}){due}")
    print()


def demo_conflict_detection(owner: Owner, buddy: Pet):
    """Phase 4 — Step 4: Warn about overlapping tasks (same pet and cross-pet).

    Uses warn_conflicts() for a single pet and warn_cross_pet_conflicts()
    for the whole household. Both return warning strings — nothing crashes.
    """
    print_separator()
    print("  DEMO 4: Conflict Detection (Warning Messages)")
    print_separator()

    # --- Single-pet warnings ---
    print("  Buddy's schedule (intentional same-time tasks):")
    buddy_warnings = Scheduler.warn_conflicts(buddy.get_tasks(), label="Buddy")
    if not buddy_warnings:
        print("    No conflicts.")
    else:
        for w in buddy_warnings:
            print(f"    {w}")

    # --- Cross-pet warnings ---
    print()
    print("  Cross-pet check (all pets in Jordan's household):")
    cross_warnings = Scheduler.warn_cross_pet_conflicts(owner)
    if not cross_warnings:
        print("    No cross-pet conflicts.")
    else:
        for w in cross_warnings:
            print(f"    {w}")
    print()


def main():
    # --- Owner setup ---
    owner = Owner(name="Jordan", available_minutes=75)

    today = date.today()

    # --- Pet 1: Buddy the dog ---
    # Tasks added OUT OF ORDER intentionally — sort_by_time() will fix the display.
    # start_time uses "HH:MM" string format; due_date enables next_occurrence().
    buddy = Pet(name="Buddy", species="Dog", breed="Labrador", age=3)
    buddy.add_task(Task("Fetch session",   "enrichment", duration_minutes=20, priority=3,
                        frequency="daily",  start_time="10:00", due_date=today))
    buddy.add_task(Task("Heartworm med",   "meds",       duration_minutes=5,  priority=2,
                        frequency="weekly", start_time="08:30", due_date=today))
    buddy.add_task(Task("Bath time",       "grooming",   duration_minutes=40, priority=4,
                        frequency="weekly", start_time="11:00", due_date=today))
    buddy.add_task(Task("Morning walk",    "walk",       duration_minutes=30, priority=1,
                        frequency="daily",  start_time="08:00", due_date=today))
    buddy.add_task(Task("Breakfast",       "feed",       duration_minutes=10, priority=1,
                        frequency="daily",  start_time="08:30", due_date=today))

    # --- Pet 2: Luna the cat ---
    # Breakfast at 08:30 intentionally overlaps Buddy's Breakfast + Heartworm med
    # to demonstrate cross-pet conflict detection.
    luna = Pet(name="Luna", species="Cat", breed="Siamese", age=2)
    luna.add_task(Task("Breakfast",        "feed",       duration_minutes=5,  priority=1,
                        frequency="daily",  start_time="08:30", due_date=today))
    luna.add_task(Task("Flea treatment",   "meds",       duration_minutes=10, priority=2,
                        frequency="weekly", start_time="12:00", due_date=today))
    luna.add_task(Task("Laser toy play",   "enrichment", duration_minutes=20, priority=3,
                        frequency="daily",  start_time="15:00", due_date=today))
    luna.add_task(Task("Brush coat",       "grooming",   duration_minutes=15, priority=3,
                        frequency="as-needed"))

    owner.add_pet(buddy)
    owner.add_pet(luna)

    # --- Print owner summary ---
    print()
    print(f"  {owner}")
    print()

    # --- Original schedule demo ---
    scheduler = Scheduler(owner)
    for pet in owner.get_pets():
        print_schedule(owner, scheduler, pet)

    # --- Phase 4 algorithm demos ---
    demo_sort_by_time(buddy)
    demo_filter_tasks(owner, buddy)
    demo_recurring_tasks(buddy)
    demo_conflict_detection(owner, buddy)
    demo_recurring_completion(scheduler, buddy)


if __name__ == "__main__":
    main()
