from dataclasses import dataclass, field
from typing import List


@dataclass
class Task:
    name: str
    category: str          # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: int          # 1 = highest priority
    completed: bool = False

    def mark_complete(self) -> None:
        self.completed = True


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def get_tasks(self) -> List[Task]:
        return self.tasks


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


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.scheduled_tasks: List[Task] = []
        self.skipped_tasks: List[Task] = []

    def generate_plan(self, pet: Pet) -> List[Task]:
        pass

    def explain_plan(self) -> str:
        pass

    def get_total_duration(self) -> int:
        pass
