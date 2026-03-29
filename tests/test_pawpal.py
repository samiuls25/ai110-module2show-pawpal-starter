from pawpal_system import Pet, Task


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
