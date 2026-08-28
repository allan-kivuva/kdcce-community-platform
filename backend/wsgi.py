import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # debug must never default to True here: Werkzeug's debugger, if ever
    # live in a real deployment, gives remote code execution to anyone who
    # can trigger a 500. Opt in explicitly and only for local dev.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true")
    app.run(debug=debug, port=5000)
