from dataclasses import dataclass
from typing import Optional


@dataclass
class Pet:
    """Holds basic profile data for a pet. Pure data — no scheduling logic."""
    name: str
    species: str
    age: int


@dataclass
class Task:
    """Represents one care activity with the duration and priority the scheduler needs."""
    title: str
    duration_minutes: int
    priority: str          # "low", "medium", or "high"
    category: str          # e.g. "walk", "feeding", "meds", "grooming", "enrichment"

    def is_high_priority(self) -> bool:
        pass


class Owner:
    """Holds owner profile and time budget. Owns exactly one Pet."""

    def __init__(self, name: str, available_minutes: int, pet: Optional[Pet] = None):
        self.name = name
        self.available_minutes = available_minutes
        self.pet = pet

    def add_pet(self, pet: Pet) -> None:
        pass


class Scheduler:
    """Reads the owner's time budget and task list, then produces a DailyPlan."""

    def __init__(self, owner: Owner, tasks: list[Task]):
        self.owner = owner
        self.tasks = tasks

    def generate_plan(self) -> "DailyPlan":
        pass


class DailyPlan:
    """The output of Scheduler. Knows what ran, what was skipped, and why."""

    def __init__(
        self,
        owner: Owner,
        scheduled_tasks: list[Task],
        skipped_tasks: list[Task],
        total_duration: int,
        skip_reasons: dict[str, str],   # task title -> reason it was skipped
    ):
        self.owner = owner
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.total_duration = total_duration
        self.skip_reasons = skip_reasons

    def explain(self) -> str:
        pass
