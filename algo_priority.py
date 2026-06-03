from models import Task
from utils import minutes_between
from dataclasses import replace
from datetime import datetime

def get_planning_start(available_slots):
    """
    Uses the earliest user-provided available slot as the planning reference.
    In the case there are no available slots, it defaults to the current time to not break the 
    priority scoring algorithm.
    """
    if available_slots:
        return min(slot.start for slot in available_slots)
    return datetime.now()


def calculate_available_minutes_before_deadline(task, available_slots):
    """
    Calculates how many minutes of the user's provided availability exist
    before a task's deadline.

    Expects pre-merged slots.
    """
    total = 0

    for slot in available_slots:
        if slot.start >= task.deadline:
            continue

        usable_start = slot.start
        usable_end = min(slot.end, task.deadline)

        if usable_end > usable_start:
            total += minutes_between(usable_start, usable_end)

    return total


def calculate_priority_scores(tasks, available_slots=None, planning_start=None):
    """
    Algorithm 1: Feasibility-Aware Deadline-Weighted Priority Scoring.

    The score uses:
    1. deadline closeness,
    2. difficulty,
    3. feasibility estimate: time remaining before the deadline vs time needed.

    Note: available_slots is used only to derive planning_start (the earliest
    available slot). The feasibility ratio itself is pure time arithmetic —
    hours_until_deadline / hours_needed — and does not scan the slot list.

    If a task cannot be completed before its deadline, its score is reduced.
    This prevents an impossible task from blocking one that can still be completed.

    Time complexity: O(T + S)
    T = number of tasks in the scoring loop.
    S = number of available slots — get_planning_start scans them once with
    min() to find the earliest start time.

    Space complexity: O(T)
    """
    if available_slots is None:
        available_slots = []

    if planning_start is None:
        planning_start = get_planning_start(available_slots)

    scored_tasks = []

    for task in tasks:
        hours_until_deadline = (task.deadline - planning_start).total_seconds() / 3600

        if hours_until_deadline <= 0:
            # If the deadline is before the first available slot, the task is
            # not feasible with the provided availability.
            # We keep the deadline score low instead of making it extremely negative,
            # because Algorithm 3 may still suggest an extra slot before the deadline.
            deadline_score = 0
        else:
            # Deadline is weighted heavily.
            # The closer the deadline, the higher the score.
            deadline_score = min(100, 80 / max(hours_until_deadline, 0.25))

        difficulty_score = task.difficulty * 5

        hours_needed = task.duration_minutes / 60
        feasibility_ratio = (
            max(0, hours_until_deadline) / hours_needed
            if hours_needed > 0
            else 0
        )

        if feasibility_ratio >= 1:
            feasibility_penalty = 0
        else:
            # The less feasible a task is, the more its score is reduced.
            # Example: if only 25% of the task can fit before the deadline,
            # the penalty is 75.
            feasibility_penalty = (1 - feasibility_ratio) * 100

        # Clamp the score at 0 so the UI does not show confusing negative values.
        priority = max(0, deadline_score + difficulty_score - feasibility_penalty)

        scored_tasks.append(replace(task, priority=round(priority, 2)))

    return scored_tasks