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
    return [row["name"] for row in response.data]


def save_habit(supabase, username, habit_name):
    """Add a new habit to Supabase."""
    supabase.table("habits").insert({"name": habit_name, "username": username}).execute()


def remove_habit(supabase, username, habit_name):
    """Remove a habit from Supabase."""
    supabase.table("habits").delete().eq("name", habit_name).eq("username", username).execute()
    supabase.table("completions").delete().eq("habit_name", habit_name).eq("username", username).execute()


def load_completions(supabase, username):
    """Load completions data from Supabase for a specific user."""
    response = supabase.table("completions").select("*").eq("username", username).execute()

    completions = {}
    for row in response.data:
        date_str = row["date"]
        habit_name = row["habit_name"]
        if date_str not in completions:
            completions[date_str] = []
        completions[date_str].append(habit_name)

    return completions


def toggle_completion(supabase, username, date_str, habit_name, is_completed):
    """Toggle completion status for a habit on a specific date."""
    if is_completed:
        supabase.table("completions").insert({
            "date": date_str,
            "habit_name": habit_name,
            "username": username
        }).execute()
    else:
        supabase.table("completions").delete().eq("date", date_str).eq("habit_name", habit_name).eq("username", username).execute()


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


def show_main_app(supabase, username):
    """Display the main habit tracker app."""
    st.set_page_config(page_title="Daily Habit Tracker", page_icon="✅", layout="wide")

    # Header with logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("📋 Daily Habit Tracker")
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

        if st.button("Add Habit", type="primary"):
            if new_habit and new_habit not in habits:
                save_habit(supabase, username, new_habit)
                st.success(f"Added '{new_habit}'!")
                st.rerun()
            elif new_habit in habits:
                st.warning("Habit already exists!")
            else:
                st.warning("Please enter a habit name.")

        st.divider()

        if habits:
            st.header("🗑️ Remove Habit")
            habit_to_remove = st.selectbox("Select habit to remove", habits)
            if st.button("Remove", type="secondary"):
                remove_habit(supabase, username, habit_to_remove)
                st.success(f"Removed '{habit_to_remove}'!")
                st.rerun()

    # Main content area
    today = datetime.now().strftime("%Y-%m-%d")
    st.subheader(f"📅 Today: {datetime.now().strftime('%A, %B %d, %Y')}")

    if not habits:
        st.info("👈 Add your first habit using the sidebar!")
    else:
        if today not in completions:
            completions[today] = []

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
                    toggle_completion(supabase, username, today, habit, checkbox_value)
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
