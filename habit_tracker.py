import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import hashlib


@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client using Streamlit secrets."""
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )


def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_access_code(supabase, code):
    """Check if access code is valid and unused."""
    response = supabase.table("access_codes").select("*").eq("code", code).eq("used", False).execute()
    return len(response.data) > 0


def mark_access_code_used(supabase, code, username):
    """Mark access code as used."""
    supabase.table("access_codes").update({"used": True, "used_by": username}).eq("code", code).execute()


def create_user(supabase, username, password):
    """Create a new user."""
    password_hash = hash_password(password)
    try:
        supabase.table("users").insert({
            "username": username,
            "password_hash": password_hash
        }).execute()
        return True
    except Exception:
        return False


def verify_user(supabase, username, password):
    """Verify user credentials."""
    password_hash = hash_password(password)
    response = supabase.table("users").select("*").eq("username", username).eq("password_hash", password_hash).execute()
    return len(response.data) > 0


def user_exists(supabase, username):
    """Check if username already exists."""
    response = supabase.table("users").select("username").eq("username", username).execute()
    return len(response.data) > 0


def load_habits(supabase, username):
    """Load habits list from Supabase for a specific user."""
    response = supabase.table("habits").select("*").eq("username", username).order("created_at").execute()
    return response.data


def save_habit(supabase, username, habit_name, habit_type):
    """Add a new habit to Supabase."""
    supabase.table("habits").insert({
        "name": habit_name,
        "username": username,
        "habit_type": habit_type
    }).execute()


def remove_habit(supabase, username, habit_name):
    """Remove a habit from Supabase."""
    supabase.table("habits").delete().eq("name", habit_name).eq("username", username).execute()
    supabase.table("completions").delete().eq("habit_name", habit_name).eq("username", username).execute()


def load_completions(supabase, username):
    """Load completions data from Supabase for a specific user."""
    response = supabase.table("completions").select("*").eq("username", username).execute()

    completions = {}
    for row in response.data:
        period_key = row["period_key"]
        habit_name = row["habit_name"]
        if period_key not in completions:
            completions[period_key] = []
        completions[period_key].append(habit_name)

    return completions


def toggle_completion(supabase, username, period_key, habit_name, is_completed):
    """Toggle completion status for a habit on a specific period."""
    if is_completed:
        supabase.table("completions").insert({
            "period_key": period_key,
            "habit_name": habit_name,
            "username": username
        }).execute()
    else:
        supabase.table("completions").delete().eq("period_key", period_key).eq("habit_name", habit_name).eq("username", username).execute()


def get_period_key(habit_type, date=None):
    """Get the period key for a habit type."""
    if date is None:
        date = datetime.now()

    if habit_type == "daily":
        return date.strftime("%Y-%m-%d")
    elif habit_type == "weekly":
        # Use ISO week number (Monday as start of week)
        return date.strftime("%Y-W%W")
    elif habit_type == "monthly":
        return date.strftime("%Y-%m")
    return date.strftime("%Y-%m-%d")


def get_period_label(habit_type):
    """Get a human-readable label for the current period."""
    now = datetime.now()

    if habit_type == "daily":
        return now.strftime("%A, %B %d, %Y")
    elif habit_type == "weekly":
        # Get start and end of current week
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return f"Week of {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
    elif habit_type == "monthly":
        return now.strftime("%B %Y")
    return ""


def get_streak(habit_name, habit_type, completions):
    """Calculate current streak for a habit based on its type."""
    streak = 0
    check_date = datetime.now()

    while True:
        period_key = get_period_key(habit_type, check_date)

        if period_key in completions and habit_name in completions[period_key]:
            streak += 1
            # Move to previous period
            if habit_type == "daily":
                check_date -= timedelta(days=1)
            elif habit_type == "weekly":
                check_date -= timedelta(weeks=1)
            elif habit_type == "monthly":
                # Move to previous month
                if check_date.month == 1:
                    check_date = check_date.replace(year=check_date.year - 1, month=12)
                else:
                    check_date = check_date.replace(month=check_date.month - 1)
        else:
            break

        # Safety limit
        if streak > 365:
            break

    return streak


def get_streak_unit(habit_type):
    """Get the unit for streak display."""
    if habit_type == "daily":
        return "day"
    elif habit_type == "weekly":
        return "week"
    elif habit_type == "monthly":
        return "month"
    return "day"


def show_login_page(supabase):
    """Display login/signup page."""
    st.title("📋 Daily Habit Tracker")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary"):
            if login_username and login_password:
                if verify_user(supabase, login_username, login_password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = login_username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")

    with tab2:
        st.subheader("Create Account")
        st.info("You need an access code to create an account")

        signup_username = st.text_input("Choose Username", key="signup_username")
        signup_password = st.text_input("Choose Password", type="password", key="signup_password")
        signup_password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
        access_code = st.text_input("Access Code", key="access_code")

        if st.button("Create Account", type="primary"):
            if not all([signup_username, signup_password, signup_password_confirm, access_code]):
                st.warning("Please fill in all fields")
            elif len(signup_password) < 6:
                st.warning("Password must be at least 6 characters")
            elif signup_password != signup_password_confirm:
                st.error("Passwords do not match")
            elif user_exists(supabase, signup_username):
                st.error("Username already taken")
            elif not verify_access_code(supabase, access_code):
                st.error("Invalid or already used access code")
            else:
                if create_user(supabase, signup_username, signup_password):
                    mark_access_code_used(supabase, access_code, signup_username)
                    st.success("Account created! Please login.")
                else:
                    st.error("Failed to create account. Please try again.")


def render_habit_section(supabase, username, habits, completions, habit_type, icon, title):
    """Render a section for a specific habit type."""
    type_habits = [h for h in habits if h.get("habit_type", "daily") == habit_type]

    if not type_habits:
        return

    period_key = get_period_key(habit_type)
    period_label = get_period_label(habit_type)
    streak_unit = get_streak_unit(habit_type)

    st.markdown(f"### {icon} {title}")
    st.caption(f"📅 {period_label}")

    cols = st.columns([3, 1, 1])
    cols[0].markdown("**Habit**")
    cols[1].markdown("**Status**")
    cols[2].markdown("**Streak**")

    for habit in type_habits:
        habit_name = habit["name"]
        cols = st.columns([3, 1, 1])

        with cols[0]:
            st.markdown(f"**{habit_name}**")

        with cols[1]:
            is_completed = habit_name in completions.get(period_key, [])
            checkbox_value = st.checkbox(
                "Done",
                value=is_completed,
                key=f"check_{habit_type}_{habit_name}",
                label_visibility="collapsed"
            )

            if checkbox_value != is_completed:
                toggle_completion(supabase, username, period_key, habit_name, checkbox_value)
                if checkbox_value:
                    completions.setdefault(period_key, []).append(habit_name)
                else:
                    completions[period_key].remove(habit_name)

        with cols[2]:
            streak = get_streak(habit_name, habit_type, completions)
            if streak > 0:
                st.markdown(f"🔥 {streak} {streak_unit}{'s' if streak > 1 else ''}")
            else:
                st.markdown("—")

    # Progress for this type
    completed_count = sum(1 for h in type_habits if h["name"] in completions.get(period_key, []))
    total_count = len(type_habits)
    progress = completed_count / total_count if total_count > 0 else 0
    st.progress(progress)
    st.caption(f"{completed_count}/{total_count} completed")
    st.divider()


def show_main_app(supabase, username):
    """Display the main habit tracker app."""
    st.set_page_config(page_title="Daily Habit Tracker", page_icon="✅", layout="wide")

    # Header with logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("📋 Habit Tracker")
    with col2:
        st.write("")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    st.markdown(f"Welcome, **{username}**!")

    # Load user's data
    habits = load_habits(supabase, username)
    completions = load_completions(supabase, username)

    # Sidebar for adding new habits
    with st.sidebar:
        st.header("➕ Add New Habit")
        new_habit = st.text_input("Habit name", placeholder="e.g., Exercise, Read, Meditate")
        habit_type = st.selectbox(
            "Frequency",
            options=["daily", "weekly", "monthly"],
            format_func=lambda x: {"daily": "📅 Daily", "weekly": "📆 Weekly", "monthly": "🗓️ Monthly"}[x]
        )

        if st.button("Add Habit", type="primary"):
            existing_names = [h["name"] for h in habits]
            if new_habit and new_habit not in existing_names:
                save_habit(supabase, username, new_habit, habit_type)
                st.success(f"Added '{new_habit}'!")
                st.rerun()
            elif new_habit in existing_names:
                st.warning("Habit already exists!")
            else:
                st.warning("Please enter a habit name.")

        st.divider()

        if habits:
            st.header("🗑️ Remove Habit")
            habit_names = [h["name"] for h in habits]
            habit_to_remove = st.selectbox("Select habit to remove", habit_names)
            if st.button("Remove", type="secondary"):
                remove_habit(supabase, username, habit_to_remove)
                st.success(f"Removed '{habit_to_remove}'!")
                st.rerun()

    # Main content area
    if not habits:
        st.info("👈 Add your first habit using the sidebar!")
    else:
        # Render each habit type section
        render_habit_section(supabase, username, habits, completions, "daily", "📅", "Daily Habits")
        render_habit_section(supabase, username, habits, completions, "weekly", "📆", "Weekly Habits")
        render_habit_section(supabase, username, habits, completions, "monthly", "🗓️", "Monthly Habits")

        # Overall stats
        st.markdown("### 📊 Overview")

        col1, col2, col3 = st.columns(3)

        daily_habits = [h for h in habits if h.get("habit_type", "daily") == "daily"]
        weekly_habits = [h for h in habits if h.get("habit_type") == "weekly"]
        monthly_habits = [h for h in habits if h.get("habit_type") == "monthly"]

        with col1:
            daily_key = get_period_key("daily")
            daily_done = sum(1 for h in daily_habits if h["name"] in completions.get(daily_key, []))
            st.metric("Daily", f"{daily_done}/{len(daily_habits)}")

        with col2:
            weekly_key = get_period_key("weekly")
            weekly_done = sum(1 for h in weekly_habits if h["name"] in completions.get(weekly_key, []))
            st.metric("Weekly", f"{weekly_done}/{len(weekly_habits)}")

        with col3:
            monthly_key = get_period_key("monthly")
            monthly_done = sum(1 for h in monthly_habits if h["name"] in completions.get(monthly_key, []))
            st.metric("Monthly", f"{monthly_done}/{len(monthly_habits)}")


def main():
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # Initialize Supabase connection
    try:
        supabase = get_supabase_client()
    except Exception as e:
        st.error("Failed to connect to Supabase. Please check your credentials.")
        st.code(str(e))
        st.stop()

    # Show login or main app based on authentication state
    if not st.session_state["authenticated"]:
        st.set_page_config(page_title="Habit Tracker - Login", page_icon="✅")
        show_login_page(supabase)
    else:
        show_main_app(supabase, st.session_state["username"])


if __name__ == "__main__":
    main()
