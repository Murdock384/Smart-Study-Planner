
import streamlit as st
from datetime import datetime, timedelta, time
from models import Task, TimeSlot, ScheduledPart, UnfinishedTask
from utils import minutes_between, add_minutes, format_dt, format_minutes, overlaps
from algo_priority import get_planning_start, calculate_priority_scores, calculate_available_minutes_before_deadline
from algo_greedy import greedy_split_scheduling, clean_and_merge_time_slots
from algo_suggest import suggest_extra_slots



# ============================================================
# Streamlit state helpers
# ============================================================


def initialize_state():
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    if "slots" not in st.session_state:
        st.session_state.slots = []
    if "next_task_id" not in st.session_state:
        st.session_state.next_task_id = 1


def add_sample_data():
    today = datetime.now().date()
    day_1 = today + timedelta(days=1)
    day_2 = today + timedelta(days=2)
    day_3 = today + timedelta(days=3)

    st.session_state.tasks = [
        Task(
            id=1,
            name="Algorithms Assignment",
            duration_minutes=180,
            deadline=datetime.combine(day_2, time(23, 0)),
            difficulty=5,
        ),
        Task(
            id=2,
            name="Statistics Quiz Prep",
            duration_minutes=120,
            deadline=datetime.combine(day_2, time(21, 0)),
            difficulty=4,
        ),
        Task(
            id=3,
            name="Marketing Slides",
            duration_minutes=60,
            deadline=datetime.combine(day_3, time(23, 0)),
            difficulty=2,
        ),
    ]

    st.session_state.slots = [
        TimeSlot(
            start=datetime.combine(day_1, time(18, 0)),
            end=datetime.combine(day_1, time(20, 0)),
        ),
        TimeSlot(
            start=datetime.combine(day_2, time(18, 0)),
            end=datetime.combine(day_2, time(20, 0)),
        ),
    ]

    st.session_state.next_task_id = 4


# ============================================================
# Streamlit UI
# ============================================================


st.set_page_config(page_title="Smart Study Planner", page_icon="📚", layout="wide")
initialize_state()

st.title("📚 Smart Study Planner")
st.write(
    "This app uses three chained algorithms: feasibility-aware deadline-weighted priority scoring, "
    "greedy split scheduling with a max heap, and suggested slot generation."
)

with st.sidebar:
    st.header("Controls")

    if st.button("Load sample data"):
        add_sample_data()
        st.success("Sample data loaded.")

    if st.button("Clear all data"):
        st.session_state.tasks = []
        st.session_state.slots = []
        st.session_state.next_task_id = 1
        st.success("All data cleared.")

    st.divider()
    st.caption("Run with: streamlit run smart_study_planner.py")

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Add a study task")

    with st.form("task_form", clear_on_submit=True):
        task_name = st.text_input("Task name", placeholder="Example: Algorithms Assignment")
        duration_hours = st.number_input("Duration in hours", min_value=0.25, max_value=20.0, step=0.25, value=1.0)
        deadline_date = st.date_input("Deadline date")
        deadline_time = st.time_input("Deadline time", value=time(23, 0), step=900)
        difficulty = st.slider("Difficulty", min_value=1, max_value=5, value=3)

        submitted_task = st.form_submit_button("Add task")

        if submitted_task:
            if not task_name.strip():
                st.error("Task name cannot be empty.")
            else:
                deadline = datetime.combine(deadline_date, deadline_time)
                task = Task(
                    id=st.session_state.next_task_id,
                    name=task_name.strip(),
                    duration_minutes=int(duration_hours * 60),
                    deadline=deadline,
                    difficulty=difficulty,
                )
                st.session_state.tasks.append(task)
                st.session_state.next_task_id += 1
                st.success("Task added.")

with right_col:
    st.subheader("Add an available study slot")

    with st.form("slot_form", clear_on_submit=True):
        slot_date = st.date_input("Slot date")
        start_time = st.time_input("Start time", value=time(18, 0), step=900)
        end_time = st.time_input("End time", value=time(20, 0), step=900)

        submitted_slot = st.form_submit_button("Add available slot")

        if submitted_slot:
            start = datetime.combine(slot_date, start_time)
            end = datetime.combine(slot_date, end_time)

            if end <= start:
                st.error("End time must be after start time.")
            else:
                st.session_state.slots.append(TimeSlot(start, end))
                st.success("Available slot added.")

st.divider()

current_tasks_col, current_slots_col = st.columns(2)

with current_tasks_col:
    st.subheader("Current tasks")
    if st.session_state.tasks:
        task_rows = []
        for task in st.session_state.tasks:
            task_rows.append(
                {
                    "ID": task.id,
                    "Task": task.name,
                    "Duration": format_minutes(task.duration_minutes),
                    "Deadline": format_dt(task.deadline),
                    "Difficulty": task.difficulty,
                }
            )
        st.table(task_rows)
    else:
        st.info("No tasks added yet.")

with current_slots_col:
    st.subheader("Current available slots")
    if st.session_state.slots:
        slot_rows = []
        for index, slot in enumerate(st.session_state.slots, start=1):
            slot_rows.append(
                {
                    "Slot": index,
                    "Start": format_dt(slot.start),
                    "End": format_dt(slot.end),
                    "Length": format_minutes(minutes_between(slot.start, slot.end)),
                }
            )
        st.table(slot_rows)
    else:
        st.info("No available slots added yet.")

st.divider()

if st.button("Generate study plan", type="primary"):
    if not st.session_state.tasks:
        st.error("Please add at least one task first.")
    else:
        now = datetime.now()

        planning_start = get_planning_start(st.session_state.slots)
        scored_tasks = calculate_priority_scores(
            st.session_state.tasks,
            st.session_state.slots,
            planning_start,
        )
        schedule, unfinished, remaining_free_slots = greedy_split_scheduling(
            scored_tasks,
            st.session_state.slots,
        )
        suggestions, still_unfinished = suggest_extra_slots(unfinished, schedule)

        final_parts = schedule + suggestions
        final_parts.sort(key=lambda part: part.start)

        st.header("Generated Study Plan")

        tab1, tab2, tab3, tab4 = st.tabs(
            [
                "Algorithm 1: Priority Scores",
                "Algorithm 2: Scheduled Parts",
                "Algorithm 3: Extra Suggestions",
                "Final Output",
            ]
        )

        with tab1:
            st.subheader("Feasibility-Aware Deadline-Weighted Priority Scoring")
            st.write(
                "Each task is scored using deadline closeness and difficulty. "
                "The algorithm also checks whether enough provided availability exists before the deadline. "
                "If a task is not feasible with the current slots, its score is reduced so it does not block a task that can still be completed."
            )

            score_rows = []
            for task in sorted(scored_tasks, key=lambda t: (-t.priority, t.deadline)):
                available_before_deadline = calculate_available_minutes_before_deadline(
                    task,
                    st.session_state.slots,
                )
                score_rows.append(
                    {
                        "Task": task.name,
                        "Priority Score": task.priority,
                        "Duration": format_minutes(task.duration_minutes),
                        "Available before deadline": format_minutes(available_before_deadline),
                        "Deadline": format_dt(task.deadline),
                        "Difficulty": task.difficulty,
                    }
                )
            st.table(score_rows)

        with tab2:
            st.subheader("Greedy Split Scheduling using Max Heap")
            st.write(
                "The task with the highest feasibility-aware priority score is handled first. "
                "This means the scheduler prefers tasks that are urgent, difficult, and actually completable with the given availability. "
                "If a task is longer than one slot, it is split across multiple available slots."
            )

            if schedule:
                schedule_rows = []
                for part in schedule:
                    schedule_rows.append(
                        {
                            "Start": format_dt(part.start),
                            "End": format_dt(part.end),
                            "Task": part.task_name,
                            "Time assigned": format_minutes(part.minutes),
                        }
                    )
                st.table(schedule_rows)
            else:
                st.warning("No tasks could be scheduled using the provided availability.")

            if unfinished:
                st.warning("Some task time could not fit into the provided availability.")
                unfinished_rows = []
                for item in unfinished:
                    unfinished_rows.append(
                        {
                            "Task": item.task.name,
                            "Remaining time": format_minutes(item.remaining_minutes),
                            "Reason": item.reason,
                        }
                    )
                st.table(unfinished_rows)
            else:
                st.success("All task time fit into the provided availability.")

        with tab3:
            st.subheader("Suggested Slot Generation")
            st.write(
                "This stage only runs for unfinished task time. It suggests extra reasonable "
                "study slots before the task deadline."
            )

            if suggestions:
                suggestion_rows = []
                for part in suggestions:
                    suggestion_rows.append(
                        {
                            "Suggested start": format_dt(part.start),
                            "Suggested end": format_dt(part.end),
                            "Task": part.task_name,
                            "Time assigned": format_minutes(part.minutes),
                        }
                    )
                st.table(suggestion_rows)
            else:
                st.info("No extra suggestions were needed or possible.")

            if still_unfinished:
                st.error("Some tasks still could not be fully planned.")
                still_rows = []
                for item in still_unfinished:
                    still_rows.append(
                        {
                            "Task": item.task.name,
                            "Remaining time": format_minutes(item.remaining_minutes),
                            "Reason": item.reason,
                        }
                    )
                st.table(still_rows)

        with tab4:
            st.subheader("Final Study Plan")

            if final_parts:
                final_rows = []
                for part in final_parts:
                    final_rows.append(
                        {
                            "Type": "Suggested extra slot" if part.source == "suggested" else "Scheduled from availability",
                            "Start": format_dt(part.start),
                            "End": format_dt(part.end),
                            "Task": part.task_name,
                            "Duration": format_minutes(part.minutes),
                        }
                    )
                st.table(final_rows)
            else:
                st.warning("No final schedule was created.")

            st.subheader("Unused original availability")
            if remaining_free_slots:
                remaining_rows = []
                for slot in remaining_free_slots:
                    remaining_rows.append(
                        {
                            "Start": format_dt(slot.start),
                            "End": format_dt(slot.end),
                            "Length": format_minutes(minutes_between(slot.start, slot.end)),
                        }
                    )
                st.table(remaining_rows)
            else:
                st.write("No unused original availability remains.")

st.divider()

with st.expander("Big O summary for presentation"):
    st.markdown(
        """
        **Algorithm 1: Feasibility-Aware Deadline-Weighted Priority Scoring**  
        Time: `O(T*S)` because every task checks the available slots before its deadline.  
        Space: `O(T)` for the scored task list.  
        The score uses deadline closeness and difficulty, but applies a penalty when the task cannot fit before its deadline using the provided availability.

        **Algorithm 2: Greedy Split Scheduling with Max Heap**  
        Time: `O(T log T + T*S)` where `T` is tasks and `S` is available slots.  
        The `T log T` part comes from heap insertion/removal. The `T*S` part comes from checking available slots.  
        Space: `O(T + S)` for the heap, schedule, unfinished tasks, and free slots.  
        The heap orders tasks by the feasibility-aware priority score.

        **Algorithm 3: Suggested Slot Generation**  
        Time: `O(U*D*P)` where `U` is unfinished tasks, `D` is days searched, and `P` is scheduled parts checked for overlaps.  
        Space: `O(U + P)` for suggestions and occupied intervals.

        **Primary bottleneck:** Algorithm 2, because scheduling may need to check many tasks against many time slots.  
        If many unfinished tasks exist, Algorithm 3 can also become expensive because it searches day-by-day before each deadline.
        """
    )
