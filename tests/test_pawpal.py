from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(**kwargs) -> Task:
    """Return a Task with sensible defaults; override any field via kwargs."""
    defaults = dict(
        title="Test task",
        duration_minutes=10,
        priority="medium",
        category="walk",
        frequency="daily",
        completed=False,
    )
    return Task(**{**defaults, **kwargs})


def make_scheduler(available_minutes: int = 120) -> tuple[Owner, Pet, Scheduler]:
    """Return a wired-up (owner, pet, scheduler) triple for use in tests."""
    owner = Owner(name="Alex", available_minutes=available_minutes)
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    return owner, pet, scheduler


# ---------------------------------------------------------------------------
# Existing baseline tests (kept intact)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """Calling mark_complete() should set completed to True."""
    task = make_task(title="Morning walk")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a Task to a Pet should increase the pet's task list by one."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Breakfast"))
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# 1. Sorting Correctness
# ---------------------------------------------------------------------------

def test_sort_by_time_chronological_order():
    """Tasks should be returned in ascending HH:MM order."""
    _, _, scheduler = make_scheduler()
    tasks = [
        make_task(title="Evening meds", start_time="18:00"),
        make_task(title="Morning walk", start_time="07:30"),
        make_task(title="Lunch feeding", start_time="12:00"),
        make_task(title="Early feeding", start_time="08:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    times = [t.start_time for t in result]
    assert times == ["07:30", "08:00", "12:00", "18:00"]


def test_sort_by_time_unscheduled_tasks_sort_last():
    """Tasks with no start_time must appear after all timed tasks."""
    _, _, scheduler = make_scheduler()
    tasks = [
        make_task(title="Unscheduled grooming", start_time=""),
        make_task(title="Morning walk", start_time="07:30"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert result[0].title == "Morning walk"
    assert result[1].title == "Unscheduled grooming"


def test_sort_by_time_empty_list():
    """sort_by_time on an empty list should return an empty list (no crash)."""
    _, _, scheduler = make_scheduler()
    assert scheduler.sort_by_time([]) == []


def test_sort_by_time_preserves_all_tasks():
    """Sorting should not drop or duplicate any task."""
    _, _, scheduler = make_scheduler()
    tasks = [make_task(title=f"Task {i}", start_time=f"0{i}:00") for i in range(1, 6)]
    result = scheduler.sort_by_time(tasks)
    assert len(result) == 5


# ---------------------------------------------------------------------------
# 2. Recurrence Logic
# ---------------------------------------------------------------------------

def test_daily_task_creates_next_day_task():
    """Completing a daily task should auto-queue a task for the next day."""
    today = date.today()
    _, pet, _ = make_scheduler()
    pet.add_task(make_task(title="Morning walk", frequency="daily", due_date=today))

    next_task = pet.mark_task_complete("Morning walk")

    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.frequency == "daily"
    assert not next_task.completed


def test_weekly_task_creates_next_week_task():
    """Completing a weekly task should auto-queue a task 7 days later."""
    today = date.today()
    _, pet, _ = make_scheduler()
    pet.add_task(make_task(title="Bath time", frequency="weekly", due_date=today))

    next_task = pet.mark_task_complete("Bath time")

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_as_needed_task_returns_none():
    """As-needed tasks should not produce a successor task."""
    _, pet, _ = make_scheduler()
    pet.add_task(make_task(title="Vet visit", frequency="as-needed"))

    next_task = pet.mark_task_complete("Vet visit")

    assert next_task is None


def test_recurring_task_appended_to_pet_tasks():
    """The new recurrence task should immediately appear in pet.tasks."""
    today = date.today()
    _, pet, _ = make_scheduler()
    pet.add_task(make_task(title="Morning walk", frequency="daily", due_date=today))

    initial_count = len(pet.tasks)
    pet.mark_task_complete("Morning walk")

    assert len(pet.tasks) == initial_count + 1


def test_completed_task_not_in_pending():
    """After completion, the original task should not appear in get_pending_tasks()."""
    _, pet, _ = make_scheduler()
    pet.add_task(make_task(title="Evening walk", frequency="daily"))
    pet.mark_task_complete("Evening walk")

    # The completed original is gone; the new recurrence task is pending.
    completed = [t for t in pet.tasks if t.title == "Evening walk" and t.completed]
    assert len(completed) == 1


# ---------------------------------------------------------------------------
# 3. Conflict Detection
# ---------------------------------------------------------------------------

def test_detect_conflicts_same_time_same_date():
    """Two tasks sharing the same date + start_time should raise a conflict."""
    today = date.today()
    owner, pet, scheduler = make_scheduler()
    t1 = make_task(title="Walk", start_time="09:00", due_date=today)
    t2 = make_task(title="Feeding", start_time="09:00", due_date=today)
    pet.add_task(t1)
    pet.add_task(t2)

    conflicts = scheduler.detect_conflicts(owner.get_all_tasks())

    assert len(conflicts) == 1
    assert "09:00" in conflicts[0]


def test_detect_conflicts_different_times_no_conflict():
    """Tasks at different times on the same day should not conflict."""
    today = date.today()
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(title="Walk", start_time="09:00", due_date=today))
    pet.add_task(make_task(title="Feeding", start_time="10:00", due_date=today))

    conflicts = scheduler.detect_conflicts(owner.get_all_tasks())

    assert conflicts == []


def test_detect_conflicts_same_time_different_dates_no_conflict():
    """Same start_time on different dates must NOT be flagged as a conflict."""
    today = date.today()
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(title="Walk", start_time="09:00", due_date=today))
    pet.add_task(
        make_task(title="Walk", start_time="09:00", due_date=today + timedelta(days=1))
    )

    conflicts = scheduler.detect_conflicts(owner.get_all_tasks())

    assert conflicts == []


def test_detect_conflicts_no_start_time_ignored():
    """Tasks with no start_time should be excluded from conflict detection."""
    today = date.today()
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(title="Walk", start_time="", due_date=today))
    pet.add_task(make_task(title="Feeding", start_time="", due_date=today))

    conflicts = scheduler.detect_conflicts(owner.get_all_tasks())

    assert conflicts == []


def test_detect_conflicts_empty_schedule():
    """detect_conflicts on an empty list should return an empty list."""
    _, _, scheduler = make_scheduler()
    assert scheduler.detect_conflicts([]) == []


# ---------------------------------------------------------------------------
# 4. Edge Cases
# ---------------------------------------------------------------------------

def test_pet_with_no_tasks_returns_empty_pending():
    """A brand-new pet should have zero pending tasks."""
    pet = Pet(name="Ghost", species="cat", age=1)
    assert pet.get_pending_tasks() == []


def test_owner_with_no_pets_returns_empty_tasks():
    """An owner with no pets should return no tasks."""
    owner = Owner(name="Sam", available_minutes=60)
    assert owner.get_all_tasks() == []


def test_add_duplicate_task_raises():
    """Adding a task with the same title and same due_date should raise ValueError."""
    pet = Pet(name="Mochi", species="dog", age=3)
    today = date.today()
    pet.add_task(make_task(title="Morning walk", due_date=today))

    with pytest.raises(ValueError):
        pet.add_task(make_task(title="Morning walk", due_date=today))


def test_is_high_priority_flag():
    """is_high_priority() should return True only for priority='high'."""
    high = make_task(priority="high")
    medium = make_task(priority="medium")
    assert high.is_high_priority() is True
    assert medium.is_high_priority() is False


def test_mark_task_complete_unknown_title_returns_none():
    """mark_task_complete with a nonexistent title should return None silently."""
    _, pet, _ = make_scheduler()
    result = pet.mark_task_complete("Nonexistent task")
    assert result is None
