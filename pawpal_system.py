from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations
from typing import List, Optional, Tuple


@dataclass
class Task:
    """A single pet care activity with a duration, priority, and completion state."""

    name: str
    category: str          # "walk", "feed", "meds", "grooming", "enrichment", etc.
    duration_minutes: int
    priority: int          # 1 = highest priority
    frequency: str = "daily"   # "daily", "weekly", "as-needed"
    completed: bool = False
    start_time: Optional[str] = None  # "HH:MM" format, e.g. "08:00" or "14:30"
    due_date: Optional[date] = None   # calendar date this instance is due

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self) -> Optional["Task"]:
        """Return a new, pending Task scheduled for the next recurrence.

        Uses Python's timedelta to advance the due_date:
          - "daily"     → due_date + timedelta(days=1)
          - "weekly"    → due_date + timedelta(weeks=1)
          - "as-needed" → returns None (no automatic next occurrence)

        If due_date is not set, today's date is used as the base.
        """
        if self.frequency == "daily":
            delta = timedelta(days=1)
        elif self.frequency == "weekly":
            delta = timedelta(weeks=1)
        else:
            return None  # "as-needed" tasks do not auto-recur

        base = self.due_date if self.due_date is not None else date.today()
        return Task(
            name=self.name,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            completed=False,
            start_time=self.start_time,
            due_date=base + delta,
        )

    def __str__(self) -> str:
        status = "done" if self.completed else "pending"
        due = f", due {self.due_date}" if self.due_date else ""
        return (
            f"[P{self.priority}] {self.name} ({self.category}) "
            f"- {self.duration_minutes} min, {self.frequency}{due} [{status}]"
        )


@dataclass
class Pet:
    """An animal with a profile and an associated list of care tasks."""

    name: str
    species: str
    breed: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a new task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> bool:
        """Remove a task by name (case-insensitive). Returns True if found and removed."""
        for task in self.tasks:
            if task.name.lower() == task_name.lower():
                self.tasks.remove(task)
                return True
        return False

    def get_tasks(self) -> List[Task]:
        """Return all tasks (completed and pending) for this pet."""
        return self.tasks

    def get_pending_tasks(self) -> List[Task]:
        """Return only tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.completed]

    def __str__(self) -> str:
        return f"{self.name} ({self.species}, {self.breed}, age {self.age})"


@dataclass
class Owner:
    """A pet owner with a daily time budget and one or more pets."""

    name: str
    available_minutes: int
    preferences: List[str] = field(default_factory=list)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's household."""
        self.pets.append(pet)

    def get_pets(self) -> List[Pet]:
        """Return all pets belonging to this owner."""
        return self.pets

    def get_all_tasks(self) -> List[Task]:
        """Return all pending tasks across every pet, for multi-pet households."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_pending_tasks())
        return all_tasks

    def __str__(self) -> str:
        pet_names = ", ".join(p.name for p in self.pets) if self.pets else "no pets"
        return (
            f"Owner: {self.name} | "
            f"Available: {self.available_minutes} min/day | "
            f"Pets: {pet_names}"
        )


class Scheduler:
    """Generates a daily care plan for a pet within the owner's available time budget."""

    def __init__(self, owner: Owner):
        """Initialize the scheduler with an owner whose time budget will constrain plans."""
        self.owner = owner
        self.scheduled_tasks: List[Task] = []
        self.skipped_tasks: List[Task] = []

    def generate_plan(self, pet: Pet) -> List[Task]:
        """
        Select tasks for the given pet that fit within the owner's daily time budget.
        Strategy: sort by priority (ascending = highest first), then greedily add
        tasks until the time budget is exhausted.
        """
        self.scheduled_tasks = []
        self.skipped_tasks = []

        candidates = sorted(pet.get_pending_tasks(), key=lambda t: t.priority)
        remaining = self.owner.available_minutes

        for task in candidates:
            if task.duration_minutes <= remaining:
                self.scheduled_tasks.append(task)
                remaining -= task.duration_minutes
            else:
                self.skipped_tasks.append(task)

        return self.scheduled_tasks

    def explain_plan(self) -> str:
        """Return a human-readable explanation of what was scheduled and why."""
        if not self.scheduled_tasks and not self.skipped_tasks:
            return "No plan generated yet. Call generate_plan() first."

        lines = []
        total = self.get_total_duration()
        lines.append(
            f"Daily plan uses {total} of {self.owner.available_minutes} available minutes.\n"
        )

        if self.scheduled_tasks:
            lines.append("Scheduled tasks (highest priority first):")
            for task in self.scheduled_tasks:
                lines.append(f"  + {task}")
        else:
            lines.append("No tasks could be scheduled.")

        if self.skipped_tasks:
            lines.append("\nSkipped tasks (did not fit in remaining time):")
            for task in self.skipped_tasks:
                lines.append(f"  - {task}")

        return "\n".join(lines)

    def get_total_duration(self) -> int:
        """Return total minutes used by the current scheduled plan."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def mark_task_complete(self, task_name: str, pet: Optional["Pet"] = None) -> bool:
        """Mark a scheduled task complete by name. Returns True if found.

        If a pet is provided and the task recurs (daily or weekly), the next
        occurrence is automatically created via next_occurrence() and added to
        the pet's task list so it appears in future schedule generations.
        As-needed tasks are marked complete but no new instance is created.
        """
        for task in self.scheduled_tasks:
            if task.name.lower() == task_name.lower():
                task.mark_complete()
                if pet is not None:
                    next_task = task.next_occurrence()
                    if next_task is not None:
                        pet.add_task(next_task)
                return True
        return False

    # ------------------------------------------------------------------
    # Phase 4 algorithms
    # ------------------------------------------------------------------

    @staticmethod
    def sort_by_time(tasks: List[Task]) -> List[Task]:
        """Sort tasks by start_time string (earliest first).

        Uses a lambda with Python's sorted() to compare "HH:MM" strings
        lexicographically. Because the format is zero-padded, string order
        equals chronological order — no parsing needed.
        Tasks without a start_time are placed at the end.
        """
        timed = sorted(
            [t for t in tasks if t.start_time is not None],
            key=lambda t: t.start_time,
        )
        untimed = [t for t in tasks if t.start_time is None]
        return timed + untimed

    @staticmethod
    def filter_tasks(
        tasks: List[Task],
        category: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> List[Task]:
        """Filter a task list by category and/or completion status.

        Pass None for a field to skip that filter (match everything).
        Examples:
            filter_tasks(tasks, category="walk")               # only walks
            filter_tasks(tasks, completed=False)               # only pending
            filter_tasks(tasks, category="meds", completed=False)
        """
        result = tasks
        if category is not None:
            result = [t for t in result if t.category.lower() == category.lower()]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    @staticmethod
    def filter_by_pet(owner: "Owner", pet_name: str) -> List[Task]:
        """Return all tasks (pending and completed) belonging to a named pet.

        Comparison is case-insensitive. Returns an empty list if the pet
        is not found in the owner's household.
        """
        for pet in owner.get_pets():
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []

    @staticmethod
    def get_due_tasks(pet: Pet, day_of_week: int) -> List[Task]:
        """Return pending tasks due on the given day of week (0=Mon … 6=Sun).

        Recurrence rules:
          - "daily"     → always due
          - "weekly"    → due on Mondays only (day_of_week == 0)
          - "as-needed" → never auto-scheduled; must be added manually

        Uses a set of eligible frequencies so adding new recurrence types
        later only requires extending that set, not adding another elif branch.
        """
        eligible = {"daily"} | ({"weekly"} if day_of_week == 0 else set())
        return [t for t in pet.get_pending_tasks() if t.frequency in eligible]

    @staticmethod
    def _to_minutes(hhmm: str) -> int:
        """Convert an "HH:MM" string to total minutes from midnight."""
        hours, mins = hhmm.split(":")
        return int(hours) * 60 + int(mins)

    @staticmethod
    def detect_conflicts(tasks: List[Task]) -> List[Tuple[Task, Task]]:
        """Find pairs of tasks whose time windows overlap.

        Only tasks with a start_time are checked. Two tasks conflict when
        one starts before the other finishes:
            A.start < B.end  AND  B.start < A.end
        start_time strings are parsed to minutes for the arithmetic.
        Returns a list of (task_a, task_b) pairs (each pair appears once).
        """
        timed = [t for t in tasks if t.start_time is not None]
        conflicts = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a, b = timed[i], timed[j]
                a_start = Scheduler._to_minutes(a.start_time)
                b_start = Scheduler._to_minutes(b.start_time)
                a_end = a_start + a.duration_minutes
                b_end = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    conflicts.append((a, b))
        return conflicts

    @staticmethod
    def warn_conflicts(tasks: List[Task], label: str = "") -> List[str]:
        """Lightweight conflict check that returns warning strings instead of raising.

        Calls detect_conflicts() internally, then formats each overlapping pair
        as a human-readable WARNING line. Returns an empty list when there are
        no conflicts, so callers can check `if warnings:` without try/except.

        Args:
            tasks: flat list of Task objects to check (can span multiple pets).
            label: optional prefix shown in each warning, e.g. a pet name.
        """
        pairs = Scheduler.detect_conflicts(tasks)
        warnings = []
        prefix = f"[{label}] " if label else ""
        for a, b in pairs:
            a_end_min = Scheduler._to_minutes(a.start_time) + a.duration_minutes
            b_end_min = Scheduler._to_minutes(b.start_time) + b.duration_minutes
            a_end = f"{a_end_min // 60:02d}:{a_end_min % 60:02d}"
            b_end = f"{b_end_min // 60:02d}:{b_end_min % 60:02d}"
            warnings.append(
                f"WARNING: {prefix}'{a.name}' ({a.start_time}-{a_end}) "
                f"overlaps '{b.name}' ({b.start_time}-{b_end})"
            )
        return warnings

    @staticmethod
    def warn_cross_pet_conflicts(owner: "Owner") -> List[str]:
        """Check for scheduling conflicts across all pets in the owner's household.

        Collects every timed pending task from every pet into one list, then
        checks every unique pair with itertools.combinations — which reads as
        "every combination of 2 items" and removes the need for index bookkeeping.
        Each warning labels both pets so the owner knows whose tasks clash.
        """
        # (pet_name, task) pairs for all timed pending tasks across the household
        tagged: List[Tuple[str, Task]] = [
            (pet.name, task)
            for pet in owner.get_pets()
            for task in pet.get_pending_tasks()
            if task.start_time is not None
        ]

        all_warnings: List[str] = []
        for (pet_a, a), (pet_b, b) in combinations(tagged, 2):
            a_start = Scheduler._to_minutes(a.start_time)
            b_start = Scheduler._to_minutes(b.start_time)
            a_end_min = a_start + a.duration_minutes
            b_end_min = b_start + b.duration_minutes
            if a_start < b_end_min and b_start < a_end_min:
                a_end = f"{a_end_min // 60:02d}:{a_end_min % 60:02d}"
                b_end = f"{b_end_min // 60:02d}:{b_end_min % 60:02d}"
                all_warnings.append(
                    f"WARNING: [{pet_a}] '{a.name}' ({a.start_time}-{a_end}) "
                    f"overlaps [{pet_b}] '{b.name}' ({b.start_time}-{b_end})"
                )
        return all_warnings

    # ------------------------------------------------------------------
    # Challenge 1: Advanced algorithmic capabilities
    # ------------------------------------------------------------------

    @staticmethod
    def auto_assign_times(tasks: List[Task], day_start: str = "08:00") -> List[Task]:
        """Assign start times to untimed tasks, producing a conflict-free timeline.

        Algorithm
        ---------
        1. Sort all tasks by priority (highest first).
        2. Walk through them with a time *cursor* that starts at ``day_start``.
        3. If a task already has a ``start_time``, keep it and advance the cursor
           past its end (so the next untimed task doesn't overlap it).
        4. If a task has no ``start_time``, assign the current cursor position,
           then advance the cursor by the task's duration.

        A new Task object is returned for each untimed task so the originals
        are never mutated. Tasks that already had a start_time are returned
        as-is.

        Args:
            tasks:     List of Task objects to schedule.
            day_start: Earliest allowed start time in ``"HH:MM"`` format.

        Returns:
            A list of Task objects in priority order, all with a start_time set.
        """
        cursor = Scheduler._to_minutes(day_start)
        result: List[Task] = []

        for task in sorted(tasks, key=lambda t: t.priority):
            if task.start_time is not None:
                # Fixed task — keep its time, advance cursor past its end
                task_end = Scheduler._to_minutes(task.start_time) + task.duration_minutes
                cursor = max(cursor, task_end)
                result.append(task)
            else:
                # Untimed task — slot it at the current cursor
                assigned = f"{cursor // 60:02d}:{cursor % 60:02d}"
                cursor += task.duration_minutes
                result.append(Task(
                    name=task.name,
                    category=task.category,
                    duration_minutes=task.duration_minutes,
                    priority=task.priority,
                    frequency=task.frequency,
                    completed=task.completed,
                    start_time=assigned,
                    due_date=task.due_date,
                ))

        return result

    @staticmethod
    def find_next_slot(
        tasks: List[Task],
        duration_minutes: int,
        day_start: str = "08:00",
        day_end: str = "22:00",
    ) -> Optional[str]:
        """Find the earliest free gap in the day that fits a task of the given duration.

        Algorithm
        ---------
        Only tasks with a ``start_time`` contribute to the occupied timeline.
        The method:

        1. Converts each timed task to a ``(start, end)`` interval in minutes.
        2. Merges overlapping intervals so a run of back-to-back tasks counts
           as one continuous block.
        3. Scans the gaps between blocks (and the gap before the first block
           and after the last) looking for the first one wide enough.

        Returns the gap's start as an ``"HH:MM"`` string, or ``None`` if the
        entire day is too full.

        Args:
            tasks:            Tasks already on the schedule (timed and untimed).
            duration_minutes: How long the new task needs.
            day_start:        Earliest the new task may start (``"HH:MM"``).
            day_end:          Latest the new task may end (``"HH:MM"``).

        Returns:
            ``"HH:MM"`` start time for the first available slot, or ``None``.
        """
        day_start_min = Scheduler._to_minutes(day_start)
        day_end_min = Scheduler._to_minutes(day_end)

        # Build and sort intervals from all timed tasks
        intervals = sorted(
            [
                (
                    Scheduler._to_minutes(t.start_time),
                    Scheduler._to_minutes(t.start_time) + t.duration_minutes,
                )
                for t in tasks
                if t.start_time is not None
            ],
            key=lambda iv: iv[0],
        )

        # Merge overlapping/adjacent intervals into contiguous blocks
        merged: List[Tuple[int, int]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # Scan for a gap wide enough to fit duration_minutes
        cursor = day_start_min
        for block_start, block_end in merged:
            gap = block_start - cursor
            if gap >= duration_minutes:
                return f"{cursor // 60:02d}:{cursor % 60:02d}"
            cursor = max(cursor, block_end)

        # Check the gap after the last block
        if day_end_min - cursor >= duration_minutes:
            return f"{cursor // 60:02d}:{cursor % 60:02d}"

        return None  # No slot fits within the day
