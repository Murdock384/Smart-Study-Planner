from dataclasses import dataclass, replace
from datetime import datetime

@dataclass
class Task:
    id: int
    name: str
    duration_minutes: int
    deadline: datetime
    difficulty: int
    priority: float = 0.0

@dataclass
class TimeSlot:
    start: datetime
    end: datetime

@dataclass
class ScheduledPart:
    task_id: int
    task_name: str
    start: datetime
    end: datetime
    minutes: int
    source: str  # "available" or "suggested"

@dataclass
class UnfinishedTask:
    task: Task
    remaining_minutes: int
    reason: str
