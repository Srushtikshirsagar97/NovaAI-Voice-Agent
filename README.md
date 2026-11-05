# NovaAI Voice Agent — Full-Stack Groq AI Project

An interactive voice-agent project with a responsive animated UI, Python Flask backend, Groq-hosted AI responses, browser speech recognition/text-to-speech, configurable personas, transcript export, and SQLite conversation storage. **It does not use Google Gemini and does not require a large AI model download.**

## Features

- Interactive animated voice orb and agent status states
- Four personas: customer support, technical interviewer, language tutor, executive assistant
- Voice input through the browser Web Speech API (Chrome/Edge support varies by browser and OS)
- Spoken replies through browser text-to-speech; voice, speed, pitch, mute and auto-loop controls
- Text chat fallback
- Editable persona instructions
- Transcript copy/export and reset
- Flask backend sends chat messages to Groq's API
- SQLite stores each user/assistant exchange; history API is available at `/api/history/<session_id>`
- Health endpoint at `/api/health`
- No Ollama installation or local AI model download required

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.10 or newer recommended
- Internet connection
- Groq API key from **https://console.groq.com/**
- Chrome or Edge recommended for browser speech recognition

Groq runs the AI model in the cloud, so prompts are sent to Groq over the internet. API availability, models, and free usage limits can change; check your Groq console for current details. Browser speech recognition may also depend on browser/OS services.

## Setup on Windows using VS Code

### 1. Get a Groq API key

1. Open **https://console.groq.com/** and sign in.
2. Create an API key from the API keys section.
3. Copy the key and keep it private. Do not post it publicly or commit it to GitHub.

### 2. Open the project

1. Extract the ZIP file.
2. Open the extracted `novaai_voice_agent` folder in VS Code.
3. Choose **Terminal → New Terminal**.

### 3. Create and activate a Python virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use ` .\.venv\Scripts\python.exe ` instead of `python` in the commands below.

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Configure the API key

1. In VS Code, copy `.env.example` and name the copy `.env` (same folder as `app.py`).
2. Open `.env` and replace `put_your_groq_api_key_here` with your actual key:

```env
GROQ_API_KEY=your_actual_key_here
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
GROQ_MODEL=llama-3.3-70b-versatile
PORT=5000
FLASK_DEBUG=false
```

Do not include quotation marks around the key. If the default model is unavailable in your Groq account, check the currently supported model names in the Groq console and update `GROQ_MODEL` accordingly.

### 6. Run the project

```powershell
python app.py
```

Open **http://127.0.0.1:5000** in Chrome or Edge and allow microphone access. You can also type in the chat box.

To check configuration, open **http://127.0.0.1:5000/api/health**. It reports whether an API key is configured; it does not expose the key.

## API endpoints

### `POST /api/chat`

Example request JSON:

```json
{
  "session_id": "demo-session",
  "scenario_id": "support",
  "system_instruction": "You are a helpful concise assistant.",
  "latest_user_message": "Hello",
  "history": [
    {"role": "user", "text": "Hello"}
  ]
}
```

Example response:

```json
{"reply": "Hello! What can I help you with today?", "model": "llama-3.3-70b-versatile", "provider": "groq"}
```

### `GET /api/history/<session_id>`

Returns up to the latest 100 saved messages for that session.

### `GET /api/health`

Reports app status, selected Groq model, and whether the API key is configured.

## Troubleshooting

- **Missing API key:** make sure `.env` is in the same folder as `app.py`, and `GROQ_API_KEY` contains your actual key. Restart `python app.py` after changing `.env`.
- **Invalid API key:** create or copy a valid key in the Groq console.
- **Model unavailable:** update `GROQ_MODEL` to a model currently available in your Groq account, then restart the app.
- **Rate/usage limit:** check the Groq console for current limits and retry later if needed.
- **Network error:** check your internet connection.
- **Microphone not working:** use a recent Chrome or Edge browser and grant microphone permission. Text chat remains available.

## Security and project notes

- Never share your API key or commit `.env` to GitHub. `.env` is excluded by `.gitignore`.
- The project stores conversation messages in a local SQLite database (`novaai.db`).
- Chat prompts are sent to Groq to generate replies. Do not send confidential or sensitive information.
- Do not use this demo as an emergency service or as a replacement for professional medical, legal, or financial advice.
- Before public deployment, add authentication, per-user session authorization, rate limiting, HTTPS, privacy/retention controls, and stronger input validation. The browser session ID is a demo identifier, not secure authentication.
