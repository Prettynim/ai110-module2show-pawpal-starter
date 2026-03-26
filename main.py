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


def main():
    # --- Owner setup ---
    owner = Owner(name="Jordan", available_minutes=75)

    # --- Pet 1: Buddy the dog ---
    buddy = Pet(name="Buddy", species="Dog", breed="Labrador", age=3)
    buddy.add_task(Task("Morning walk",    "walk",       duration_minutes=30, priority=1))
    buddy.add_task(Task("Breakfast",       "feed",       duration_minutes=10, priority=1))
    buddy.add_task(Task("Heartworm med",   "meds",       duration_minutes=5,  priority=2))
    buddy.add_task(Task("Fetch session",   "enrichment", duration_minutes=20, priority=3))
    buddy.add_task(Task("Bath time",       "grooming",   duration_minutes=40, priority=4))

    # --- Pet 2: Luna the cat ---
    luna = Pet(name="Luna", species="Cat", breed="Siamese", age=2)
    luna.add_task(Task("Breakfast",        "feed",       duration_minutes=5,  priority=1))
    luna.add_task(Task("Flea treatment",   "meds",       duration_minutes=10, priority=2))
    luna.add_task(Task("Brush coat",       "grooming",   duration_minutes=15, priority=3))
    luna.add_task(Task("Laser toy play",   "enrichment", duration_minutes=20, priority=3))

    owner.add_pet(buddy)
    owner.add_pet(luna)

    # --- Print owner summary ---
    print()
    print(f"  {owner}")
    print()

    # --- Generate and display schedule for each pet ---
    scheduler = Scheduler(owner)

    for pet in owner.get_pets():
        print_schedule(owner, scheduler, pet)


if __name__ == "__main__":
    main()
