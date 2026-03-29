from pawpal_system import Owner, Pet, Task, Scheduler

# ── Setup ──────────────────────────────────────────────────────────────────────

owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks
mochi.add_task(Task("Morning walk",    30, "high",   "walk",      "daily"))
mochi.add_task(Task("Breakfast",       10, "high",   "feeding",   "daily"))
mochi.add_task(Task("Evening run",     45, "medium", "walk",      "daily"))

# Luna's tasks
luna.add_task(Task("Medication",        5, "high",   "meds",      "daily"))
luna.add_task(Task("Grooming brush",   15, "medium", "grooming",  "weekly"))
luna.add_task(Task("Puzzle feeder",    20, "low",    "enrichment","as-needed"))

owner.add_pet(mochi)
owner.add_pet(luna)

# ── Generate plan ──────────────────────────────────────────────────────────────

plan = Scheduler(owner).generate_plan()

# ── Print schedule ─────────────────────────────────────────────────────────────

WIDTH = 56
PRIORITY_ICON = {"high": "(!)", "medium": "(~)", "low": "( )"}

print("=" * WIDTH)
print(f"  TODAY'S SCHEDULE  —  {owner.name}")
print(f"  Budget: {owner.available_minutes} min  |  Used: {plan.total_duration} min")
print("=" * WIDTH)

if plan.scheduled_tasks:
    for task in plan.scheduled_tasks:
        icon = PRIORITY_ICON.get(task.priority, "   ")
        print(f"  {icon}  {task.title:<28} {task.duration_minutes:>3} min")
else:
    print("  No tasks could be scheduled.")

print("-" * WIDTH)
print(f"  Total time used: {plan.total_duration} / {owner.available_minutes} min")

if plan.skipped_tasks:
    print()
    print("  Skipped (didn't fit):")
    for task in plan.skipped_tasks:
        reason = plan.skip_reasons.get(task.title, "")
        print(f"    x  {task.title:<28}  [{reason}]")

print("=" * WIDTH)
