import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "novaai.db"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'model')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id)
        """)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "NovaAI Voice Agent",
        "ai_provider": "Groq API",
        "ai_available": bool(GROQ_API_KEY),
        "model": GROQ_MODEL,
        "api_key_configured": bool(GROQ_API_KEY),
    })


@app.get("/api/history/<session_id>")
def history(session_id):
    with get_db() as db:
        rows = db.execute(
            """SELECT role, content, created_at, scenario_id
               FROM messages WHERE session_id = ?
               ORDER BY id DESC LIMIT 100""",
            (session_id,)
        ).fetchall()
    return jsonify({"messages": [dict(row) for row in reversed(rows)]})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    scenario_id = str(payload.get("scenario_id", "support")).strip()[:80]
    system_instruction = str(payload.get("system_instruction", "")).strip()
    latest_user_message = str(payload.get("latest_user_message", "")).strip()
    history_items = payload.get("history", [])

    if not session_id or len(session_id) > 200:
        return jsonify({"error": "A valid session_id is required."}), 400
    if not latest_user_message:
        return jsonify({"error": "Message cannot be empty."}), 400
    if len(latest_user_message) > 8000:
        return jsonify({"error": "Message is too long (maximum 8,000 characters)."}), 413
    if not GROQ_API_KEY:
        return jsonify({
            "error": "Groq API key is missing. Open the .env file and set GROQ_API_KEY=your_key, then restart the app. Get a key at https://console.groq.com/"
        }), 503
    if not system_instruction:
        system_instruction = "You are a helpful conversational voice assistant. Keep answers natural and concise."

    messages = [{"role": "system", "content": system_instruction[:12000]}]
    for item in history_items[-20:] if isinstance(history_items, list) else []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        role = "user" if item.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": text[:8000]})

    # Ensure the current user message is present exactly once at the end.
    if not messages or messages[-1]["role"] != "user" or messages[-1]["content"] != latest_user_message:
        messages.append({"role": "user", "content": latest_user_message})

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
            },
            timeout=(10, 90),
        )
        if response.status_code in (401, 403):
            app.logger.warning("Groq authentication failed: %s", response.text[:300])
            return jsonify({"error": "Groq rejected the API key. Check GROQ_API_KEY in your .env file."}), 502
        if response.status_code == 429:
            return jsonify({"error": "Groq rate limit or usage limit reached. Wait a little and try again, or check your Groq console."}), 429
        if response.status_code == 404:
            app.logger.warning("Groq model or endpoint not found: %s", response.text[:300])
            return jsonify({"error": f"The Groq model '{GROQ_MODEL}' was not found or is unavailable. Check the current model names in your Groq console and update GROQ_MODEL in .env."}), 502
        if not response.ok:
            app.logger.warning("Groq returned %s: %s", response.status_code, response.text[:500])
            return jsonify({"error": "Groq could not complete the request. Check your model name, API key, and usage limits."}), 502

        result = response.json()
        choices = result.get("choices", [])
        reply = str(choices[0].get("message", {}).get("content", "")).strip() if choices else ""
        if not reply:
            return jsonify({"error": "Groq returned an empty response. Please try again."}), 502

        now = utc_now()
        with get_db() as db:
            db.execute(
                "INSERT INTO messages (session_id, scenario_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, scenario_id, "user", latest_user_message, now)
            )
            db.execute(
                "INSERT INTO messages (session_id, scenario_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, scenario_id, "model", reply, utc_now())
            )

        return jsonify({"reply": reply, "model": GROQ_MODEL, "provider": "groq"})
    except requests.ConnectTimeout:
        return jsonify({"error": "Connection to Groq timed out. Check your internet connection and try again."}), 504
    except requests.ReadTimeout:
        return jsonify({"error": "Groq took too long to respond. Please try again with a shorter message."}), 504
    except requests.ConnectionError:
        return jsonify({"error": "Could not connect to Groq. Check your internet connection."}), 503
    except requests.RequestException:
        app.logger.exception("Could not connect to Groq API")
        return jsonify({"error": "Could not reach Groq. Check your internet connection and try again."}), 502
    except (ValueError, IndexError, TypeError):
        app.logger.exception("Groq returned an invalid response")
        return jsonify({"error": "Groq returned an invalid response. Please try again."}), 502


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request payload is too large."}), 413


init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
