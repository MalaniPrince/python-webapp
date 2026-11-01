"""Local development server with live reload and project-local SQLite storage."""
import argparse
from pathlib import Path

from app import create_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Daybook for local development")
    parser.add_argument("--port", type=int, default=8092)
    parser.add_argument("--no-reload", action="store_true", help="Disable the reloader for a temporary smoke test")
    arguments = parser.parse_args()
    data_directory = Path(__file__).resolve().parent / "data"
    application = create_app({"DATA_DIR": str(data_directory)})
    print(f"Development database: {application.config['DATABASE']}", flush=True)
    print(f"Open http://127.0.0.1:{arguments.port}", flush=True)
    application.run(host="127.0.0.1", port=arguments.port, debug=True,
                    use_reloader=not arguments.no_reload)
