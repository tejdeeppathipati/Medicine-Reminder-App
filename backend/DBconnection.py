from flask import Flask
from DBsaving import user_setup_bp
from flask_cors import CORS

# DBconnection.py
# this is connecting to mongodb for the form function.
# this is set up connecting to localhost for now but can be changed for production

app = Flask(__name__)
CORS(app)  # Enable CORS so frontend can call API
app.register_blueprint(user_setup_bp)

if __name__ == "__main__":
    # debug=True lets you see errors in the terminal
    app.run(host="127.0.0.1", port=5000, debug=True)
