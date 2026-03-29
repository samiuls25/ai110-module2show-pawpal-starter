from __future__ import annotations
from dataclasses import dataclass

# Maps priority label to a numeric weight for sorting.
_PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Task:
    """One pet care activity. Tracks what needs doing, how long it takes, and whether it's done."""

    title: str
    duration_minutes: int
    priority: str       # "low", "medium", or "high"
    category: str       # "walk", "feeding", "meds", "grooming", "enrichment"
    frequency: str      # "daily", "weekly", "as-needed"
    completed: bool = False

    def is_high_priority(self) -> bool:
        """Return True if this task's priority is 'high'."""
        return self.priority == "high"

    def mark_complete(self) -> None:
        """Mark this task as done so it is excluded from future plans."""
        self.completed = True


class Pet:
    """Stores a pet's profile and owns its list of care tasks."""

    def __init__(self, name: str, species: str, age: int):
        self.name = name
        self.species = species
        self.age = age
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Append a Task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove all tasks whose title matches the given string."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been marked complete."""
        return [t for t in self.tasks if not t.completed]


class Owner:
    """Manages one or more pets and provides the Scheduler access to all their tasks."""

    def __init__(self, name: str, available_minutes: int):
        self.name = name
        self.available_minutes = available_minutes
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a Pet to this owner's list of pets."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove the pet with the given name from the owner's list."""
        self.pets = [p for p in self.pets if p.name != name]

    def get_all_tasks(self) -> list[Task]:
        """Collect pending tasks across every pet the owner has."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_pending_tasks())
        return tasks


class Scheduler:
    """The scheduling brain. Retrieves tasks from the Owner, sorts by priority,
    and greedily builds a plan that fits within the owner's time budget."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def generate_plan(self) -> "DailyPlan":
        """Sort all pending tasks by priority and greedily build a plan within the time budget."""
        all_tasks = self.owner.get_all_tasks()

        # Sort: highest priority first; among ties, shorter tasks first so more tasks fit.
        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (_PRIORITY_WEIGHT.get(t.priority, 0), -t.duration_minutes),
            reverse=True,
        )

        scheduled: list[Task] = []
        skipped: list[Task] = []
        skip_reasons: dict[str, str] = {}
        time_remaining = self.owner.available_minutes

        for task in sorted_tasks:
            if task.duration_minutes <= time_remaining:
                scheduled.append(task)
                time_remaining -= task.duration_minutes
            else:
                skipped.append(task)
                skip_reasons[task.title] = (
                    f"needs {task.duration_minutes} min but only "
                    f"{time_remaining} min remaining in the budget"
                )

        total_duration = self.owner.available_minutes - time_remaining
        return DailyPlan(self.owner, scheduled, skipped, total_duration, skip_reasons)


class DailyPlan:
    """The Scheduler's output. Holds what was scheduled, what was skipped, and why."""

    def __init__(
        self,
        owner: Owner,
        scheduled_tasks: list[Task],
        skipped_tasks: list[Task],
        total_duration: int,
        skip_reasons: dict[str, str],
    ):
        self.owner = owner
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.total_duration = total_duration
        self.skip_reasons = skip_reasons

    def explain(self) -> str:
        """Return a human-readable summary of what was scheduled and why items were skipped."""
        lines = [
            f"Daily plan for {self.owner.name}",
            f"Time budget: {self.owner.available_minutes} min  |  "
            f"Time used: {self.total_duration} min\n",
        ]

        if self.scheduled_tasks:
            lines.append("Scheduled:")
            for task in self.scheduled_tasks:
                lines.append(
                    f"  [{task.priority.upper():6}] {task.title} "
                    f"— {task.duration_minutes} min ({task.category})"
                )
        else:
            lines.append("No tasks could be scheduled.")

        if self.skipped_tasks:
            lines.append("\nSkipped:")
            for task in self.skipped_tasks:
                reason = self.skip_reasons.get(task.title, "unknown reason")
                lines.append(f"  {task.title} — {reason}")

        return "\n".join(lines)
