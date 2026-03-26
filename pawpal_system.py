from dataclasses import dataclass, field
from typing import List


@dataclass
class Task:
    name: str
    category: str          # "walk", "feed", "meds", "grooming", "enrichment", etc.
    duration_minutes: int
    priority: int          # 1 = highest priority
    frequency: str = "daily"   # "daily", "weekly", "as-needed"
    completed: bool = False

    def mark_complete(self) -> None:
        self.completed = True

    def __str__(self) -> str:
        status = "done" if self.completed else "pending"
        return (
            f"[P{self.priority}] {self.name} ({self.category}) "
            f"- {self.duration_minutes} min, {self.frequency} [{status}]"
        )


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task_name: str) -> bool:
        """Remove a task by name. Returns True if found and removed."""
        for task in self.tasks:
            if task.name.lower() == task_name.lower():
                self.tasks.remove(task)
                return True
        return False

    def get_tasks(self) -> List[Task]:
        return self.tasks

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if not t.completed]

    def __str__(self) -> str:
        return f"{self.name} ({self.species}, {self.breed}, age {self.age})"


@dataclass
class Owner:
    name: str
    available_minutes: int
    preferences: List[str] = field(default_factory=list)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def get_pets(self) -> List[Pet]:
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
    def __init__(self, owner: Owner):
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

    def mark_task_complete(self, task_name: str) -> bool:
        """Mark a scheduled task complete by name. Returns True if found."""
        for task in self.scheduled_tasks:
            if task.name.lower() == task_name.lower():
                task.mark_complete()
                return True
        return False
