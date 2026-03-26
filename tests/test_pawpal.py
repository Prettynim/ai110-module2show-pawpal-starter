import os
import tempfile
from datetime import date, timedelta

import pytest

from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Helpers — reusable fixtures so each test doesn't repeat boilerplate setup
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    """An owner with a generous 120-minute daily budget."""
    return Owner(name="Alex", available_minutes=120)


@pytest.fixture
def basic_pet():
    """A dog with three tasks added in reverse-priority order."""
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Grooming", "grooming",   duration_minutes=15, priority=3))
    pet.add_task(Task("Meds",     "meds",       duration_minutes=5,  priority=2))
    pet.add_task(Task("Walk",     "walk",       duration_minutes=20, priority=1))
    return pet


# ---------------------------------------------------------------------------
# Task — mark_complete and next_occurrence
# ---------------------------------------------------------------------------

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


def test_next_occurrence_daily_advances_one_day():
    """A daily task's next occurrence should be due_date + 1 day."""
    today = date.today()
    task = Task("Morning walk", "walk", duration_minutes=30, priority=1,
                frequency="daily", due_date=today)
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.due_date == today + timedelta(days=1)


def test_next_occurrence_weekly_advances_seven_days():
    """A weekly task's next occurrence should be due_date + 7 days."""
    today = date.today()
    task = Task("Bath time", "grooming", duration_minutes=40, priority=3,
                frequency="weekly", due_date=today)
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.due_date == today + timedelta(weeks=1)


def test_next_occurrence_as_needed_returns_none():
    """as-needed tasks should not auto-recur — next_occurrence() returns None."""
    task = Task("Vet visit", "meds", duration_minutes=60, priority=1,
                frequency="as-needed", due_date=date.today())
    assert task.next_occurrence() is None


def test_next_occurrence_result_is_not_completed():
    """The new task returned by next_occurrence() must start as pending."""
    task = Task("Walk", "walk", duration_minutes=20, priority=1,
                frequency="daily", due_date=date.today())
    task.mark_complete()
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.completed is False


def test_next_occurrence_preserves_task_attributes():
    """next_occurrence() should carry forward name, category, duration, and priority."""
    task = Task("Morning walk", "walk", duration_minutes=30, priority=1,
                frequency="daily", start_time="08:00", due_date=date.today())
    nxt = task.next_occurrence()
    assert nxt.name == task.name
    assert nxt.category == task.category
    assert nxt.duration_minutes == task.duration_minutes
    assert nxt.priority == task.priority
    assert nxt.start_time == task.start_time


# ---------------------------------------------------------------------------
# Pet — task management
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    """Adding a task to a Pet should increase its task list length by one."""
    pet = Pet(name="Buddy", species="Dog", breed="Labrador", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(name="Walk", category="walk", duration_minutes=20, priority=1))
    assert len(pet.get_tasks()) == 1


def test_add_multiple_tasks():
    """Adding three tasks should result in a task list of length three."""
    pet = Pet(name="Luna", species="Cat", breed="Siamese", age=2)
    pet.add_task(Task("Breakfast",  "feed",       10, 1))
    pet.add_task(Task("Flea med",   "meds",        5, 2))
    pet.add_task(Task("Laser play", "enrichment", 15, 3))
    assert len(pet.get_tasks()) == 3


def test_pet_with_no_tasks_returns_empty_lists():
    """A brand-new pet should report zero tasks and zero pending tasks."""
    pet = Pet(name="Ghost", species="Cat", breed="Persian", age=1)
    assert pet.get_tasks() == []
    assert pet.get_pending_tasks() == []


# ---------------------------------------------------------------------------
# Scheduler — core scheduling
# ---------------------------------------------------------------------------

def test_scheduler_respects_time_budget(owner, basic_pet):
    """Scheduler should not schedule more minutes than the owner has available."""
    scheduler = Scheduler(owner)
    scheduler.generate_plan(basic_pet)
    assert scheduler.get_total_duration() <= owner.available_minutes


def test_scheduler_skips_tasks_that_dont_fit():
    """Tasks that exceed remaining time should appear in skipped_tasks."""
    owner = Owner(name="Alex", available_minutes=20)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Quick feed", "feed", duration_minutes=10, priority=1))
    pet.add_task(Task("Long walk",  "walk", duration_minutes=30, priority=2))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)

    skipped_names = [t.name for t in scheduler.skipped_tasks]
    assert "Long walk" in skipped_names


def test_scheduler_orders_by_priority(owner, basic_pet):
    """Highest-priority tasks (lowest number) should appear first in the plan."""
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(basic_pet)
    priorities = [t.priority for t in plan]
    assert priorities == sorted(priorities)


def test_scheduler_empty_pet_returns_empty_plan():
    """generate_plan() on a pet with no tasks should return an empty list."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Ghost", species="Cat", breed="Persian", age=1)
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(pet)
    assert plan == []
    assert scheduler.scheduled_tasks == []
    assert scheduler.skipped_tasks == []


def test_scheduler_all_tasks_exceed_budget():
    """When every task is longer than the budget, scheduled_tasks should be empty."""
    owner = Owner(name="Alex", available_minutes=5)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Long walk", "walk",     duration_minutes=30, priority=1))
    pet.add_task(Task("Bath",      "grooming", duration_minutes=40, priority=2))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)

    assert scheduler.scheduled_tasks == []
    assert len(scheduler.skipped_tasks) == 2


# ---------------------------------------------------------------------------
# Scheduler — mark_task_complete with auto-recurrence
# ---------------------------------------------------------------------------

def test_mark_complete_adds_next_occurrence_to_pet():
    """Completing a daily task with pet= should add a new pending task to the pet."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    today = date.today()
    pet.add_task(Task("Walk", "walk", duration_minutes=20, priority=1,
                      frequency="daily", due_date=today))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)
    count_before = len(pet.get_tasks())

    scheduler.mark_task_complete("Walk", pet=pet)

    assert len(pet.get_tasks()) == count_before + 1


def test_mark_complete_new_task_has_correct_due_date():
    """The auto-created task should be due tomorrow for a daily task."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    today = date.today()
    pet.add_task(Task("Walk", "walk", duration_minutes=20, priority=1,
                      frequency="daily", due_date=today))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)
    scheduler.mark_task_complete("Walk", pet=pet)

    new_task = pet.get_tasks()[-1]
    assert new_task.due_date == today + timedelta(days=1)
    assert new_task.completed is False


def test_mark_complete_without_pet_does_not_add_task():
    """Completing a task without passing pet= should NOT create a new occurrence."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Walk", "walk", duration_minutes=20, priority=1,
                      frequency="daily", due_date=date.today()))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)
    count_before = len(pet.get_tasks())

    scheduler.mark_task_complete("Walk")  # no pet= argument

    assert len(pet.get_tasks()) == count_before


def test_mark_complete_as_needed_does_not_add_task():
    """Completing an as-needed task with pet= should NOT create a new occurrence."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Vet visit", "meds", duration_minutes=60, priority=1,
                      frequency="as-needed", due_date=date.today()))

    scheduler = Scheduler(owner)
    scheduler.generate_plan(pet)
    count_before = len(pet.get_tasks())

    scheduler.mark_task_complete("Vet visit", pet=pet)

    assert len(pet.get_tasks()) == count_before


# ---------------------------------------------------------------------------
# Scheduler — sort_by_time
# ---------------------------------------------------------------------------

def test_sort_by_time_orders_chronologically():
    """Tasks added out of order should be returned earliest start_time first."""
    tasks = [
        Task("Fetch",    "enrichment", duration_minutes=20, priority=3, start_time="10:00"),
        Task("Walk",     "walk",       duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds",     "meds",       duration_minutes=5,  priority=2, start_time="09:00"),
    ]
    result = Scheduler.sort_by_time(tasks)
    times = [t.start_time for t in result]
    assert times == ["08:00", "09:00", "10:00"]


def test_sort_by_time_untimed_tasks_placed_last():
    """Tasks without a start_time should always appear after all timed tasks."""
    tasks = [
        Task("Untimed",  "grooming",   duration_minutes=15, priority=1),
        Task("Morning",  "walk",       duration_minutes=30, priority=2, start_time="08:00"),
    ]
    result = Scheduler.sort_by_time(tasks)
    assert result[0].start_time == "08:00"
    assert result[-1].start_time is None


def test_sort_by_time_all_untimed_unchanged_length():
    """If no tasks have a start_time, sort_by_time should return all tasks."""
    tasks = [
        Task("A", "feed",  5, 1),
        Task("B", "walk", 20, 2),
    ]
    result = Scheduler.sort_by_time(tasks)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Scheduler — filter_tasks and filter_by_pet
# ---------------------------------------------------------------------------

def test_filter_tasks_by_category():
    """filter_tasks(category=) should return only tasks in that category."""
    tasks = [
        Task("Walk",  "walk", 20, 1),
        Task("Meds",  "meds",  5, 2),
        Task("Feed",  "feed", 10, 1),
    ]
    result = Scheduler.filter_tasks(tasks, category="walk")
    assert len(result) == 1
    assert result[0].name == "Walk"


def test_filter_tasks_by_completed_false():
    """filter_tasks(completed=False) should exclude completed tasks."""
    task_a = Task("Walk", "walk", 20, 1)
    task_b = Task("Feed", "feed", 10, 1)
    task_a.mark_complete()

    result = Scheduler.filter_tasks([task_a, task_b], completed=False)
    names = [t.name for t in result]
    assert "Walk" not in names
    assert "Feed" in names


def test_filter_tasks_combined_category_and_status():
    """Combining category and completed filters should apply both."""
    task_a = Task("Meds AM", "meds", 5, 1)
    task_b = Task("Meds PM", "meds", 5, 1)
    task_c = Task("Walk",    "walk", 20, 2)
    task_a.mark_complete()

    result = Scheduler.filter_tasks([task_a, task_b, task_c],
                                    category="meds", completed=False)
    assert len(result) == 1
    assert result[0].name == "Meds PM"


def test_filter_by_pet_returns_correct_tasks():
    """filter_by_pet should return only the named pet's tasks."""
    owner = Owner(name="Alex", available_minutes=60)
    buddy = Pet(name="Buddy", species="Dog", breed="Lab", age=3)
    luna  = Pet(name="Luna",  species="Cat", breed="Siamese", age=2)
    buddy.add_task(Task("Walk",      "walk", 20, 1))
    luna.add_task( Task("Laser toy", "enrichment", 15, 2))
    owner.add_pet(buddy)
    owner.add_pet(luna)

    result = Scheduler.filter_by_pet(owner, "Luna")
    assert len(result) == 1
    assert result[0].name == "Laser toy"


def test_filter_by_pet_unknown_name_returns_empty():
    """filter_by_pet with a name that doesn't exist should return []."""
    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(Pet(name="Buddy", species="Dog", breed="Lab", age=3))

    result = Scheduler.filter_by_pet(owner, "NoSuchPet")
    assert result == []


# ---------------------------------------------------------------------------
# Scheduler — get_due_tasks (recurring filter by day)
# ---------------------------------------------------------------------------

def test_get_due_tasks_daily_always_included():
    """Daily tasks should appear regardless of the day of week."""
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Walk", "walk", 20, 1, frequency="daily"))

    for day in range(7):
        due = Scheduler.get_due_tasks(pet, day_of_week=day)
        assert any(t.name == "Walk" for t in due), f"Walk missing on day {day}"


def test_get_due_tasks_weekly_only_on_monday():
    """Weekly tasks should appear on Monday (0) and not on other days."""
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Bath", "grooming", 40, 3, frequency="weekly"))

    assert any(t.name == "Bath" for t in Scheduler.get_due_tasks(pet, day_of_week=0))
    for day in range(1, 7):
        due = Scheduler.get_due_tasks(pet, day_of_week=day)
        assert not any(t.name == "Bath" for t in due), f"Bath wrongly included on day {day}"


def test_get_due_tasks_as_needed_never_included():
    """as-needed tasks should never appear in get_due_tasks output."""
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Vet visit", "meds", 60, 1, frequency="as-needed"))

    for day in range(7):
        due = Scheduler.get_due_tasks(pet, day_of_week=day)
        assert not any(t.name == "Vet visit" for t in due)


# ---------------------------------------------------------------------------
# Scheduler — conflict detection
# ---------------------------------------------------------------------------

def test_detect_conflicts_exact_same_time():
    """Two tasks starting at the same time should be detected as a conflict."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds",  "meds", duration_minutes=10, priority=2, start_time="08:00"),
    ]
    conflicts = Scheduler.detect_conflicts(tasks)
    assert len(conflicts) == 1


def test_detect_conflicts_partial_overlap():
    """A task starting before another finishes should count as a conflict."""
    tasks = [
        Task("Walk",  "walk",      duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds",  "meds",      duration_minutes=10, priority=2, start_time="08:20"),
    ]
    conflicts = Scheduler.detect_conflicts(tasks)
    assert len(conflicts) == 1


def test_detect_conflicts_no_overlap():
    """Tasks that end before the next one starts should produce no conflicts."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds",  "meds", duration_minutes=10, priority=2, start_time="09:00"),
    ]
    conflicts = Scheduler.detect_conflicts(tasks)
    assert conflicts == []


def test_detect_conflicts_untimed_tasks_ignored():
    """Tasks without a start_time should never be flagged as conflicting."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1),
        Task("Meds",  "meds", duration_minutes=10, priority=2),
    ]
    conflicts = Scheduler.detect_conflicts(tasks)
    assert conflicts == []


def test_warn_conflicts_returns_warning_strings():
    """warn_conflicts() should return non-empty strings for each conflict."""
    tasks = [
        Task("Walk", "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds", "meds", duration_minutes=10, priority=2, start_time="08:00"),
    ]
    warnings = Scheduler.warn_conflicts(tasks, label="Buddy")
    assert len(warnings) == 1
    assert "WARNING" in warnings[0]
    assert "Buddy" in warnings[0]


def test_warn_conflicts_no_conflict_returns_empty_list():
    """warn_conflicts() should return [] when there are no overlaps."""
    tasks = [
        Task("Walk", "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Meds", "meds", duration_minutes=10, priority=2, start_time="09:00"),
    ]
    assert Scheduler.warn_conflicts(tasks) == []


def test_warn_cross_pet_conflicts_detects_cross_pet_overlap():
    """Two pets with overlapping tasks should trigger a cross-pet warning."""
    owner = Owner(name="Alex", available_minutes=120)
    buddy = Pet(name="Buddy", species="Dog", breed="Lab", age=3)
    luna  = Pet(name="Luna",  species="Cat", breed="Siamese", age=2)
    buddy.add_task(Task("Breakfast", "feed", duration_minutes=10, priority=1,
                        start_time="08:30"))
    luna.add_task( Task("Breakfast", "feed", duration_minutes=5,  priority=1,
                        start_time="08:30"))
    owner.add_pet(buddy)
    owner.add_pet(luna)

    warnings = Scheduler.warn_cross_pet_conflicts(owner)
    assert len(warnings) >= 1
    assert "Buddy" in warnings[0]
    assert "Luna" in warnings[0]


def test_warn_cross_pet_conflicts_no_overlap_returns_empty():
    """Pets with non-overlapping schedules should produce no cross-pet warnings."""
    owner = Owner(name="Alex", available_minutes=120)
    buddy = Pet(name="Buddy", species="Dog", breed="Lab", age=3)
    luna  = Pet(name="Luna",  species="Cat", breed="Siamese", age=2)
    buddy.add_task(Task("Walk",      "walk", duration_minutes=30, priority=1,
                        start_time="08:00"))
    luna.add_task( Task("Laser toy", "enrichment", duration_minutes=20, priority=2,
                        start_time="14:00"))
    owner.add_pet(buddy)
    owner.add_pet(luna)

    assert Scheduler.warn_cross_pet_conflicts(owner) == []


# ---------------------------------------------------------------------------
# Scheduler — auto_assign_times (Challenge 1)
# ---------------------------------------------------------------------------

def test_auto_assign_times_untimed_tasks_get_start_times():
    """Every task returned by auto_assign_times should have a start_time."""
    tasks = [
        Task("Walk",  "walk",      duration_minutes=30, priority=1),
        Task("Feed",  "feed",      duration_minutes=10, priority=2),
        Task("Meds",  "meds",      duration_minutes=5,  priority=3),
    ]
    result = Scheduler.auto_assign_times(tasks, day_start="08:00")
    assert all(t.start_time is not None for t in result)


def test_auto_assign_times_sequential_no_overlap():
    """Assigned start times should be sequential with no gaps or overlaps."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1),
        Task("Feed",  "feed", duration_minutes=10, priority=2),
    ]
    result = Scheduler.auto_assign_times(tasks, day_start="08:00")
    # Walk: 08:00–08:30, Feed should start at 08:30
    times = [t.start_time for t in result]
    assert times[0] == "08:00"
    assert times[1] == "08:30"


def test_auto_assign_times_respects_existing_start_time():
    """A task that already has a start_time should keep it unchanged."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1, start_time="09:00"),
        Task("Feed",  "feed", duration_minutes=10, priority=2),
    ]
    result = Scheduler.auto_assign_times(tasks, day_start="08:00")
    walk = next(t for t in result if t.name == "Walk")
    assert walk.start_time == "09:00"


def test_auto_assign_times_cursor_advances_past_fixed_task():
    """An untimed task after a fixed task should not overlap with it."""
    tasks = [
        Task("Walk",  "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Feed",  "feed", duration_minutes=10, priority=2),  # no start_time
    ]
    result = Scheduler.auto_assign_times(tasks, day_start="07:00")
    feed = next(t for t in result if t.name == "Feed")
    # Walk ends at 08:30, so Feed must start at 08:30 or later
    feed_start = Scheduler._to_minutes(feed.start_time)
    assert feed_start >= Scheduler._to_minutes("08:30")


def test_auto_assign_times_priority_order():
    """Tasks should be returned in priority order (highest first)."""
    tasks = [
        Task("Bath",  "grooming", duration_minutes=40, priority=3),
        Task("Meds",  "meds",     duration_minutes=5,  priority=1),
        Task("Feed",  "feed",     duration_minutes=10, priority=2),
    ]
    result = Scheduler.auto_assign_times(tasks, day_start="08:00")
    priorities = [t.priority for t in result]
    assert priorities == sorted(priorities)


def test_auto_assign_times_does_not_mutate_originals():
    """Original tasks without a start_time should remain unchanged."""
    task = Task("Feed", "feed", duration_minutes=10, priority=1)
    Scheduler.auto_assign_times([task], day_start="08:00")
    assert task.start_time is None


# ---------------------------------------------------------------------------
# Scheduler — find_next_slot (Challenge 1)
# ---------------------------------------------------------------------------

def test_find_next_slot_empty_schedule_returns_day_start():
    """With no existing tasks, the first slot should be the day start."""
    slot = Scheduler.find_next_slot([], duration_minutes=30, day_start="08:00")
    assert slot == "08:00"


def test_find_next_slot_gap_between_tasks():
    """A gap between two tasks that is large enough should be found."""
    tasks = [
        Task("Walk", "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Bath", "grooming", duration_minutes=40, priority=3, start_time="10:00"),
    ]
    # Gap: 08:30 to 10:00 = 90 min. A 60-min task should fit at 08:30.
    slot = Scheduler.find_next_slot(tasks, duration_minutes=60, day_start="08:00")
    assert slot == "08:30"


def test_find_next_slot_gap_too_small_skips_to_next():
    """A gap smaller than the requested duration should be skipped."""
    tasks = [
        Task("Walk", "walk", duration_minutes=30, priority=1, start_time="08:00"),
        Task("Bath", "grooming", duration_minutes=40, priority=3, start_time="08:40"),
    ]
    # Gap between Walk (ends 08:30) and Bath (starts 08:40) is only 10 min.
    # A 30-min task should land after Bath ends at 09:20.
    slot = Scheduler.find_next_slot(tasks, duration_minutes=30, day_start="08:00")
    assert slot == "09:20"


def test_find_next_slot_no_room_returns_none():
    """If the day is too full, find_next_slot should return None."""
    tasks = [
        Task("Block", "walk", duration_minutes=840, priority=1, start_time="08:00"),
    ]
    # Block runs 08:00–22:00, filling the entire day window.
    slot = Scheduler.find_next_slot(
        tasks, duration_minutes=30, day_start="08:00", day_end="22:00"
    )
    assert slot is None


def test_find_next_slot_untimed_tasks_ignored():
    """Tasks without a start_time should not affect slot finding."""
    tasks = [
        Task("Untimed", "feed", duration_minutes=120, priority=1),  # no start_time
    ]
    slot = Scheduler.find_next_slot(tasks, duration_minutes=30, day_start="08:00")
    assert slot == "08:00"


def test_find_next_slot_slot_after_all_tasks():
    """When no gaps fit, the slot should be offered after the last task."""
    tasks = [
        Task("Walk", "walk", duration_minutes=30, priority=1, start_time="08:00"),
    ]
    # Walk ends 08:30. A 20-min task should start at 08:30.
    slot = Scheduler.find_next_slot(tasks, duration_minutes=20, day_start="08:00")
    assert slot == "08:30"


# ---------------------------------------------------------------------------
# Persistence — save_to_json / load_from_json (Challenge 2)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_json(tmp_path):
    """Return a path to a temporary JSON file that doesn't exist yet."""
    return str(tmp_path / "test_data.json")


def test_save_and_load_round_trip(tmp_json):
    """Saving then loading should reproduce an identical Owner with all fields."""
    owner = Owner(name="Jordan", available_minutes=75)
    pet = Pet(name="Buddy", species="Dog", breed="Labrador", age=3)
    pet.add_task(Task(
        "Morning walk", "walk", duration_minutes=30, priority=1,
        frequency="daily", start_time="08:00", due_date=date(2026, 3, 25),
    ))
    pet.add_task(Task("Bath", "grooming", duration_minutes=40, priority=4,
                      frequency="weekly"))
    owner.add_pet(pet)

    owner.save_to_json(tmp_json)
    loaded = Owner.load_from_json(tmp_json)

    assert loaded.name == owner.name
    assert loaded.available_minutes == owner.available_minutes
    assert len(loaded.get_pets()) == 1
    loaded_pet = loaded.get_pets()[0]
    assert loaded_pet.name == "Buddy"
    assert len(loaded_pet.get_tasks()) == 2


def test_due_date_survives_round_trip(tmp_json):
    """due_date should be restored as a datetime.date, not a plain string."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    today = date(2026, 3, 25)
    pet.add_task(Task("Walk", "walk", 20, 1, due_date=today))
    owner.add_pet(pet)

    owner.save_to_json(tmp_json)
    loaded = Owner.load_from_json(tmp_json)

    restored_task = loaded.get_pets()[0].get_tasks()[0]
    assert restored_task.due_date == today
    assert isinstance(restored_task.due_date, date)


def test_none_due_date_survives_round_trip(tmp_json):
    """Tasks with no due_date should reload with due_date still None."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    pet.add_task(Task("Walk", "walk", 20, 1))  # no due_date
    owner.add_pet(pet)

    owner.save_to_json(tmp_json)
    loaded = Owner.load_from_json(tmp_json)
    assert loaded.get_pets()[0].get_tasks()[0].due_date is None


def test_completed_flag_survives_round_trip(tmp_json):
    """A completed task should still be completed after reload."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Rex", species="Dog", breed="Poodle", age=2)
    task = Task("Walk", "walk", 20, 1)
    task.mark_complete()
    pet.add_task(task)
    owner.add_pet(pet)

    owner.save_to_json(tmp_json)
    loaded = Owner.load_from_json(tmp_json)
    assert loaded.get_pets()[0].get_tasks()[0].completed is True


def test_load_from_json_raises_for_missing_file():
    """load_from_json should raise FileNotFoundError for a non-existent path."""
    with pytest.raises(FileNotFoundError):
        Owner.load_from_json("definitely_does_not_exist_xyz.json")


def test_multiple_pets_survive_round_trip(tmp_json):
    """An owner with multiple pets should reload all of them."""
    owner = Owner(name="Jordan", available_minutes=90)
    owner.add_pet(Pet(name="Buddy", species="Dog", breed="Lab", age=3))
    owner.add_pet(Pet(name="Luna", species="Cat", breed="Siamese", age=2))

    owner.save_to_json(tmp_json)
    loaded = Owner.load_from_json(tmp_json)

    assert len(loaded.get_pets()) == 2
    names = [p.name for p in loaded.get_pets()]
    assert "Buddy" in names
    assert "Luna" in names
