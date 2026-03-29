"""Auto-generated Flask application entrypoint.

This file was created by the Project Builder module.
Run with: python app.py
"""

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return {"status": "ok", "message": "Multi-Agent Orchestrator API"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
