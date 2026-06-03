from models import TimeSlot, ScheduledPart, UnfinishedTask
from utils import minutes_between, add_minutes
from datetime import timedelta
from bisect import bisect_left, insort


SUGGESTION_BUFFER_MINUTES = 15


def _insert_into_sorted_occupied(occupied, slot):
    """
    Inserts a TimeSlot into the occupied list while maintaining sort order by
    start time.

    insort finds the insertion point with binary search, but the list still has
    to shift later elements to make room. That makes insertion O(P), not O(log P).
    """
    insort(occupied, slot, key=lambda s: s.start)


def suggest_extra_slots(unfinished_tasks, scheduled_parts):
    """
    Algorithm 3: Suggested Slot Generation.

    Places each unfinished task in the latest non-conflicting slot before its
    deadline, leaving a 15-minute buffer. Searches backwards from the ideal
    position if conflicts exist. The search is bounded to 7 days before the
    deadline to prevent infinite iteration.

    Assumes scheduled_parts is already sorted by start time. This is the
    contract with Algorithm 2, which sorts its schedule before returning it.

    Time complexity: O(U * P)
    U = number of unfinished tasks
    P = number of scheduled parts in occupied
    occupied is kept in sorted order via insort, so per task:
    - Binary search finds window boundaries in O(log P)
    - Only slots inside the window are clipped and iterated — O(k), k <= P
    - Backwards gap walk is O(k)
    - insort to add confirmed suggestion is O(P) (list shift)

    Space complexity: O(P + U)
    P for the occupied list, U for suggestions and still_unfinished.
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
        search_start_limit = task.deadline - timedelta(days=7)


        # Use binary search to find only the slots inside the interval of [search_start_limit, latest_allowed_end].
        slot_suggestion_window_start_idx = bisect_left(occupied, search_start_limit, key=lambda s: s.start)
        slot_suggestion_window_end_idx   = bisect_left(occupied, latest_allowed_end,  key=lambda s: s.start)

        # Step back one index so a slot that starts before search_start_limit but
        # ends inside the window is not silently dropped. The clipping below trims
        # whatever falls outside the window, so over-including by one is safe.
        effective_start_idx = max(0, slot_suggestion_window_start_idx - 1)

        # Walk backwards through the gaps between occupied slots.
        # The first gap (from the right) that fits remaining minutes is the placement.
        gap_end = latest_allowed_end
        candidate_found = False

        for slot in reversed(occupied[effective_start_idx:slot_suggestion_window_end_idx]):
            slot_start = max(slot.start, search_start_limit)
            slot_end = min(slot.end, latest_allowed_end)

            if slot_start >= slot_end:
                continue

            gap_minutes = minutes_between(slot_end, gap_end)
            # If we find a gap that can fit between the user provided slots that is large enough 
            # to fit the remaining minutes, we create a suggestion and break out of the loop as the 
            # unfinished task is now fully scheduled.
            if gap_minutes >= remaining:
                candidate_end = gap_end
                candidate_start = add_minutes(candidate_end, -remaining)
                suggestions.append(ScheduledPart(
                    task_id=task.id,
                    task_name=task.name,
                    start=candidate_start,
                    end=candidate_end,
                    minutes=remaining,
                    source="suggested",
                ))
                _insert_into_sorted_occupied(occupied, TimeSlot(candidate_start, candidate_end))
                remaining = 0
                candidate_found = True
                break
            gap_end = slot_start

        # Check the leftmost gap: [search_start_limit, gap_end]
        if not candidate_found and remaining > 0:
            if minutes_between(search_start_limit, gap_end) >= remaining:
                candidate_end = gap_end
                candidate_start = add_minutes(candidate_end, -remaining)
                suggestions.append(ScheduledPart(
                    task_id=task.id,
                    task_name=task.name,
                    start=candidate_start,
                    end=candidate_end,
                    minutes=remaining,
                    source="suggested",
                ))
                _insert_into_sorted_occupied(occupied, TimeSlot(candidate_start, candidate_end))
                remaining = 0
                candidate_found = True

        # Handling edge case that no time slot was empty to create a new suggestion 1 week before the deadline.
        if not candidate_found and remaining > 0:
            still_unfinished.append(
                UnfinishedTask(
                    task=task,
                    remaining_minutes=remaining,
                    reason="no non-overlapping suggested slot was found a week before the deadline",
                )
            )

    suggestions.sort(key=lambda part: part.start)

    return suggestions, still_unfinished
