from models import TimeSlot, ScheduledPart, UnfinishedTask
from utils import minutes_between, add_minutes, overlaps
from datetime import timedelta


SUGGESTION_BUFFER_MINUTES = 15


def subtract_occupied_intervals(window_start, window_end, occupied_intervals):
    """
    Finds free intervals inside a possible study window.

    Example:
    Window: 21:45-22:45
    Occupied: 22:00-22:15
    Free result: 21:45-22:00 and 22:15-22:45
    """
    free_segments = []
    cursor = window_start

    relevant_occupied = []

    for occupied in occupied_intervals:
        if overlaps(window_start, window_end, occupied.start, occupied.end):
            relevant_occupied.append(occupied)

    relevant_occupied.sort(key=lambda slot: slot.start)

    for occupied in relevant_occupied:
        if occupied.start > cursor:
            free_segments.append(
                TimeSlot(
                    cursor,
                    min(occupied.start, window_end),
                )
            )

        cursor = max(cursor, occupied.end)

        if cursor >= window_end:
            break

    if cursor < window_end:
        free_segments.append(TimeSlot(cursor, window_end))

    return free_segments


def suggest_extra_slots(unfinished_tasks, scheduled_parts):
    """
    Algorithm 3: Suggested Slot Generation.

    This algorithm runs only for unfinished task time.

    New logic:
    The suggested slot is created as close as possible to the deadline while
    leaving a 15-minute buffer.

    Example:
    Task duration: 1 hour
    Deadline: 23:00
    Buffer: 15 minutes

    Suggested slot:
    21:45-22:45

    If the exact slot conflicts with an already scheduled task, the algorithm
    searches backwards until it finds a non-overlapping slot.
    """
    occupied = [TimeSlot(part.start, part.end) for part in scheduled_parts]

    suggestions = []
    still_unfinished = []

    for item in unfinished_tasks:
        task = item.task
        remaining = item.remaining_minutes

        if remaining <= 0:
            continue

        latest_allowed_end = task.deadline - timedelta(minutes=SUGGESTION_BUFFER_MINUTES)

        # First try the ideal slot directly before the deadline buffer.
        ideal_start = add_minutes(latest_allowed_end, -remaining)
        ideal_end = latest_allowed_end

        if ideal_end <= ideal_start:
            still_unfinished.append(
                UnfinishedTask(
                    task=task,
                    remaining_minutes=remaining,
                    reason="deadline is too soon to create a suggested slot",
                )
            )
            continue

        # We search backwards from the ideal slot.
        # The search window starts 7 days before the deadline to avoid infinite search.
        search_start_limit = task.deadline - timedelta(days=7)
        search_end = ideal_end

        candidate_found = False

        while search_end > search_start_limit and remaining > 0:
            candidate_start = add_minutes(search_end, -remaining)
            candidate_end = search_end

            if candidate_start < search_start_limit:
                break

            conflicts = [
                occupied_slot
                for occupied_slot in occupied
                if overlaps(
                    candidate_start,
                    candidate_end,
                    occupied_slot.start,
                    occupied_slot.end,
                )
            ]

            if not conflicts:
                suggested_part = ScheduledPart(
                    task_id=task.id,
                    task_name=task.name,
                    start=candidate_start,
                    end=candidate_end,
                    minutes=remaining,
                    source="suggested",
                )

                suggestions.append(suggested_part)
                occupied.append(TimeSlot(candidate_start, candidate_end))
                remaining = 0
                candidate_found = True
                break

            # Move the candidate slot to end before the nearest conflicting slot.
            earliest_conflict_start = min(slot.start for slot in conflicts)
            search_end = earliest_conflict_start

        if not candidate_found and remaining > 0:
            still_unfinished.append(
                UnfinishedTask(
                    task=task,
                    remaining_minutes=remaining,
                    reason="no non-overlapping suggested slot was found before the deadline",
                )
            )

    suggestions.sort(key=lambda part: part.start)

    return suggestions, still_unfinished