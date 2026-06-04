# Smart Scheduler Agent

An AI-powered scheduling assistant that understands natural language and manages your Google Calendar automatically. Built with Google Gemini and Streamlit.

**[Try it live →](https://smart-scheduler-agent-gbgjyqricckdghcqwiwb8q.streamlit.app/)**

---

## What it does

You describe what you need in plain language — the agent figures out the rest:

- **"Schedule a team meeting next Tuesday at 3pm for 1 hour"** → creates the event
- **"What do I have on Friday?"** → reads and summarizes your calendar
- **"Move my dentist appointment to Thursday morning"** → finds and updates it
- **"Cancel my 4pm tomorrow"** → deletes the event

No manual form-filling. Just talk to it.

---

## Tech stack

| Layer | Technology |
|---|---|
| AI model | Google Gemini (via `google-generativeai`) |
| Frontend | Streamlit |
| Calendar integration | Google Calendar API v3 |
| Auth | OAuth 2.0 (Google) |
| Deployment | Streamlit Cloud |

---

## Features

- **Natural language understanding** — Gemini interprets user intent and extracts event details (date, time, duration, title, attendees)
- **Full CRUD on calendar events** — create, read, update, and delete
- **Persistent chat memory** — conversation history is kept in session state so context carries across turns
- **Secure OAuth flow** — users authenticate with their own Google account; no credentials are stored by the app
- **Streaming UI** — responses appear progressively for a smoother experience

---

## Architecture

```
User input (Streamlit chat)
        ↓
  Gemini API (intent + entity extraction)
        ↓
  Google Calendar API (action execution)
        ↓
  Response streamed back to UI
```

The agent uses Gemini to parse intent and extract structured data from free-text, then calls the appropriate Google Calendar API endpoint based on the action type (insert / list / patch / delete).

---

## Running locally

### Prerequisites

- Python 3.10+
- A Google Cloud project with the **Google Calendar API** enabled
- OAuth 2.0 credentials (Desktop app type) downloaded as `credentials.json`
- A Gemini API key

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/smart-scheduler-agent.git
cd smart-scheduler-agent
pip install -r requirements.txt
```

Add your secrets to `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your_gemini_api_key"

[gcp_service_account]
# paste your OAuth credentials JSON fields here
```

Or set them as environment variables.

### Run

```bash
streamlit run app.py
```

On first run, a browser window will open for Google OAuth authorization. A `token.json` file will be saved locally for subsequent runs.

---

## Deployment (Streamlit Cloud)

1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Add secrets in the Streamlit Cloud dashboard (Settings → Secrets)
4. Set the app visibility to **Public** if you want others to use it

> **Note on OAuth verification:** This app uses the `https://www.googleapis.com/auth/calendar.events` scope, which requires Google verification for unrestricted public use. During development / class use, you can add specific Gmail addresses as test users in your GCP project's OAuth consent screen (up to 100 users without verification).

---

## Project structure

```
smart-scheduler-agent/
├── app.py                  # Main Streamlit app
├── requirements.txt
├── .streamlit/
│   └── secrets.toml        # (local only, gitignored)
└── README.md
```

---

## Known limitations

- Requires users to be added as OAuth test users unless the app goes through Google's verification process
- Timezone handling depends on the calendar's default timezone
- Recurring event editing is not yet supported

---

## Built with

- [Streamlit](https://streamlit.io/)
- [Google Gemini API](https://ai.google.dev/)
- [Google Calendar API](https://developers.google.com/calendar)

---

*Built as part of a data & AI engineering program.*
