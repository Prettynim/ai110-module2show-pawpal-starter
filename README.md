# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

Phase 4 adds four algorithmic features to `Scheduler` in `pawpal_system.py`:

### Sort by time
`Scheduler.sort_by_time(tasks)` orders any task list chronologically using
Python's `sorted()` with a `lambda` key on the `"HH:MM"` `start_time` field.
Zero-padded time strings compare correctly without parsing — tasks without a
`start_time` are placed at the end.

### Filter tasks
`Scheduler.filter_tasks(tasks, category, completed)` returns only the tasks
that match the supplied filters. Pass `None` for any field to skip it.
`Scheduler.filter_by_pet(owner, pet_name)` retrieves all tasks for a single
named pet across the owner's household.

### Recurring tasks
Each `Task` stores a `due_date` (`datetime.date`) and a `frequency`
(`"daily"`, `"weekly"`, or `"as-needed"`).

- `Task.next_occurrence()` uses `timedelta` to compute the next due date and
  returns a fresh, uncompleted copy of the task (`+1 day` or `+7 days`).
- `Scheduler.mark_task_complete(name, pet)` calls `next_occurrence()` after
  marking the task done and automatically adds the result to the pet's task
  list, so future schedule generations include it without manual re-entry.
- `Scheduler.get_due_tasks(pet, day_of_week)` filters to only the tasks due
  on a given day: daily tasks are always included; weekly tasks only on
  Mondays; as-needed tasks never appear automatically.

### Conflict detection
`Scheduler.detect_conflicts(tasks)` finds pairs of tasks whose time windows
overlap using the interval test `A.start < B.end AND B.start < A.end`.

`Scheduler.warn_conflicts(tasks, label)` wraps this in a lightweight layer
that returns human-readable `WARNING:` strings instead of raising exceptions,
so callers check `if warnings:` rather than using try/except.

`Scheduler.warn_cross_pet_conflicts(owner)` pools timed tasks from every pet
in the household and checks all unique pairs with `itertools.combinations`,
labelling each warning with both pet names so the owner knows exactly which
animals have a scheduling clash.
