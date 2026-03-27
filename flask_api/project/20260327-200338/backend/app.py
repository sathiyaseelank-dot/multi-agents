import os
from flask import Flask, send_file

app = Flask(__name__)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def hello():
    return send_file(os.path.join(BACKEND_DIR, "hello.txt"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
