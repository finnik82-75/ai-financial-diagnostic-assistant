"""
Flask-сайт: веб-интерфейс чата для AI Financial Diagnostic Assistant.
API запросов к RAG — отдельный FastAPI-сервис (`backend.app`).
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

app = Flask(__name__)
app.config["FASTAPI_URL"] = os.getenv("FASTAPI_URL", "http://localhost:8000")


@app.route("/")
def index():
    return render_template(
        "index.html",
        api_base=app.config["FASTAPI_URL"],
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
