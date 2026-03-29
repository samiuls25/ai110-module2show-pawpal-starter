from __future__ import annotations
from dataclasses import dataclass

# Maps priority label to a numeric weight for sorting.
_PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}

# Daily tasks outrank weekly/as-needed tasks of equal priority.
_FREQUENCY_WEIGHT = {"daily": 2, "weekly": 1, "as-needed": 0}


def filter_by_category(tasks: list["Task"], category: str) -> list["Task"]:
    """Return tasks whose category matches the given string."""
    return [t for t in tasks if t.category == category]


def filter_by_frequency(tasks: list["Task"], frequency: str) -> list["Task"]:
    """Return tasks whose frequency matches the given string."""
    return [t for t in tasks if t.frequency == frequency]


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
        """Append a Task to this pet's task list.

        Raises ValueError if a task with the same title already exists,
        or if a second daily 'meds' task is added (likely a duplicate).
        """
        if any(t.title == task.title for t in self.tasks):
            raise ValueError(f"Task '{task.title}' already exists for {self.name}.")
        if task.category == "meds" and task.frequency == "daily":
            if any(t.category == "meds" and t.frequency == "daily" for t in self.tasks):
                raise ValueError(
                    f"{self.name} already has a daily medication task. "
                    "Add a distinct title if this is a separate medication."
                )
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove all tasks whose title matches the given string."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been marked complete."""
        return [t for t in self.tasks if not t.completed]

    def get_daily_tasks(self) -> list[Task]:
        """Return pending tasks that must be done every day."""
        return [t for t in self.tasks if t.frequency == "daily" and not t.completed]


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

    def get_tasks_for_pet(self, pet_name: str) -> list[Task]:
        """Return pending tasks for a single named pet."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet.get_pending_tasks()
        return []


class Scheduler:
    """The scheduling brain. Retrieves tasks from the Owner, sorts by priority,
    and greedily builds a plan that fits within the owner's time budget."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def generate_plan(self) -> "DailyPlan":
        """Build a daily plan using two-pass scheduling and frequency-aware sorting.

        Pass 1: schedule all daily tasks first (non-negotiable).
        Pass 2: fill remaining time with weekly/as-needed tasks.
        Within each pass, tasks are sorted by priority then frequency then duration.
        """
        all_tasks = self.owner.get_all_tasks()

        # Warn early if total task time far exceeds the available budget.
        total_task_minutes = sum(t.duration_minutes for t in all_tasks)
        overcommit_warning: str | None = None
        if total_task_minutes > self.owner.available_minutes * 1.5:
            overcommit_warning = (
                f"Total task time ({total_task_minutes} min) is more than 1.5x "
                f"your budget ({self.owner.available_minutes} min). "
                "Many tasks will be skipped — consider reducing tasks or increasing available time."
            )

        def sort_key(t: Task) -> tuple:
            # Higher values = scheduled first.
            # Tie-break on title for a deterministic, stable order.
            return (
                _PRIORITY_WEIGHT.get(t.priority, 0),
                _FREQUENCY_WEIGHT.get(t.frequency, 0),
                -t.duration_minutes,   # shorter tasks first among equals
                t.title,
            )

        daily_tasks = sorted(
            filter_by_frequency(all_tasks, "daily"), key=sort_key, reverse=True
        )
        other_tasks = sorted(
            [t for t in all_tasks if t.frequency != "daily"], key=sort_key, reverse=True
        )

        scheduled: list[Task] = []
        skipped: list[Task] = []
        skip_reasons: dict[str, str] = {}
        time_remaining = self.owner.available_minutes

        # Pass 1 — daily tasks always get first shot at the budget.
        for task in daily_tasks:
            if task.duration_minutes <= time_remaining:
                scheduled.append(task)
                time_remaining -= task.duration_minutes
            else:
                skipped.append(task)
                skip_reasons[task.title] = (
                    f"needs {task.duration_minutes} min but only "
                    f"{time_remaining} min remaining in the budget "
                    f"[DAILY — reschedule immediately]"
                )

        # Pass 2 — weekly / as-needed fill whatever time is left.
        for task in other_tasks:
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
        return DailyPlan(
            self.owner, scheduled, skipped, total_duration, skip_reasons, overcommit_warning
        )


class DailyPlan:
    """The Scheduler's output. Holds what was scheduled, what was skipped, and why."""

    def __init__(
        self,
        owner: Owner,
        scheduled_tasks: list[Task],
        skipped_tasks: list[Task],
        total_duration: int,
        skip_reasons: dict[str, str],
        overcommit_warning: str | None = None,
    ):
        self.owner = owner
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.total_duration = total_duration
        self.skip_reasons = skip_reasons
        self.overcommit_warning = overcommit_warning
        self.load_warnings: list[str] = self._check_per_pet_load()

    def _check_per_pet_load(self) -> list[str]:
        """Warn if any single pet consumes a disproportionate share of the schedule."""
        if not self.owner.pets:
            return []
        fair_share = self.owner.available_minutes / len(self.owner.pets)
        warnings: list[str] = []
        for pet in self.owner.pets:
            pet_minutes = sum(
                t.duration_minutes for t in self.scheduled_tasks if t in pet.tasks
            )
            if pet_minutes > fair_share * 1.5:
                warnings.append(
                    f"Warning: {pet.name} has {pet_minutes} min scheduled "
                    f"(fair share ≈ {int(fair_share)} min) — consider redistributing."
                )
        return warnings

    def explain(self) -> str:
        """Return a human-readable summary of what was scheduled and why items were skipped."""
        lines = [
            f"Daily plan for {self.owner.name}",
            f"Time budget: {self.owner.available_minutes} min  |  "
            f"Time used: {self.total_duration} min\n",
        ]

        if self.overcommit_warning:
            lines.append(f"⚠  {self.overcommit_warning}\n")

        for w in self.load_warnings:
            lines.append(f"⚠  {w}\n")

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
