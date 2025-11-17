import os
from flask import Flask
from flask_cors import CORS
from backend.DBsaving import user_setup_bp
from backend.commandLogic import textD
from backend.scheduler import start_scheduler

# app.py
# flask app entry point used to register the blueprint and sets up routes for the api
# this also runs the server 

app = Flask(__name__)
# CORS for production
CORS(app, origins=[
    "http://localhost:5173",  # Local development
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "*")  # Production frontend URL
])

app.register_blueprint(user_setup_bp)
app.register_blueprint(textD)

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_scheduler(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=False, use_reloader=False)