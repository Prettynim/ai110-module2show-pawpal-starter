from pawpal_system import Task, Pet, Owner, Scheduler


# --- Task tests ---

def test_mark_complete_changes_status():
    """mark_complete() should set completed to True."""
    task = Task(name="Morning walk", category="walk", duration_minutes=30, priority=1)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_mark_complete_is_idempotent():
    """Calling mark_complete() twice should not raise and should stay True."""
    task = Task(name="Breakfast", category="feed", duration_minutes=10, priority=1)
    task.mark_complete()
    task.mark_complete()
    assert task.completed is True


# --- Pet tests ---

def test_add_task_increases_count():
    """Adding a task to a Pet should increase its task list length by one."""
    pet = Pet(name="Buddy", species="Dog", breed="Labrador", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(name="Walk", category="walk", duration_minutes=20, priority=1))
    assert len(pet.get_tasks()) == 1


def test_add_multiple_tasks():
    """Adding three tasks should result in a task list of length three."""
    pet = Pet(name="Luna", species="Cat", breed="Siamese", age=2)
    pet.add_task(Task("Breakfast",   "feed",      10, 1))
    pet.add_task(Task("Flea med",    "meds",       5, 2))
    pet.add_task(Task("Laser play",  "enrichment", 15, 3))
    assert len(pet.get_tasks()) == 3


# --- Scheduler tests ---

def test_scheduler_respects_time_budget():
    """Scheduler should not schedule more minutes than the owner has available."""
    owner = Owner(name="Alex", available_minutes=30)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Long walk",  "walk", duration_minutes=25, priority=1))
    pet.add_task(Task("Bath",       "grooming", duration_minutes=40, priority=2))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)

    assert scheduler.get_total_duration() <= owner.available_minutes


def test_scheduler_skips_tasks_that_dont_fit():
    """Tasks that exceed remaining time should appear in skipped_tasks."""
    owner = Owner(name="Alex", available_minutes=20)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Quick feed", "feed",     duration_minutes=10, priority=1))
    pet.add_task(Task("Long walk",  "walk",     duration_minutes=30, priority=2))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)

    skipped_names = [t.name for t in scheduler.skipped_tasks]
    assert "Long walk" in skipped_names


def test_scheduler_orders_by_priority():
    """Highest-priority tasks (lowest number) should appear first in the plan."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Grooming", "grooming",   duration_minutes=15, priority=3))
    pet.add_task(Task("Meds",     "meds",       duration_minutes=5,  priority=2))
    pet.add_task(Task("Walk",     "walk",       duration_minutes=20, priority=1))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(pet)

    priorities = [t.priority for t in plan]
    assert priorities == sorted(priorities)
