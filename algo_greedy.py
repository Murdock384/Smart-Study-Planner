from models import Task, TimeSlot, ScheduledPart, UnfinishedTask
from utils import minutes_between, add_minutes

class MaxHeap:
    def __init__(self):
        self.data = []

    def is_empty(self):
        return len(self.data) == 0

    def push(self, task):
        self.data.append(task)
        self._sift_up(len(self.data) - 1)

    def pop(self):
        if self.is_empty():
            return None
        self._swap(0, len(self.data) - 1)
        best_task = self.data.pop()
        self._sift_down(0)
        return best_task

    def _is_higher_priority(self, a, b):
        """
        Compares two tasks based on priority, deadline, difficulty, and duration and
        returns True if a has higher priority than b.
        """
        if a.priority != b.priority:
            return a.priority > b.priority
        if a.deadline != b.deadline:
            return a.deadline < b.deadline
        if a.difficulty != b.difficulty:
            return a.difficulty > b.difficulty
        if a.duration_minutes != b.duration_minutes:
            return a.duration_minutes < b.duration_minutes
        return a.id < b.id

    def _sift_up(self, index):
        while index > 0:
            parent = (index - 1) // 2
            if self._is_higher_priority(self.data[index], self.data[parent]):
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index):
        size = len(self.data)
        while True:
            left = (2 * index) + 1
            right = (2 * index) + 2
            best = index
            if left < size and self._is_higher_priority(self.data[left], self.data[best]):
                best = left
            if right < size and self._is_higher_priority(self.data[right], self.data[best]):
                best = right
            if best != index:
                self._swap(index, best)
                index = best
            else:
                break
            
    def _swap(self, i, j):
        self.data[i], self.data[j] = self.data[j], self.data[i]

def clean_and_merge_time_slots(slots):
    """
    Creates a copy of the provided slots, sorts them by start time,
    and merges any overlapping or adjacent intervals into a single slot.

    Time complexity: O(S log S) — dominated by the sort.
    Space complexity: O(S) — a fresh list is allocated and returned.
    """
    cleaned = []
    for slot in slots:
        cleaned.append(TimeSlot(slot.start, slot.end))
    cleaned.sort(key=lambda slot: slot.start)
    merged = []
    for slot in cleaned:
        if not merged:
            merged.append(slot)
            continue
        last = merged[-1]
        if slot.start <= last.end:
            last.end = max(last.end, slot.end)
        else:
            merged.append(slot)
    return merged

def greedy_split_scheduling(scored_tasks, available_slots):
    """
    Algorithm 2: Greedy Split Scheduling with Max Heap.

    Pops tasks from a max heap in priority order and assigns them into
    available time slots, splitting a task across multiple slots if needed.
    Tasks that cannot be fully scheduled before their deadline are returned
    as unfinished for Algorithm 3 to handle.

    Time complexity: O(S log S + T log T + T*S)
    S log S — clean_and_merge_time_slots sorts the available slots once.
    T log T — each of the T heap push/pop operations sifts through log T levels.
    T*S   — the scheduling loop: slot_index resets to 0 for every task,
            so each task rescans up to S slots.

    Space complexity: O(T + S)
    T for the heap, S for the free_slots list.
    """
    free_slots = clean_and_merge_time_slots(available_slots)
    heap = MaxHeap()
    for task in scored_tasks:
        heap.push(task)
    schedule = []
    unfinished = []
    while not heap.is_empty():
        task = heap.pop()
        remaining = task.duration_minutes
        slot_index = 0
        while remaining > 0 and slot_index < len(free_slots):
            slot = free_slots[slot_index]
            if slot.start >= task.deadline:
                break
            usable_start = slot.start
            usable_end = min(slot.end, task.deadline)
            usable_minutes = minutes_between(usable_start, usable_end)
            if usable_minutes <= 0:
                slot_index += 1
                continue
            minutes_to_use = min(remaining, usable_minutes)
            part_start = usable_start
            part_end = add_minutes(part_start, minutes_to_use)
            schedule.append(
                ScheduledPart(
                    task_id=task.id,
                    task_name=task.name,
                    start=part_start,
                    end=part_end,
                    minutes=minutes_to_use,
                    source="available",
                )
            )
            remaining -= minutes_to_use
            if part_end < slot.end:
                free_slots[slot_index] = TimeSlot(part_end, slot.end)
            else:
                free_slots.pop(slot_index)
        if remaining > 0:
            unfinished.append(
                UnfinishedTask(
                    task=task,
                    remaining_minutes=remaining,
                    reason="not enough provided availability before the deadline",
                )
            )
    schedule.sort(key=lambda part: part.start)
    return schedule, unfinished, free_slots
