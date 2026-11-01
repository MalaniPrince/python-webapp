# Backend, database, and local development

This is a server-rendered Python application. Requests go to Flask routes in `app.py`; those routes query or update SQLite, then render the Jinja HTML template. The browser forms create, complete, reopen, and delete real database rows.

```text
Browser -> Flask Python routes -> SQLite database
              |
              +-> Jinja template -> HTML response
```

## Where the current Docker database lives

Inside the running `python-webapp-local` container:

```text
/data/tasks.sqlite3
```

It is stored in a Docker named volume. In this laptop's Ubuntu WSL, its backing path is:

```text
/var/lib/docker/volumes/daybook-local-data/_data/tasks.sqlite3
```

From Windows Explorer the corresponding WSL path is:

```text
\\wsl.localhost\Ubuntu\var\lib\docker\volumes\daybook-local-data\_data\tasks.sqlite3
```

Permissions may require root to inspect that volume. Avoid editing or replacing a live SQLite file through Explorer; use SQLite queries or a consistent backup.

The Kubernetes deployment has a separate database at `/data/tasks.sqlite3` inside its application Pod, stored on PVC `python-app/daybook-data`. Docker and Kubernetes are separate running environments with independent data.

## A development database you can see in this project

The development launcher uses this project-local SQLite database:

```text
C:\Users\HP\Desktop\devops\python-webapp\data\tasks.sqlite3
```

This is an independent development database that starts empty. Changes here do not update the Docker or Kubernetes database, and Docker tasks are not synchronized into it. The `data/` folder is excluded from Git, the image build, and the source archive.

## Run the full development application

In Windows PowerShell, from the workspace:

```powershell
cd C:\Users\HP\Desktop\devops\python-webapp
python dev.py
```

Open **http://localhost:8092**. The running development server automatically reloads when Python files change, and debug mode reloads templates. Save a change in `app.py` or the template, then refresh the page. Reload the browser after CSS edits.

If Flask is missing in a fresh Python environment, install it first:

```powershell
python -m pip install Flask==3.1.3
```

This launcher is bound to local loopback for development. The Docker image uses Gunicorn for deployment.

If port 8092 is already serving the development app, reuse it, or stop that process before launching another copy. Ctrl+C stops a foreground development server. You can choose a different port with `python dev.py --port 8093`.

## Read the development database in Python

Run from `python-webapp` in PowerShell:

```powershell
python -c "import sqlite3; db=sqlite3.connect('data/tasks.sqlite3'); print(db.execute('SELECT id, title, completed FROM tasks').fetchall())"
```

You can also open this file using a SQLite database viewer. It is a binary database file, not a text document.

## Main application parts

| File | Responsibility |
|---|---|
| `app.py` | Flask backend, validation, CSRF checks, SQLite operations |
| `templates/index.html` | Server-rendered interface and forms |
| `static/style.css` | Responsive styling |
| `data/tasks.sqlite3` | Local development database |
| `dev.py` | Development server and live reload |
| `Dockerfile` | Deployable Python/Gunicorn image |
| `k8s.yaml` | Deployment, Service, and persistent storage |

The current product is a shared task tracker. It has persistent CRUD operations and health endpoints. User accounts, permissions, and a multi-user PostgreSQL service are separate features that can be added if needed.
