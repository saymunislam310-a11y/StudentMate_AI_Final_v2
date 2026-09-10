import os
import sqlite3
from functools import wraps
from datetime import datetime
import base64
import mimetypes
import io
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "studentmate.db")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "studentmate-ai-secret-key-change-later"
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    db = get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            class_name TEXT DEFAULT '',
            school TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            exam_name TEXT DEFAULT '',
            exam_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT DEFAULT '',
            minutes INTEGER DEFAULT 0,
            study_date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS ai_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL,
            image_data TEXT DEFAULT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
        );
    """)

    db.commit()
    db.close()


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)

    return wrapper


# =========================================================
# USER
# =========================================================

def current_user():
    if "user_id" not in session:
        return None

    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    db.close()

    return user


# =========================================================
# INDEX
# =========================================================

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("home"))

    return render_template("index.html")


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash(
                "Password must be at least 6 characters.",
                "error"
            )
            return render_template("signup.html")

        db = get_db()

        existing_user = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            db.close()
            flash(
                "An account with this email already exists.",
                "error"
            )
            return render_template("signup.html")

        password_hash = generate_password_hash(password)

        cursor = db.execute(
            """
            INSERT INTO users
            (name, email, password, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                password_hash,
                datetime.now().isoformat()
            )
        )

        db.commit()

        user_id = cursor.lastrowid

        db.close()

        session["user_id"] = user_id
        session["user_name"] = name

        flash("Welcome to StudentMate AI!", "success")

        return redirect(url_for("home"))

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            flash("Login successful.", "success")

            return redirect(url_for("home"))

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# =========================================================
# HOME
# =========================================================

@app.route("/home")
@login_required
def home():

    user = current_user()

    db = get_db()

    tasks_total = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    tasks_completed = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
        AND completed = 1
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    notes_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM notes
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    exams_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM exams
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    recent_tasks = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (session["user_id"],)
    ).fetchall()

    upcoming_exams = db.execute(
        """
        SELECT *
        FROM exams
        WHERE user_id = ?
        ORDER BY exam_date ASC
        LIMIT 3
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "home.html",
        user=user,
        tasks_total=tasks_total,
        tasks_completed=tasks_completed,
        notes_count=notes_count,
        exams_count=exams_count,
        recent_tasks=recent_tasks,
        upcoming_exams=upcoming_exams
    )


# =========================================================
# STUDY
# =========================================================

@app.route("/study")
@login_required
def study():

    db = get_db()

    sessions = db.execute(
        """
        SELECT *
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "study.html",
        sessions=sessions
    )


@app.route("/study/add", methods=["POST"])
@login_required
def add_study_session():

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    minutes = request.form.get(
        "minutes",
        "0"
    ).strip()

    try:
        minutes = int(minutes)
    except ValueError:
        minutes = 0

    if minutes > 0:

        db = get_db()

        db.execute(
            """
            INSERT INTO study_sessions
            (user_id, subject, minutes, study_date)
            VALUES (?, ?, ?, ?)
            """,
            (
                session["user_id"],
                subject,
                minutes,
                datetime.now().strftime("%Y-%m-%d")
            )
        )

        db.commit()
        db.close()

        flash(
            "Study session added.",
            "success"
        )

    return redirect(url_for("study"))


# =========================================================
# TASKS
# =========================================================

@app.route("/tasks")
@login_required
def tasks():

    db = get_db()

    tasks_list = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id = ?
        ORDER BY completed ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "tasks.html",
        tasks=tasks_list
    )


@app.route("/tasks/add", methods=["POST"])
@login_required
def add_task():

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    due_date = request.form.get(
        "due_date",
        ""
    ).strip()

    if title:

        db = get_db()

        db.execute(
            """
            INSERT INTO tasks
            (user_id, title, description, due_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                description,
                due_date,
                datetime.now().isoformat()
            )
        )

        db.commit()
        db.close()

        flash(
            "Task added.",
            "success"
        )

    return redirect(url_for("tasks"))


@app.route("/tasks/<int:task_id>/toggle")
@login_required
def toggle_task(task_id):

    db = get_db()

    task = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    ).fetchone()

    if task:

        new_status = 0 if task["completed"] else 1

        db.execute(
            """
            UPDATE tasks
            SET completed = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                new_status,
                task_id,
                session["user_id"]
            )
        )

        db.commit()

    db.close()

    return redirect(url_for("tasks"))


@app.route("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id):

    db = get_db()

    db.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    )

    db.commit()
    db.close()

    return redirect(url_for("tasks"))


# =========================================================
# NOTES
# =========================================================

@app.route("/notes")
@login_required
def notes():

    db = get_db()

    notes_list = db.execute(
        """
        SELECT *
        FROM notes
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "notes.html",
        notes=notes_list
    )


@app.route("/notes/add", methods=["POST"])
@login_required
def add_note():

    title = request.form.get(
        "title",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if title:

        db = get_db()

        db.execute(
            """
            INSERT INTO notes
            (user_id, title, content, subject, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                content,
                subject,
                datetime.now().isoformat()
            )
        )

        db.commit()
        db.close()

        flash(
            "Note saved.",
            "success"
        )

    return redirect(url_for("notes"))


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id=? AND user_id=?", (note_id, session["user_id"])).fetchone()
    if not note:
        db.close()
        return redirect(url_for("notes"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        content = request.form.get("content", "").strip()
        if title:
            db.execute("UPDATE notes SET title=?, subject=?, content=? WHERE id=? AND user_id=?",
                       (title, subject, content, note_id, session["user_id"]))
            db.commit()
            db.close()
            flash("Note updated.", "success")
            return redirect(url_for("notes"))
    db.close()
    return render_template("edit_note.html", note=note)


@app.route("/notes/<int:note_id>/delete")
@login_required
def delete_note(note_id):

    db = get_db()

    db.execute(
        """
        DELETE FROM notes
        WHERE id = ?
        AND user_id = ?
        """,
        (
            note_id,
            session["user_id"]
        )
    )

    db.commit()
    db.close()

    return redirect(url_for("notes"))


# =========================================================
# ROUTINE
# =========================================================

@app.route("/routine")
@login_required
def routine():

    db = get_db()

    routines = db.execute(
        """
        SELECT *
        FROM routines
        WHERE user_id = ?
        ORDER BY
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            start_time
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "routine.html",
        routines=routines
    )


@app.route("/routine/add", methods=["POST"])
@login_required
def add_routine():

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    day = request.form.get(
        "day",
        ""
    ).strip()

    start_time = request.form.get(
        "start_time",
        ""
    ).strip()

    end_time = request.form.get(
        "end_time",
        ""
    ).strip()

    if subject and day and start_time and end_time:

        db = get_db()

        db.execute(
            """
            INSERT INTO routines
            (user_id, subject, day, start_time, end_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                subject,
                day,
                start_time,
                end_time,
                datetime.now().isoformat()
            )
        )

        db.commit()
        db.close()

        flash(
            "Routine added.",
            "success"
        )

    return redirect(url_for("routine"))


# =========================================================
# EXAMS
# =========================================================

@app.route("/exams")
@login_required
def exams():

    db = get_db()

    exams_list = db.execute(
        """
        SELECT *
        FROM exams
        WHERE user_id = ?
        ORDER BY exam_date ASC
        """,
        (session["user_id"],)
    ).fetchall()

    db.close()

    return render_template(
        "exams.html",
        exams=exams_list
    )


@app.route("/exams/add", methods=["POST"])
@login_required
def add_exam():

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    exam_name = request.form.get(
        "exam_name",
        ""
    ).strip()

    exam_date = request.form.get(
        "exam_date",
        ""
    ).strip()

    if subject and exam_date:

        db = get_db()

        db.execute(
            """
            INSERT INTO exams
            (user_id, subject, exam_name, exam_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                subject,
                exam_name,
                exam_date,
                datetime.now().isoformat()
            )
        )

        db.commit()
        db.close()

        flash(
            "Exam added.",
            "success"
        )

    return redirect(url_for("exams"))


@app.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exam(exam_id):
    db = get_db()
    exam = db.execute("SELECT * FROM exams WHERE id=? AND user_id=?", (exam_id, session["user_id"])).fetchone()
    if not exam:
        db.close()
        return redirect(url_for("exams"))
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        exam_name = request.form.get("exam_name", "").strip()
        exam_date = request.form.get("exam_date", "").strip()
        if subject and exam_date:
            db.execute("UPDATE exams SET subject=?, exam_name=?, exam_date=? WHERE id=? AND user_id=?",
                       (subject, exam_name, exam_date, exam_id, session["user_id"]))
            db.commit()
            db.close()
            flash("Exam updated.", "success")
            return redirect(url_for("exams"))
    db.close()
    return render_template("edit_exam.html", exam=exam)


@app.route("/exams/<int:exam_id>/delete")
@login_required
def delete_exam(exam_id):
    db = get_db()
    db.execute("DELETE FROM exams WHERE id=? AND user_id=?", (exam_id, session["user_id"]))
    db.commit()
    db.close()
    flash("Exam deleted.", "success")
    return redirect(url_for("exams"))


# =========================================================
# AI HELPER
# =========================================================

AI_SYSTEM_PROMPT = """
You are StudentMate AI, a friendly general-purpose AI assistant built for students.
You are not limited to school questions. Help with study, math, science, coding,
writing, translation, planning, brainstorming, explanations, everyday problems,
and general knowledge.

Language rules:
- Reply in the same language as the user whenever practical.
- If the user writes Bangla, reply in natural Bangla using Unicode Bangla script.
- If the user mixes Bangla and English, understand the mix and reply naturally,
  usually in the dominant language.
- Never answer Bangla questions using Bangla written only in Latin/roman letters
  unless the user explicitly asks for Roman Bangla.

Style:
- Be warm, clear and useful.
- Explain difficult things step by step.
- For schoolwork, teach rather than simply giving unexplained answers.
- Use headings, bullets and numbered steps when useful.
- For code, provide complete, runnable examples when appropriate.
- If information is uncertain or current, say so rather than inventing facts.
- Do not claim to have performed an action you cannot actually perform.
"""

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)

def clean_history(history):
    if not isinstance(history, list):
        return []
    cleaned = []
    for item in history[-20:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content[:12000]})
    return cleaned

def make_data_url(image_data, image_type="image/jpeg"):
    if not isinstance(image_data, str):
        return None
    if image_data.startswith("data:image/"):
        return image_data
    # Accept a raw base64 payload from the browser as well.
    try:
        base64.b64decode(image_data, validate=True)
        return f"data:{image_type};base64,{image_data}"
    except Exception:
        return None

@app.route("/ai-helper")
@login_required
def ai_helper():
    return render_template("ai_helper.html")

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def history_to_gemini_contents(history):
    contents = []
    for item in history:
        role = "user" if item["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": item["content"]}]
        })
    return contents


def ask_gemini(message, history, image_data=None, image_type="image/jpeg"):
    client = get_gemini_client()
    if client is None or genai_types is None:
        raise RuntimeError("Gemini is not configured.")

    model = os.environ.get(
        "GEMINI_AI_MODEL",
        "gemini-3.7-flash"
    ).strip()

    contents = history_to_gemini_contents(history)
    parts = []
    if message:
        parts.append(genai_types.Part.from_text(text=message))

    if image_data:
        image_url = make_data_url(image_data, image_type)
        if image_url and "," in image_url:
            try:
                encoded = image_url.split(",", 1)[1]
                raw = base64.b64decode(encoded)
                parts.append(
                    genai_types.Part.from_bytes(
                        data=raw,
                        mime_type=image_type or "image/jpeg"
                    )
                )
            except Exception as exc:
                raise RuntimeError("The selected image could not be decoded.") from exc

    if not parts:
        raise RuntimeError("No user content supplied.")

    contents.append(genai_types.Content(role="user", parts=parts))

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=AI_SYSTEM_PROMPT,
            max_output_tokens=4000,
            temperature=0.7
        )
    )

    reply = (getattr(response, "text", None) or "").strip()
    if not reply:
        raise RuntimeError("Gemini returned an empty response.")
    return reply


def ask_openai(message, history, image_data=None, image_type="image/jpeg"):
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI is not configured.")

    user_content = []
    if message:
        user_content.append({
            "type": "input_text",
            "text": message
        })

    if image_data:
        image_url = make_data_url(image_data, image_type)
        if image_url:
            user_content.append({
                "type": "input_image",
                "image_url": image_url,
                "detail": "auto"
            })

    input_items = []
    for item in history:
        input_items.append({
            "role": item["role"],
            "content": item["content"]
        })

    input_items.append({
        "role": "user",
        "content": (
            user_content if len(user_content) > 1
            else (
                user_content[0]["text"]
                if user_content and user_content[0]["type"] == "input_text"
                else user_content
            )
        )
    })

    model = os.environ.get(
        "STUDENTMATE_AI_MODEL",
        "gpt-5.6-luna"
    ).strip()

    response = client.responses.create(
        model=model,
        instructions=AI_SYSTEM_PROMPT,
        input=input_items,
        max_output_tokens=4000,
        timeout=60.0
    )

    reply = (response.output_text or "").strip()
    if not reply:
        raise RuntimeError("OpenAI returned an empty response.")
    return reply


def _conversation_belongs_to_user(db, conversation_id):
    return db.execute("SELECT * FROM ai_conversations WHERE id = ? AND user_id = ?", (conversation_id, session["user_id"])).fetchone()

@app.route("/api/ai/chats", methods=["GET"])
@login_required
def ai_chats():
    db=get_db(); rows=db.execute("""SELECT c.id,c.title,c.created_at,c.updated_at,COUNT(m.id) AS message_count FROM ai_conversations c LEFT JOIN ai_messages m ON m.conversation_id=c.id WHERE c.user_id=? GROUP BY c.id ORDER BY c.updated_at DESC,c.id DESC""",(session["user_id"],)).fetchall(); db.close()
    return jsonify({"chats":[dict(r) for r in rows]})

@app.route("/api/ai/chats/<int:conversation_id>", methods=["GET"])
@login_required
def ai_chat_get(conversation_id):
    db=get_db(); convo=_conversation_belongs_to_user(db,conversation_id)
    if not convo: db.close(); return jsonify({"error":"Conversation not found."}),404
    msgs=db.execute("SELECT role,content,image_data,created_at FROM ai_messages WHERE conversation_id=? ORDER BY id ASC",(conversation_id,)).fetchall(); db.close()
    return jsonify({"chat":{"id":convo["id"],"title":convo["title"],"created_at":convo["created_at"],"updated_at":convo["updated_at"],"messages":[dict(m) for m in msgs]}})

@app.route("/api/ai/chats", methods=["POST"])
@login_required
def ai_chat_save():
    data=request.get_json(silent=True) or {}; cid=data.get("id"); messages=data.get("messages") or []
    if not isinstance(messages,list): return jsonify({"error":"Invalid messages."}),400
    cleaned=[]
    for m in messages[-100:]:
        if not isinstance(m,dict): continue
        role=m.get("role"); content=str(m.get("content","")).strip()
        if role not in ("user","assistant") or not content: continue
        image=m.get("image") if isinstance(m.get("image"),str) and len(m.get("image"))<=300000 else None
        cleaned.append({"role":role,"content":content[:20000],"image_data":image})
    if not cleaned: return jsonify({"error":"Nothing to save."}),400
    title=" ".join(next((m["content"] for m in cleaned if m["role"]=="user"),"New chat").split())[:80] or "New chat"; now=datetime.now().isoformat(); db=get_db()
    try:
        if cid:
            convo=_conversation_belongs_to_user(db,int(cid))
            if not convo: return jsonify({"error":"Conversation not found."}),404
            cid=convo["id"]; db.execute("DELETE FROM ai_messages WHERE conversation_id=?",(cid,)); db.execute("UPDATE ai_conversations SET title=?,updated_at=? WHERE id=? AND user_id=?",(title,now,cid,session["user_id"]))
        else:
            cid=db.execute("INSERT INTO ai_conversations(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",(session["user_id"],title,now,now)).lastrowid
        db.executemany("INSERT INTO ai_messages(conversation_id,role,content,image_data,created_at) VALUES(?,?,?,?,?)",[(cid,m["role"],m["content"],m["image_data"],now) for m in cleaned]); db.commit(); return jsonify({"id":cid,"title":title,"updated_at":now})
    finally: db.close()

@app.route("/api/ai/chats/<int:conversation_id>", methods=["DELETE"])
@login_required
def ai_chat_delete(conversation_id):
    db=get_db(); convo=_conversation_belongs_to_user(db,conversation_id)
    if not convo: db.close(); return jsonify({"error":"Conversation not found."}),404
    db.execute("DELETE FROM ai_messages WHERE conversation_id=?",(conversation_id,)); db.execute("DELETE FROM ai_conversations WHERE id=? AND user_id=?",(conversation_id,session["user_id"])); db.commit(); db.close(); return jsonify({"ok":True})

@app.route("/api/ai", methods=["POST"])
@login_required
def ai_api():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = clean_history(data.get("history", []))
    image_data = data.get("image")
    image_type = data.get("image_type") or "image/jpeg"
    if not isinstance(image_type, str) or not image_type.startswith("image/"):
        image_type = "image/jpeg"

    if not message and not image_data:
        return jsonify({
            "reply": "Please type a question or attach an image first."
        }), 400

    # PRIMARY: Gemini.
    # This avoids waiting for the user's OpenAI quota failure.
    try:
        reply = ask_gemini(
            message,
            history,
            image_data=image_data,
            image_type=image_type
        )
        return jsonify({
            "reply": reply,
            "provider": "gemini"
        })
    except Exception as gemini_exc:
        app.logger.warning(
            "Gemini primary request failed: %s",
            gemini_exc
        )

    # BACKUP: OpenAI.
    gemini_exc = None
    try:
        reply = ask_openai(
            message,
            history,
            image_data=image_data,
            image_type=image_type
        )
        return jsonify({
            "reply": reply,
            "provider": "openai"
        })
    except Exception as openai_exc:
        app.logger.exception(
            "Both StudentMate AI providers failed. "
            "Gemini=%r OpenAI=%r",
            gemini_exc,
            openai_exc
        )

        if app.debug:
            return jsonify({
                "reply": "Both AI services are unavailable right now.",
                "error": {
                    "gemini": str(gemini_exc),
                    "openai": str(openai_exc)
                }
            }), 502

        return jsonify({
            "reply": "Both AI services are unavailable right now. Please try again in a moment."
        }), 502


@app.route("/api/ai/image", methods=["POST"])
@login_required
def ai_image():
    """
    Generate an image from a prompt. This endpoint is intentionally separate
    from normal chat so the app can add image tools without making every
    conversation an image request.
    """
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "Please describe the image you want."}), 400

    client = get_openai_client()
    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is not configured."}), 503

    try:
        result = client.images.generate(
            model=os.environ.get("STUDENTMATE_IMAGE_MODEL", "gpt-image-2"),
            prompt=prompt
        )
        image_b64 = result.data[0].b64_json
        return jsonify({
            "image": f"data:image/png;base64,{image_b64}"
        })

    except Exception:
        app.logger.exception("Image generation failed")
        return jsonify({
            "error": "Image generation is unavailable right now. Check your API/model access."
        }), 502

@app.route("/api/ai/image-edit", methods=["POST"])
@login_required
def ai_image_edit():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    image_data = data.get("image")

    if not prompt or not image_data:
        return jsonify({"error": "Please attach an image and describe the edit you want."}), 400

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not configured."}), 503

    try:
        if image_data.startswith("data:"):
            header, encoded = image_data.split(",", 1)
            mime = header.split(";")[0].split(":", 1)[1]
        else:
            encoded = image_data
            mime = data.get("image_type", "image/png")

        raw = base64.b64decode(encoded)
        ext = mimetypes.guess_extension(mime) or ".png"

        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"image": (f"studentmate{ext}", io.BytesIO(raw), mime)},
            data={
                "model": os.environ.get("STUDENTMATE_IMAGE_MODEL", "gpt-image-2"),
                "prompt": prompt
            },
            timeout=180
        )
        response.raise_for_status()
        payload = response.json()
        image_b64 = payload["data"][0]["b64_json"]

        return jsonify({"image": f"data:image/png;base64,{image_b64}"})

    except Exception:
        app.logger.exception("Image editing failed")
        return jsonify({
            "error": "Image editing failed. Check your image-model access and API settings."
        }), 502

# =========================================================
# SCIENTIFIC CALCULATOR
# =========================================================

@app.route("/calculator")
@login_required
def calculator():
    return render_template("calculator.html")


# =========================================================
# PROGRESS
# =========================================================

@app.route("/progress")
@login_required
def progress():

    db = get_db()

    total_minutes = db.execute(
        """
        SELECT COALESCE(SUM(minutes), 0) AS total
        FROM study_sessions
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    completed_tasks = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
        AND completed = 1
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    total_tasks = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["total"]

    db.close()

    task_percentage = 0

    if total_tasks:
        task_percentage = round(
            (completed_tasks / total_tasks) * 100
        )

    return render_template(
        "progress.html",
        total_minutes=total_minutes,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        task_percentage=task_percentage
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        ).strip()

        school = request.form.get(
            "school",
            ""
        ).strip()

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        if name:

            db = get_db()

            db.execute(
                """
                UPDATE users
                SET name = ?,
                    class_name = ?,
                    school = ?,
                    bio = ?
                WHERE id = ?
                """,
                (
                    name,
                    class_name,
                    school,
                    bio,
                    session["user_id"]
                )
            )

            db.commit()
            db.close()

            session["user_name"] = name

            flash(
                "Profile updated.",
                "success"
            )

        return redirect(url_for("profile"))

    user = current_user()

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route("/settings")
@login_required
def settings():

    user = current_user()

    return render_template(
        "settings.html",
        user=user
    )


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return """
    <h1>404</h1>
    <p>Page not found.</p>
    <a href="/">Go Home</a>
    """, 404


# =========================================================
# START
# =========================================================

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
