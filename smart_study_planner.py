import html
import streamlit as st
from datetime import datetime, time
from textwrap import dedent

from models import Task, TimeSlot
from utils import minutes_between, format_dt, format_minutes
from algo_priority import (
    get_planning_start,
    calculate_priority_scores,
    calculate_available_minutes_before_deadline,
)
from algo_greedy import greedy_split_scheduling
from algo_suggest import suggest_extra_slots


# ============================================================
# Page setup
# ============================================================

st.set_page_config(
    page_title="Smart Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Styling
# ============================================================

def inject_css():
    st.markdown(
        dedent(
            """
            <style>
                :root {
                    --bg: #0B1120;
                    --panel: rgba(17, 24, 39, 0.82);
                    --panel-soft: rgba(15, 23, 42, 0.78);
                    --border: rgba(148, 163, 184, 0.20);
                    --border-strong: rgba(148, 163, 184, 0.32);
                    --text: #F8FAFC;
                    --muted: #94A3B8;
                    --muted-light: #CBD5E1;
                    --accent: #38BDF8;
                    --success: #22C55E;
                    --warning: #FBBF24;
                    --danger: #F87171;
                }

                .stApp {
                    background:
                        radial-gradient(circle at 10% 0%, rgba(56, 189, 248, 0.10), transparent 28%),
                        linear-gradient(180deg, #0B1120 0%, #0F172A 100%);
                    color: var(--text);
                }

                .block-container {
                    max-width: 980px;
                    padding-top: 2rem;
                    padding-bottom: 3rem;
                }

                header[data-testid="stHeader"] {
                    background: transparent;
                }

                #MainMenu, footer {
                    visibility: hidden;
                }

                html, body, [class*="css"] {
                    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                }

                .hero {
                    margin-bottom: 1.8rem;
                }

                .eyebrow {
                    color: var(--accent);
                    font-size: 0.78rem;
                    font-weight: 800;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    margin-bottom: 0.45rem;
                }

                .title {
                    color: var(--text);
                    font-size: clamp(2.3rem, 5vw, 3.8rem);
                    line-height: 0.96;
                    font-weight: 850;
                    letter-spacing: -0.06em;
                    margin-bottom: 0.8rem;
                }

                .subtitle {
                    color: var(--muted-light);
                    max-width: 740px;
                    font-size: 1rem;
                    line-height: 1.65;
                    margin-bottom: 1.1rem;
                }

                .step-title {
                    color: var(--text);
                    font-size: 1.25rem;
                    font-weight: 850;
                    letter-spacing: -0.03em;
                    margin-bottom: 0.25rem;
                }

                .step-copy {
                    color: var(--muted);
                    font-size: 0.92rem;
                    line-height: 1.55;
                    margin-bottom: 1rem;
                }

                div[data-testid="stVerticalBlockBorderWrapper"] {
                    border-color: var(--border) !important;
                    background: rgba(17, 24, 39, 0.62) !important;
                    border-radius: 20px !important;
                    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.14);
                }

                .list-card {
                    border: 1px solid var(--border);
                    border-radius: 18px;
                    padding: 1rem 1.05rem;
                    margin-bottom: 0.75rem;
                    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.12);
                }

                .stButton > button[kind="tertiary"] {
                    width: 28px !important;
                    height: 28px !important;
                    min-width: 28px !important;
                    min-height: 28px !important;
                    padding: 0 !important;

                    display: inline-flex !important;
                    align-items: center !important;
                    justify-content: center !important;

                    border-radius: 7px !important;
                    border: 1px solid rgba(248, 113, 113, 0.75) !important;
                    background: rgba(15, 23, 42, 0.75) !important;
                    color: #FCA5A5 !important;

                    font-size: 0.95rem !important;
                    font-weight: 700 !important;
                    line-height: 1 !important;
                    box-shadow: none !important;
                    transform: none !important;
                }

                .stButton > button[kind="tertiary"] p {
                    margin: 0 !important;
                    padding: 0 !important;
                    line-height: 1 !important;
                }

                .stButton > button[kind="tertiary"]:hover {
                    background: rgba(239, 68, 68, 0.16) !important;
                    border-color: rgba(248, 113, 113, 1) !important;
                    color: #FECACA !important;
                    transform: none !important;
                }

                .task-card {
                    background:
                        linear-gradient(135deg, rgba(124, 58, 237, 0.16), rgba(15, 23, 42, 0.82));
                    border-left: 4px solid #8B5CF6;
                }

                .slot-card {
                    background:
                        linear-gradient(135deg, rgba(20, 184, 166, 0.16), rgba(15, 23, 42, 0.82));
                    border-left: 4px solid #14B8A6;
                }

                .list-kicker {
                    font-size: 0.72rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    font-weight: 800;
                    margin-bottom: 0.35rem;
                }

                .task-card .list-kicker {
                    color: #C4B5FD;
                }

                .slot-card .list-kicker {
                    color: #99F6E4;
                }

                .list-title {
                    color: var(--text);
                    font-weight: 850;
                    font-size: 1.2rem;
                    margin-bottom: 0.55rem;
                }

                .task-header-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 2rem;
                }

                .task-main-info {
                    min-width: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    gap: 0.4rem;
                }

                .task-meta-inline {
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                    gap: 1.6rem;
                    margin-left: auto;
                    text-align: left;
                }

                .task-meta-item {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    gap: 0.4rem;
                    min-height: 42px;
                }

                .task-meta-label,
                .list-kicker {
                    font-size: 0.72rem;
                    line-height: 1;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    color: var(--muted);
                    font-weight: 780;
                }

                .task-card .list-kicker {
                    color: #C4B5FD;
                }

                .task-meta-value,
                .list-title {
                    font-size: 1rem;
                    line-height: 1.2;
                    font-weight: 820;
                    color: var(--text);
                    margin: 0;
                }

                .task-card .list-kicker {
                    color: #C4B5FD;
                }

                .task-meta-value,
                .list-title {
                    font-size: 1rem;
                    line-height: 1.25;
                    font-weight: 820;
                    color: var(--text);
                    margin: 0;
                }

                @media (max-width: 760px) {
                    .task-header-row {
                        grid-template-columns: 1fr;
                        gap: 0.85rem;
                    }

                    .task-meta-inline {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 1rem;
                    }
                }

                .slot-header-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 2rem;
                }

                .slot-main-info {
                    min-width: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    gap: 0.4rem;
                }

                .slot-meta-inline {
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                    gap: 1.6rem;
                    margin-left: auto;
                    text-align: left;
                }

                .slot-meta-item {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    gap: 0.4rem;
                    min-height: 42px;
                }

                .slot-meta-label,
                .slot-card .list-kicker {
                    font-size: 0.72rem;
                    line-height: 1;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    color: var(--muted);
                    font-weight: 780;
                }

                .slot-card .list-kicker {
                    color: #99F6E4;
                }

                .slot-meta-value,
                .slot-card .list-title {
                    font-size: 1rem;
                    line-height: 1.2;
                    font-weight: 820;
                    color: var(--text);
                    margin: 0;
                }

                @media (max-width: 760px) {
                    .slot-header-row {
                        grid-template-columns: 1fr;
                        gap: 0.85rem;
                    }

                    .slot-meta-inline {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 1rem;
                    }
                }

                .primary-meta-row {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 1.25rem;
                    margin-bottom: 0.6rem;
                }

                .primary-meta-item {
                    display: flex;
                    flex-direction: column;
                    gap: 0.15rem;
                }

                .primary-meta-label {
                    font-size: 0.72rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    color: var(--muted);
                    font-weight: 780;
                }

                .primary-meta-value {
                    font-size: 1rem;
                    font-weight: 820;
                    color: var(--text);
                }

                .chip-row {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.4rem;
                }

                .chip {
                    color: var(--muted-light);
                    background: rgba(30, 41, 59, 0.82);
                    border: 1px solid rgba(148, 163, 184, 0.14);
                    padding: 0.32rem 0.56rem;
                    border-radius: 999px;
                    font-size: 0.76rem;
                    font-weight: 650;
                }

                .plan-card {
                    border: 1px solid var(--border);
                    background: rgba(15, 23, 42, 0.82);
                    border-radius: 18px;
                    padding: 1rem 1.05rem;
                    margin-bottom: 0.8rem;
                }

                .plan-card.scheduled {
                    border-left: 4px solid var(--accent);
                }

                .plan-card.suggested {
                    border-left: 4px solid var(--warning);
                }

                .plan-layout {
                    display: grid;
                    grid-template-columns: 180px 1fr;
                    gap: 1rem;
                    align-items: center;
                }

                .plan-time-block {
                    padding-right: 0.9rem;
                    border-right: 1px solid rgba(148, 163, 184, 0.16);
                }

                .plan-time {
                    color: var(--text);
                    font-size: 1.35rem;
                    font-weight: 850;
                    line-height: 1.1;
                    letter-spacing: -0.03em;
                }

                .plan-date {
                    color: var(--muted);
                    font-size: 0.78rem;
                    margin-top: 0.35rem;
                }

                .plan-content {
                    min-width: 0;
                }

                .plan-title {
                    color: var(--text);
                    font-weight: 850;
                    font-size: 1.08rem;
                    margin-bottom: 0.45rem;
                }

                .plan-subtitle {
                    color: var(--muted);
                    font-size: 0.85rem;
                    margin-bottom: 0.55rem;
                }

                .empty-state {
                    border: 1px dashed rgba(148, 163, 184, 0.30);
                    background: rgba(15, 23, 42, 0.45);
                    border-radius: 15px;
                    padding: 0.9rem 1rem;
                    color: var(--muted-light);
                    font-size: 0.9rem;
                    margin-bottom: 0.6rem;
                }

                .success-state {
                    border: 1px solid rgba(34, 197, 94, 0.25);
                    background: rgba(34, 197, 94, 0.09);
                    border-radius: 15px;
                    padding: 0.9rem 1rem;
                    color: #BBF7D0;
                    font-size: 0.9rem;
                    margin-bottom: 0.6rem;
                }

                .warning-state {
                    border: 1px solid rgba(251, 191, 36, 0.25);
                    background: rgba(251, 191, 36, 0.09);
                    border-radius: 15px;
                    padding: 0.9rem 1rem;
                    color: #FDE68A;
                    font-size: 0.9rem;
                    margin-bottom: 0.6rem;
                }

                .stButton > button {
                    border-radius: 12px;
                    min-height: 2.55rem;
                    font-weight: 760;
                    border: 1px solid rgba(148, 163, 184, 0.24);
                    background: rgba(30, 41, 59, 0.86);
                    color: var(--text);
                    box-shadow: none;
                    transition: all 0.15s ease;
                }

                .stButton > button:hover {
                    transform: translateY(-1px);
                    border-color: rgba(56, 189, 248, 0.45);
                    background: rgba(30, 41, 59, 1);
                    color: white;
                }

                .stButton > button[kind="primary"] {
                    border: 1px solid rgba(56, 189, 248, 0.38);
                    background: #0EA5E9;
                    color: white;
                    box-shadow: 0 12px 28px rgba(14, 165, 233, 0.16);
                }

                .stButton > button[kind="primary"]:hover {
                    background: #0284C7;
                    box-shadow: 0 14px 32px rgba(14, 165, 233, 0.22);
                }

                label {
                    color: var(--muted-light) !important;
                    font-weight: 720 !important;
                }

                input,
                textarea,
                div[data-baseweb="select"] > div {
                    border-radius: 12px !important;
                }

                div[data-testid="stForm"] {
                    border: none;
                    padding: 0;
                }

                div[data-baseweb="tab-list"] {
                    gap: 0.3rem;
                    background: rgba(15, 23, 42, 0.62);
                    border: 1px solid rgba(148, 163, 184, 0.16);
                    padding: 0.3rem;
                    border-radius: 14px;
                    width: fit-content;
                    margin-bottom: 1rem;
                }

                button[data-baseweb="tab"] {
                    border-radius: 10px;
                    padding: 0.48rem 0.78rem;
                    color: var(--muted-light);
                    font-weight: 750;
                }

                button[data-baseweb="tab"][aria-selected="true"] {
                    background: rgba(56, 189, 248, 0.16);
                    color: #E0F2FE;
                }

                div[data-testid="stSlider"] div[role="slider"] {
                    background-color: var(--accent) !important;
                    border-color: var(--accent) !important;
                    box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.14) !important;
                }

                div[data-testid="stDataFrame"] {
                    border-radius: 16px;
                    overflow: hidden;
                    border: 1px solid rgba(148, 163, 184, 0.12);
                }

                hr {
                    border-color: rgba(148, 163, 184, 0.14);
                    margin: 1.25rem 0;
                }

                @media (max-width: 760px) {
                    .plan-layout {
                        grid-template-columns: 1fr;
                        gap: 0.8rem;
                    }

                    .plan-time-block {
                        border-right: none;
                        border-bottom: 1px solid rgba(148, 163, 184, 0.16);
                        padding-right: 0;
                        padding-bottom: 0.8rem;
                    }
                }

            /* Small red square delete button */
            div[data-testid="stButton"] button[data-testid="stBaseButton-tertiary"] {
                width: 34px !important;
                height: 34px !important;
                min-width: 34px !important;
                min-height: 34px !important;
                max-width: 34px !important;
                max-height: 34px !important;

                padding: 0 !important;
                margin: 0 !important;

                display: flex !important;
                align-items: center !important;
                justify-content: center !important;

                border-radius: 9px !important;
                border: 1px solid rgba(248, 113, 113, 0.85) !important;
                background: rgba(239, 68, 68, 0.16) !important;
                color: #FCA5A5 !important;

                font-size: 1.35rem !important;
                font-weight: 700 !important;
                line-height: 1 !important;
                text-align: center !important;

                box-shadow: none !important;
                transform: none !important;
            }

            div[data-testid="stButton"] button[data-testid="stBaseButton-tertiary"] p {
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1 !important;

                display: flex !important;
                align-items: center !important;
                justify-content: center !important;

                transform: translateY(-1px);
            }

            div[data-testid="stButton"] button[data-testid="stBaseButton-tertiary"]:hover {
                background: rgba(239, 68, 68, 0.26) !important;
                border-color: rgba(248, 113, 113, 1) !important;
                color: #FECACA !important;
                transform: none !important;
            }

            </style>
            """
        ),
        unsafe_allow_html=True,
    )


# ============================================================
# State
# ============================================================

def initialize_state():
    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    if "slots" not in st.session_state:
        st.session_state.slots = []

    if "next_task_id" not in st.session_state:
        st.session_state.next_task_id = 1

    if "plan_result" not in st.session_state:
        st.session_state.plan_result = None


def clear_all_data():
    st.session_state.tasks = []
    st.session_state.slots = []
    st.session_state.next_task_id = 1
    st.session_state.plan_result = None

def delete_task(task_id):
    st.session_state.tasks = [
        task for task in st.session_state.tasks
        if task.id != task_id
    ]
    st.session_state.plan_result = None


def delete_slot(slot_index):
    if 0 <= slot_index < len(st.session_state.slots):
        st.session_state.slots.pop(slot_index)
        st.session_state.plan_result = None

# ============================================================
# UI helpers
# ============================================================

def safe_text(value):
    return html.escape(str(value))


def render_html(markup):
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def render_empty(message):
    render_html(
        f"""
        <div class="empty-state">{safe_text(message)}</div>
        """
    )


def render_success(message):
    render_html(
        f"""
        <div class="success-state">{safe_text(message)}</div>
        """
    )


def render_warning(message):
    render_html(
        f"""
        <div class="warning-state">{safe_text(message)}</div>
        """
    )


def render_task_card(task):
    html_content = (
        f'<div class="list-card task-card">'
        f'<div class="task-header-row">'
        f'<div class="task-main-info">'
        f'<div class="list-kicker">Task</div>'
        f'<div class="list-title">{safe_text(task.name)}</div>'
        f'</div>'
        f'<div class="task-meta-inline">'
        f'<div class="task-meta-item">'
        f'<div class="task-meta-label">Duration</div>'
        f'<div class="task-meta-value">{format_minutes(task.duration_minutes)}</div>'
        f'</div>'
        f'<div class="task-meta-item">'
        f'<div class="task-meta-label">Deadline</div>'
        f'<div class="task-meta-value">{format_dt(task.deadline)}</div>'
        f'</div>'
        f'<div class="task-meta-item">'
        f'<div class="task-meta-label">Difficulty</div>'
        f'<div class="task-meta-value">{task.difficulty}/5</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html_content, unsafe_allow_html=True)


def render_slot_card(slot, index):
    html_content = (
        f'<div class="list-card slot-card">'
        f'<div class="slot-header-row">'
        f'<div class="slot-main-info">'
        f'<div class="list-kicker">Available study time</div>'
        f'<div class="list-title">Slot {index}</div>'
        f'</div>'
        f'<div class="slot-meta-inline">'
        f'<div class="slot-meta-item">'
        f'<div class="slot-meta-label">Start</div>'
        f'<div class="slot-meta-value">{format_dt(slot.start)}</div>'
        f'</div>'
        f'<div class="slot-meta-item">'
        f'<div class="slot-meta-label">End</div>'
        f'<div class="slot-meta-value">{format_dt(slot.end)}</div>'
        f'</div>'
        f'<div class="slot-meta-item">'
        f'<div class="slot-meta-label">Duration</div>'
        f'<div class="slot-meta-value">{format_minutes(minutes_between(slot.start, slot.end))}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html_content, unsafe_allow_html=True)


def render_plan_card(part):
    card_type = "suggested" if part.source == "suggested" else "scheduled"
    label = "Suggested extra slot" if part.source == "suggested" else "Scheduled from availability"

    start_time = part.start.strftime("%H:%M")
    end_time = part.end.strftime("%H:%M")
    date_label = part.start.strftime("%Y-%m-%d")

    html_content = (
        f'<div class="plan-card {card_type}">'
        f'<div class="plan-layout">'
        f'<div class="plan-time-block">'
        f'<div class="plan-time">{start_time} - {end_time}</div>'
        f'<div class="plan-date">{date_label}</div>'
        f'</div>'
        f'<div class="plan-content">'
        f'<div class="plan-title">{safe_text(part.task_name)}</div>'
        f'<div class="plan-subtitle">{safe_text(label)}</div>'
        f'<div class="chip-row">'
        f'<span class="chip">Duration: {format_minutes(part.minutes)}</span>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html_content, unsafe_allow_html=True)


def generate_plan():
    if not st.session_state.tasks:
        st.error("Please add at least one task first.")
        return

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

    st.session_state.plan_result = {
        "scored_tasks": scored_tasks,
        "schedule": schedule,
        "unfinished": unfinished,
        "suggestions": suggestions,
        "still_unfinished": still_unfinished,
        "final_parts": final_parts,
        "remaining_free_slots": remaining_free_slots,
    }


# ============================================================
# App
# ============================================================

inject_css()
initialize_state()

render_html(
    """
    <div class="hero">
        <div class="eyebrow">Algorithms in Data Science</div>
        <div class="title">Smart Study Planner</div>
        <div class="subtitle">
            Add tasks, add availability, and generate a study plan.
            The final schedule is shown first, while the algorithm details stay available for your presentation.
        </div>
    </div>
    """
)


# ============================================================
# Step 1: Add tasks
# ============================================================

render_html('<div class="step-title">Step 1: Add your tasks</div>')
render_html(
    '<div class="step-copy">Enter what needs to be done. The deadline is used to calculate urgency automatically.</div>'
)

with st.container(border=True):
    with st.form("task_form", clear_on_submit=True):
        task_name = st.text_input(
            "Task name",
            placeholder="Example: Algorithms Assignment",
        )

        form_col_1, form_col_2, form_col_3, form_col_4 = st.columns([1, 1, 1, 1])

        with form_col_1:
            duration_hours = st.number_input(
                "Duration",
                min_value=0.25,
                max_value=20.0,
                step=0.25,
                value=1.0,
                help="Duration in hours",
            )

        with form_col_2:
            deadline_date = st.date_input("Deadline date", key="deadline_date")

        with form_col_3:
            deadline_time = st.time_input(
                "Deadline time",
                value=time(23, 0),
                step=900,
                key="deadline_time",
            )

        with form_col_4:
            difficulty = st.slider(
                "Difficulty",
                min_value=1,
                max_value=5,
                value=3,
            )

        submitted_task = st.form_submit_button("Add task", width='stretch')

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
                st.session_state.plan_result = None
                st.success("Task added.")

if st.session_state.tasks:
    for task in st.session_state.tasks:
        card_col, delete_col = st.columns(
            [24, 1],
            gap="small",
            vertical_alignment="center",
        )

        with card_col:
            render_task_card(task)

        with delete_col:
            if st.button("✖", key=f"delete_task_{task.id}", help="Remove task", type="tertiary"):
                delete_task(task.id)
                st.rerun()
else:
    render_empty("No tasks added yet.")

# ============================================================
# Step 2: Add availability
# ============================================================

render_html('<div class="step-title">Step 2: Add your available study time</div>')
render_html(
    '<div class="step-copy">These are the slots the scheduler will try to use before suggesting extra time.</div>'
)

with st.container(border=True):
    with st.form("slot_form", clear_on_submit=True):
        slot_col_1, slot_col_2, slot_col_3 = st.columns(3)

        with slot_col_1:
            slot_date = st.date_input("Slot date", key="slot_date")

        with slot_col_2:
            start_time = st.time_input(
                "Start time",
                value=time(18, 0),
                step=900,
                key="slot_start",
            )

        with slot_col_3:
            end_time = st.time_input(
                "End time",
                value=time(20, 0),
                step=900,
                key="slot_end",
            )

        submitted_slot = st.form_submit_button("Add available slot", width='stretch')

        if submitted_slot:
            start = datetime.combine(slot_date, start_time)
            end = datetime.combine(slot_date, end_time)

            if end <= start:
                st.error("End time must be after start time.")
            else:
                st.session_state.slots.append(TimeSlot(start, end))
                st.session_state.plan_result = None
                st.success("Available slot added.")

if st.session_state.slots:
    for index, slot in enumerate(st.session_state.slots):
        card_col, delete_col = st.columns(
            [24, 1],
            gap="small",
            vertical_alignment="center",
        )

        with card_col:
            render_slot_card(slot, index + 1)

        with delete_col:
            if st.button("✖", key=f"delete_slot_{index}", help="Remove available slot", type="tertiary"):
                delete_slot(index)
                st.rerun()
else:
    render_empty("No available slots added yet.")
# ============================================================
# Step 3: Generate
# ============================================================

render_html('<div class="step-title">Step 3: Generate the study plan</div>')
render_html(
    '<div class="step-copy">Run the algorithm chain after adding your tasks and available time.</div>'
)

button_col_1, button_col_2, button_space = st.columns([1.5, 1, 2.5])

with button_col_1:
    if st.button("Generate study plan", type="primary", width='stretch'):
        generate_plan()

with button_col_2:
    if st.button("Clear all", width='stretch'):
        clear_all_data()
        st.success("All data cleared.")

# ============================================================
# Output
# ============================================================

render_html('<div class="step-title">Final output</div>')

if st.session_state.plan_result:
    result = st.session_state.plan_result

    if result["final_parts"]:
        for part in result["final_parts"]:
            render_plan_card(part)
    else:
        render_empty("No final schedule was created.")

    if result["still_unfinished"]:
        render_warning("Some tasks still could not be fully planned.")
    elif result["suggestions"]:
        render_warning("The planner created extra suggested study time.")
    else:
        render_success("All tasks fit into the provided availability.")

    with st.expander("Show algorithm details"):
        alg_tab_1, alg_tab_2, alg_tab_3 = st.tabs(
            [
                "1. Priority scoring",
                "2. Greedy scheduling",
                "3. Slot suggestions",
            ]
        )

        with alg_tab_1:
            score_rows = []

            for task in sorted(result["scored_tasks"], key=lambda t: (-t.priority, t.deadline)):
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

            st.dataframe(score_rows, width='stretch', hide_index=True)

        with alg_tab_2:
            if result["schedule"]:
                for part in result["schedule"]:
                    render_plan_card(part)
            else:
                render_empty("No tasks could be scheduled using the provided availability.")

            if result["unfinished"]:
                unfinished_rows = [
                    {
                        "Task": item.task.name,
                        "Remaining time": format_minutes(item.remaining_minutes),
                        "Reason": item.reason,
                    }
                    for item in result["unfinished"]
                ]

                st.dataframe(unfinished_rows, width='stretch', hide_index=True)

        with alg_tab_3:
            if result["suggestions"]:
                for part in result["suggestions"]:
                    render_plan_card(part)
            else:
                render_empty("No extra suggestions were needed or possible.")

            if result["still_unfinished"]:
                still_rows = [
                    {
                        "Task": item.task.name,
                        "Remaining time": format_minutes(item.remaining_minutes),
                        "Reason": item.reason,
                    }
                    for item in result["still_unfinished"]
                ]

                st.dataframe(still_rows, width='stretch', hide_index=True)

    with st.expander("Big O summary for presentation"):
        st.markdown(
            """
            **Algorithm 1: Feasibility-Aware Deadline-Weighted Priority Scoring**  
            Time: `O(T*S)` because every task checks the available slots before its deadline.  
            Space: `O(T)` for the scored task list.

            **Algorithm 2: Greedy Split Scheduling with Max Heap**  
            Time: `O(T log T + T*S)`, where `T` is tasks and `S` is available slots.  
            The `T log T` part comes from heap insertion/removal. The `T*S` part comes from checking available slots.

            **Algorithm 3: Suggested Slot Generation**  
            Time: `O(U*D*P)`, where `U` is unfinished tasks, `D` is days searched, and `P` is scheduled parts checked for overlaps.

            **Primary bottleneck:** Algorithm 2, because scheduling may need to check many tasks against many available slots.
            """
        )
else:
    render_empty("No plan generated yet.")