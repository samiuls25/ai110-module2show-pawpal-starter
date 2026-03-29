from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta

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
    priority: str           # "low", "medium", or "high"
    category: str           # "walk", "feeding", "meds", "grooming", "enrichment"
    frequency: str          # "daily", "weekly", "as-needed"
    start_time: str = ""    # Optional "HH:MM" scheduled start, e.g. "08:30"
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def is_high_priority(self) -> bool:
        """Return True if this task's priority is 'high'."""
        return self.priority == "high"

    def mark_complete(self) -> "Task | None":
        """Mark this task as done and return a new Task for the next occurrence.

        For recurring tasks (daily/weekly), Python's timedelta calculates the
        next due_date automatically:
          - daily  → due_date + timedelta(days=1)
          - weekly → due_date + timedelta(weeks=1)
        Returns None for "as-needed" tasks (no automatic recurrence).
        """
        self.completed = True
        if self.frequency == "daily":
            return Task(
                title=self.title,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                category=self.category,
                frequency=self.frequency,
                start_time=self.start_time,
                due_date=self.due_date + timedelta(days=1),
            )
        if self.frequency == "weekly":
            return Task(
                title=self.title,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                category=self.category,
                frequency=self.frequency,
                start_time=self.start_time,
                due_date=self.due_date + timedelta(weeks=1),
            )
        return None


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
        # Block exact duplicates (same title AND same due date).
        if any(t.title == task.title and t.due_date == task.due_date for t in self.tasks):
            raise ValueError(
                f"Task '{task.title}' due {task.due_date} already exists for {self.name}."
            )
        # Block a second *distinct* daily meds task (different title is fine).
        if task.category == "meds" and task.frequency == "daily":
            if any(
                t.category == "meds"
                and t.frequency == "daily"
                and t.title != task.title
                for t in self.tasks
            ):
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

    def mark_task_complete(self, title: str) -> "Task | None":
        """Mark the first matching pending task complete and auto-queue its next occurrence.

        Delegates to Task.mark_complete(), which uses Python's timedelta to calculate
        the next due_date:
            - "daily"  tasks → due_date + timedelta(days=1)
            - "weekly" tasks → due_date + timedelta(weeks=1)
            - "as-needed"   → no recurrence; returns None

        The new Task (if any) is appended to this pet's task list immediately, so it
        will appear in the next call to get_pending_tasks() without any extra steps.

        Args:
            title: The exact title of the task to mark complete. If multiple pending
                   tasks share the same title, only the first one found is affected.

        Returns:
            The newly created Task for the next occurrence, or None if the task is
            "as-needed" or no matching pending task was found.
        """
        for task in self.tasks:
            if task.title == title and not task.completed:
                next_task = task.mark_complete()
                if next_task is not None:
                    self.tasks.append(next_task)
                return next_task
        return None


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

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return a new list of tasks sorted by scheduled start_time in ascending order.

        Sorting strategy:
            Python's built-in sorted() is called with a lambda key that reads each
            task's start_time string (format "HH:MM"). Zero-padded hour digits
            sort identically under lexicographic and numeric comparison, so plain
            string sorting produces the correct chronological order without
            converting to datetime objects.

            Tasks that have no start_time (empty string "") are assigned the
            sentinel value "99:99" so they always sort after every real time slot.
            The explicit ternary (``if t.start_time else``) is used rather than
            the shorter ``t.start_time or "99:99"`` because empty-string falsiness
            is not immediately obvious to all readers.

        Args:
            tasks: Any list of Task objects (pending, completed, or mixed).

        Returns:
            A new sorted list; the original list is not modified.

        Example:
            sorted_tasks = scheduler.sort_by_time(owner.get_all_tasks())
            # → tasks ordered 07:30, 08:00, 09:00, 18:00, then unscheduled
        """
        return sorted(
            tasks,
            key=lambda t: t.start_time if t.start_time else "99:99",
        )

    def filter_tasks(
        self,
        tasks: list[Task],
        *,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """Return a filtered subset of tasks by pet name, completion status, or both.

        Both filters are optional and can be combined. Passing neither returns the
        original list unchanged.

        Implementation note:
            Pet membership is resolved by building a dict from Python object id()
            to pet name. Using id() avoids modifying the Task dataclass and handles
            cases where two tasks share the same title but belong to different pets.

        Args:
            tasks:     The task list to filter (e.g. from owner.get_all_tasks()).
            pet_name:  If given, keep only tasks that belong to this pet's task list.
                       Unrecognised names produce an empty list (no error raised).
            completed: If True, keep only tasks where task.completed is True.
                       If False, keep only tasks where task.completed is False.
                       If None (default), completion status is not filtered.

        Returns:
            A new filtered list; the original list is not modified.

        Examples:
            # All pending tasks for Mochi
            scheduler.filter_tasks(all_tasks, pet_name="Mochi", completed=False)

            # Every completed task across all pets
            scheduler.filter_tasks(all_tasks, completed=True)
        """
        # Build a quick lookup: task object → pet name.
        task_to_pet: dict[int, str] = {}
        for pet in self.owner.pets:
            for t in pet.tasks:
                task_to_pet[id(t)] = pet.name

        result = tasks
        if pet_name is not None:
            result = [t for t in result if task_to_pet.get(id(t)) == pet_name]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def detect_conflicts(self, tasks: list[Task]) -> list[str]:
        """Return a list of human-readable warning strings for scheduling conflicts.

        A conflict is defined as two or more tasks that share the same due_date
        AND the same start_time. Tasks without a start_time are skipped (they
        have no fixed slot and therefore cannot collide).

        Detection strategy (lightweight — no crash on conflict):
            1. Build a dict mapping each Task's object id() to its owner's pet name,
               so warnings can name the affected pet.
            2. Use a defaultdict to bucket tasks by the tuple (due_date, start_time).
               Bucketing by both fields means a daily task at 09:00 today does NOT
               conflict with its auto-created successor at 09:00 tomorrow.
            3. Any bucket with more than one task produces one warning string.
               The function returns a plain list — callers decide how to display it.

        Known tradeoff:
            Conflict detection checks for *exact* start_time overlap only. Two tasks
            whose durations overlap (e.g., a 30-min task at 08:45 and a 60-min task
            at 09:00) are NOT flagged. See reflection.md §2b for rationale.

        Args:
            tasks: Any list of Task objects to scan (pending, completed, or mixed).

        Returns:
            A list of warning strings, one per conflicting time slot.
            Returns an empty list when no conflicts exist.

        Example:
            conflicts = scheduler.detect_conflicts(owner.get_all_tasks())
            for warning in conflicts:
                print(warning)
        """
        warnings: list[str] = []
        # Build a quick lookup: task object → pet name.
        task_to_pet: dict[int, str] = {}
        for pet in self.owner.pets:
            for t in pet.tasks:
                task_to_pet[id(t)] = pet.name

        # Bucket by (due_date, start_time) — tasks on different days cannot conflict.
        from collections import defaultdict
        buckets: dict[tuple, list[Task]] = defaultdict(list)
        for task in tasks:
            if not task.start_time:
                continue
            buckets[(task.due_date, task.start_time)].append(task)

        for (day, time_slot), conflicting in buckets.items():
            if len(conflicting) > 1:
                names = ", ".join(
                    f"'{t.title}' ({task_to_pet.get(id(t), '?')})"
                    for t in conflicting
                )
                warnings.append(
                    f"Conflict on {day} at {time_slot}: {names} are all scheduled at the same time."
                )
        return warnings

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
