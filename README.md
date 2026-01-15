# Habit Tracker

A personal habit tracking web application built with Streamlit and Supabase.

## Features

- **User Authentication**: Secure login with username/password
- **Access Code Registration**: New accounts require an access code (invite-only)
- **Multiple Habit Types**: Track daily, weekly, and monthly habits
- **Streak Tracking**: See consecutive streaks for each habit (days, weeks, or months)
- **Progress Tracking**: Visual progress bars for each habit category
- **Overview Dashboard**: See completion stats across all habit types

## Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **Deployment**: [Streamlit Cloud](https://share.streamlit.io/)

## Setup Instructions

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your **Project URL** and **anon public key** from Settings → API

### 2. Set Up Database Tables

Run this SQL in the Supabase SQL Editor:

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Access codes table (for invite-only registration)
CREATE TABLE access_codes (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Habits table (per user, with type)
CREATE TABLE habits (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    habit_type TEXT NOT NULL DEFAULT 'daily',  -- 'daily', 'weekly', or 'monthly'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, username)
);

-- Completions table (per user, with period_key for flexible tracking)
CREATE TABLE completions (
    id SERIAL PRIMARY KEY,
    period_key TEXT NOT NULL,  -- '2024-01-15' for daily, '2024-W03' for weekly, '2024-01' for monthly
    habit_name TEXT NOT NULL,
    username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(period_key, habit_name, username)
);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE completions ENABLE ROW LEVEL SECURITY;

-- Policies (allow all for simplicity - the app handles auth)
CREATE POLICY "Allow all" ON users FOR ALL USING (true);
CREATE POLICY "Allow all" ON access_codes FOR ALL USING (true);
CREATE POLICY "Allow all" ON habits FOR ALL USING (true);
CREATE POLICY "Allow all" ON completions FOR ALL USING (true);
```

### 3. Create Access Codes

To allow users to register, insert access codes:

```sql
INSERT INTO access_codes (code) VALUES
    ('INVITE001'),
    ('INVITE002'),
    ('INVITE003');
```

### 4. Configure Secrets

#### For Local Development

Create `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://your-project-id.supabase.co"
key = "your-anon-public-key"
```

#### For Streamlit Cloud

Add secrets in your app's Settings → Secrets:

```toml
[supabase]
url = "https://your-project-id.supabase.co"
key = "your-anon-public-key"
```

### 5. Run Locally

```bash
pip install -r requirements.txt
streamlit run habit_tracker.py
```

### 6. Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" and select your repository
4. Set main file to `habit_tracker.py`
5. Add your Supabase secrets in Advanced Settings
6. Deploy!

## Habit Types

| Type | Tracking Period | Streak Unit | Example |
|------|-----------------|-------------|---------|
| Daily | Each day | Days | Exercise, Meditate |
| Weekly | Each week (Mon-Sun) | Weeks | Meal prep, Deep clean |
| Monthly | Each month | Months | Budget review, Doctor visit |

## Managing Access Codes

To generate new access codes, run this in Supabase SQL Editor:

```sql
-- Add a single code
INSERT INTO access_codes (code) VALUES ('NEWCODE123');

-- View all codes and their status
SELECT code, used, used_by, created_at FROM access_codes ORDER BY created_at DESC;
```

## License

MIT
