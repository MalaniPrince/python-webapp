import hmac
import os
import secrets
import socket
import sqlite3
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from metrics import install_metrics


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATA_DIR=os.environ.get("APP_DATA_DIR", str(Path(__file__).parent / "data")),
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        METRICS_PORT=os.environ.get("APP_METRICS_PORT", "0"),
    )
    if config:
        app.config.update(config)
    directory = Path(app.config["DATA_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    key_path = directory / "session.key"
    try:
        with key_path.open("xb") as key_file:
            key_file.write(secrets.token_bytes(32))
        key_path.chmod(0o600)
    except FileExistsError:
        pass
    app.secret_key = key_path.read_bytes()
    app.config["DATABASE"] = str(directory / "tasks.sqlite3")
    with sqlite3.connect(app.config["DATABASE"], timeout=10) as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
            completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )""")

    install_metrics(app)

    def db():
        if "database" not in g:
            g.database = sqlite3.connect(app.config["DATABASE"], timeout=10)
            g.database.row_factory = sqlite3.Row
        return g.database

    @app.teardown_appcontext
    def close_database(error=None):
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            expected = session.get("csrf", "")
            received = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected.encode(), received.encode()):
                abort(400, description="This form expired. Refresh the page and try again.")

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        selected = request.args.get("filter", "all")
        if selected not in {"all", "active", "done"}:
            selected = "all"
        where = {"all": "", "active": "WHERE completed = 0", "done": "WHERE completed = 1"}[selected]
        tasks = db().execute(f"SELECT * FROM tasks {where} ORDER BY completed, id DESC").fetchall()
        counts = db().execute("SELECT COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done FROM tasks").fetchone()
        return render_template("index.html", tasks=tasks, selected=selected,
            total=counts["total"], done=counts["done"], hostname=socket.gethostname())

    @app.post("/tasks")
    def add_task():
        title = request.form.get("title", "").strip()
        if not 1 <= len(title) <= 160:
            flash("Enter a task between 1 and 160 characters.", "error")
            return redirect(url_for("index"), code=303)
        db().execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        db().commit()
        flash("Task added. One step closer.", "success")
        return redirect(url_for("index"), code=303)

    @app.post("/tasks/<int:task_id>/toggle")
    def toggle_task(task_id):
        cursor = db().execute("UPDATE tasks SET completed = 1 - completed WHERE id = ?", (task_id,))
        if not cursor.rowcount:
            abort(404)
        db().commit()
        return redirect(url_for("index"), code=303)

    @app.post("/tasks/<int:task_id>/delete")
    def delete_task(task_id):
        cursor = db().execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if not cursor.rowcount:
            abort(404)
        db().commit()
        flash("Task deleted.", "success")
        return redirect(url_for("index"), code=303)

    @app.get("/healthz")
    def health():
        db().execute("SELECT 1").fetchone()
        return jsonify(status="ok", database="connected", hostname=socket.gethostname())

    @app.get("/api/tasks")
    def list_tasks():
        tasks = db().execute("SELECT * FROM tasks ORDER BY id").fetchall()
        return jsonify(tasks=[dict(task) for task in tasks])

    return app
