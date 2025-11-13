import os

from flask import Flask

from backend.DBsaving import user_setup_bp
from backend.commandLogic import textD
from backend.scheduler import start_scheduler

# app.py
# flask app entry point used to register the blueprint and sets up routes for the api
# this also runs the server and could be extended to include more blueprints if needed

app = Flask(__name__)
app.register_blueprint(user_setup_bp)
app.register_blueprint(textD)

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_scheduler(app)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
