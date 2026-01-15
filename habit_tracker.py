import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta


@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client using Streamlit secrets."""
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )


def load_habits(supabase):
    """Load habits list from Supabase."""
    response = supabase.table("habits").select("*").order("created_at").execute()
    return [row["name"] for row in response.data]


def save_habit(supabase, habit_name):
    """Add a new habit to Supabase."""
    supabase.table("habits").insert({"name": habit_name}).execute()


def remove_habit(supabase, habit_name):
    """Remove a habit from Supabase."""
    supabase.table("habits").delete().eq("name", habit_name).execute()
    # Also remove all completions for this habit
    supabase.table("completions").delete().eq("habit_name", habit_name).execute()


def load_completions(supabase):
    """Load completions data from Supabase."""
    response = supabase.table("completions").select("*").execute()

    completions = {}
    for row in response.data:
        date_str = row["date"]
        habit_name = row["habit_name"]
        if date_str not in completions:
            completions[date_str] = []
        completions[date_str].append(habit_name)

    return completions


def toggle_completion(supabase, date_str, habit_name, is_completed):
    """Toggle completion status for a habit on a specific date."""
    if is_completed:
        # Add completion
        supabase.table("completions").insert({
            "date": date_str,
            "habit_name": habit_name
        }).execute()
    else:
        # Remove completion
        supabase.table("completions").delete().eq("date", date_str).eq("habit_name", habit_name).execute()


def get_streak(habit_name, completions):
    """Calculate current streak for a habit."""
    streak = 0
    check_date = datetime.now().date()

    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in completions and habit_name in completions[date_str]:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


def main():
    st.set_page_config(page_title="Daily Habit Tracker", page_icon="✅", layout="wide")

    st.title("📋 Daily Habit Tracker")
    st.markdown("Track your daily habits and build streaks!")

    # Initialize Supabase connection
    try:
        supabase = get_supabase_client()
    except Exception as e:
        st.error("Failed to connect to Supabase. Please check your credentials.")
        st.code(str(e))
        st.stop()

    # Load data from Supabase
    habits = load_habits(supabase)
    completions = load_completions(supabase)

    # Sidebar for adding new habits
    with st.sidebar:
        st.header("➕ Add New Habit")
        new_habit = st.text_input("Habit name", placeholder="e.g., Exercise, Read, Meditate")

        if st.button("Add Habit", type="primary"):
            if new_habit and new_habit not in habits:
                save_habit(supabase, new_habit)
                st.success(f"Added '{new_habit}'!")
                st.rerun()
            elif new_habit in habits:
                st.warning("Habit already exists!")
            else:
                st.warning("Please enter a habit name.")

        st.divider()

        # Remove habit section
        if habits:
            st.header("🗑️ Remove Habit")
            habit_to_remove = st.selectbox("Select habit to remove", habits)
            if st.button("Remove", type="secondary"):
                remove_habit(supabase, habit_to_remove)
                st.success(f"Removed '{habit_to_remove}'!")
                st.rerun()

    # Main content area
    today = datetime.now().strftime("%Y-%m-%d")
    st.subheader(f"📅 Today: {datetime.now().strftime('%A, %B %d, %Y')}")

    if not habits:
        st.info("👈 Add your first habit using the sidebar!")
    else:
        # Initialize today's completions if not exists
        if today not in completions:
            completions[today] = []

        # Display habits with checkboxes
        st.markdown("### Today's Habits")

        cols = st.columns([3, 1, 1])
        cols[0].markdown("**Habit**")
        cols[1].markdown("**Status**")
        cols[2].markdown("**Streak**")

        for habit in habits:
            cols = st.columns([3, 1, 1])

            with cols[0]:
                st.markdown(f"**{habit}**")

            with cols[1]:
                is_completed = habit in completions.get(today, [])
                checkbox_value = st.checkbox(
                    "Done",
                    value=is_completed,
                    key=f"check_{habit}",
                    label_visibility="collapsed"
                )

                if checkbox_value != is_completed:
                    toggle_completion(supabase, today, habit, checkbox_value)
                    if checkbox_value:
                        completions.setdefault(today, []).append(habit)
                    else:
                        completions[today].remove(habit)

            with cols[2]:
                streak = get_streak(habit, completions)
                if streak > 0:
                    st.markdown(f"🔥 {streak} day{'s' if streak > 1 else ''}")
                else:
                    st.markdown("—")

        # Progress summary
        st.divider()
        completed_today = len(completions.get(today, []))
        total_habits = len(habits)
        progress = completed_today / total_habits if total_habits > 0 else 0

        st.markdown("### Today's Progress")
        st.progress(progress)
        st.markdown(f"**{completed_today}/{total_habits}** habits completed")

        # Weekly overview
        st.divider()
        st.markdown("### 📊 Last 7 Days")

        week_cols = st.columns(7)
        for i in range(6, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            day_name = date.strftime("%a")

            with week_cols[6-i]:
                completed = len(completions.get(date_str, []))
                st.metric(
                    label=day_name,
                    value=f"{completed}/{total_habits}",
                    delta=None
                )


if __name__ == "__main__":
    main()
