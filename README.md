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

## Smarter Scheduling

Four algorithmic improvements were added to make the scheduler more useful for
real pet-care routines:

**Sorting by time** — `Scheduler.sort_by_time(tasks)` orders any task list
chronologically using each task's `start_time` field (`"HH:MM"` format). Tasks
with no assigned time are placed at the end. Because zero-padded hour strings
sort identically to numeric comparison, no datetime conversion is needed.

**Filtering by pet or status** — `Scheduler.filter_tasks(tasks, pet_name=..., completed=...)`
lets you narrow any task list to a single pet, to only pending tasks, only
completed tasks, or any combination. Both parameters are optional keyword-only
arguments so callers only specify what they need.

**Recurring task auto-creation** — When `Pet.mark_task_complete(title)` is
called, it automatically queues the next occurrence for recurring tasks using
Python's `timedelta`: daily tasks reappear the next day, weekly tasks reappear
seven days later. One-off ("as-needed") tasks are simply completed with no
follow-up. No manual re-entry is required.

**Conflict detection** — `Scheduler.detect_conflicts(tasks)` scans the task list
and returns a plain list of warning strings for any two tasks that share the same
date and start time. It never raises an exception — callers decide how to display
or act on the warnings. The method uses exact time-slot matching (not duration
overlap); see `reflection.md §2b` for the reasoning behind that tradeoff.

---

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
