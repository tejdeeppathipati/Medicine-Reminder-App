from flask import Flask
from backend.DBsaving import user_setup_bp

# app.py
# flask app entry point used to register the blueprint and sets up routes for the api
# this also runs the server and could be extended to include more blueprints if needed

app = Flask(__name__)
app.register_blueprint(user_setup_bp)

if __name__ == "__main__":
    app.run(debug=True)
