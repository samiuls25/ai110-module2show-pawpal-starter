from pawpal_system import Owner, Pet, Task, Scheduler

WIDTH = 60
PRIORITY_ICON = {"high": "(!)", "medium": "(~)", "low": "( )"}

# ── Setup ──────────────────────────────────────────────────────────────────────

owner = Owner(name="Jordan", available_minutes=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Tasks added OUT OF ORDER on purpose — sort_by_time will fix this.
# Mochi's tasks
mochi.add_task(Task("Evening run",     45, "medium", "walk",       "daily",     start_time="18:00"))
mochi.add_task(Task("Morning walk",    30, "high",   "walk",       "daily",     start_time="07:30"))
mochi.add_task(Task("Breakfast",       10, "high",   "feeding",    "daily",     start_time="08:00"))

# Luna's tasks — "Medication" and "Puzzle feeder" both at 09:00 → conflict!
luna.add_task(Task("Medication",        5, "high",   "meds",       "daily",     start_time="09:00"))
luna.add_task(Task("Grooming brush",   15, "medium", "grooming",   "weekly",    start_time="11:00"))
luna.add_task(Task("Puzzle feeder",    20, "low",    "enrichment", "as-needed", start_time="09:00"))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler(owner)
all_tasks = owner.get_all_tasks()

# ── 1. Sorting by start_time ───────────────────────────────────────────────────

print("=" * WIDTH)
print("  1. TASKS SORTED BY TIME (HH:MM)")
print("=" * WIDTH)
sorted_tasks = scheduler.sort_by_time(all_tasks)
for task in sorted_tasks:
    time_label = task.start_time if task.start_time else "--:--"
    icon = PRIORITY_ICON.get(task.priority, "   ")
    print(f"  {time_label}  {icon}  {task.title:<28} {task.duration_minutes:>3} min")

# ── 2. Filtering ───────────────────────────────────────────────────────────────

print()
print("=" * WIDTH)
print("  2. FILTERING")
print("=" * WIDTH)

mochi_tasks = scheduler.filter_tasks(all_tasks, pet_name="Mochi")
print(f"\n  Mochi's tasks ({len(mochi_tasks)} total):")
for t in mochi_tasks:
    print(f"    - {t.title}")

pending = scheduler.filter_tasks(all_tasks, completed=False)
print(f"\n  Pending tasks across all pets ({len(pending)} total):")
for t in pending:
    print(f"    - {t.title}")

# ── 3. Recurring task auto-creation ───────────────────────────────────────────

print()
print("=" * WIDTH)
print("  3. RECURRING TASK AUTO-CREATION")
print("=" * WIDTH)

print("\n  Marking Mochi's 'Morning walk' complete...")
next_task = mochi.mark_task_complete("Morning walk")
if next_task:
    print(f"  → Next occurrence auto-created: '{next_task.title}' due {next_task.due_date}")

print("\n  Marking Luna's 'Grooming brush' (weekly) complete...")
next_task = luna.mark_task_complete("Grooming brush")
if next_task:
    print(f"  → Next occurrence auto-created: '{next_task.title}' due {next_task.due_date}")

print("\n  Marking Luna's 'Puzzle feeder' (as-needed) complete...")
next_task = luna.mark_task_complete("Puzzle feeder")
print(f"  → Next occurrence: {next_task!r}  (None expected — no recurrence for as-needed)")

# ── 4. Conflict detection ──────────────────────────────────────────────────────

print()
print("=" * WIDTH)
print("  4. CONFLICT DETECTION")
print("=" * WIDTH)

# Scan all tasks (including completed) so we catch the deliberate 09:00 conflict
# between Luna's 'Medication' and 'Puzzle feeder' set up at the top.
all_pet_tasks = [t for pet in owner.pets for t in pet.tasks]
conflicts = scheduler.detect_conflicts(all_pet_tasks)

if conflicts:
    print()
    for warning in conflicts:
        print(f"  ⚠  {warning}")
else:
    print("\n  No scheduling conflicts found.")

# ── 5. Generate final plan ─────────────────────────────────────────────────────

print()
print("=" * WIDTH)
print("  5. FULL DAILY PLAN")
print("=" * WIDTH)

plan = scheduler.generate_plan()
print()
print(plan.explain())
print("=" * WIDTH)
