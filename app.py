import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt

# ---------------------------------------
# APP INIT
# ---------------------------------------
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/bracketdb")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Railway sets DATABASE_URL with "postgres://" prefix; SQLAlchemy needs "postgresql://"
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

# ---------------------------------------
# EXTENSIONS
# ---------------------------------------
from models import db, User, Bracket

db.init_app(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------
# BLUEPRINTS
# ---------------------------------------
from auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

# ---------------------------------------
# DB INIT (creates tables on first deploy)
# ---------------------------------------
with app.app_context():
    db.create_all()

# ---------------------------------------
# SIMULATION LOGIC (placeholder)
# ---------------------------------------
def simulate_tournament(strategy):
    # TODO: Replace with real seeding + simulation logic
    return {
        "round_1": ["Team A", "Team B", "Team C", "Team D"]
    }

# ---------------------------------------
# PAGE ROUTES
# ---------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/bracket")
@login_required
def bracket_page():
    return render_template("bracket.html")

@app.route("/leaderboard")
def leaderboard_page():
    brackets = Bracket.query.order_by(Bracket.score.desc()).all()
    return render_template("leaderboard.html", brackets=brackets)

# ---------------------------------------
# API ENDPOINTS
# ---------------------------------------
@app.route("/autofill_bracket", methods=["POST"])
@login_required
def autofill_bracket():
    strategy = request.json.get("strategy")
    bracket = simulate_tournament(strategy)
    return jsonify(bracket)

@app.route("/submit_bracket", methods=["POST"])
@login_required
def submit_bracket():
    data = request.json
    bracket_data = data.get("bracket")

    if not bracket_data:
        return jsonify({"error": "No bracket data provided"}), 400

    # Enforce max 2 entries per user
    existing = Bracket.query.filter_by(user_id=current_user.id).count()
    if existing >= 2:
        return jsonify({"error": "You have already submitted 2 brackets."}), 400

    new_bracket = Bracket(
        user_id=current_user.id,
        entry_number=existing + 1,
        bracket_data=bracket_data
    )

    db.session.add(new_bracket)
    db.session.commit()

    return jsonify({"message": "Bracket submitted successfully!"})

# ---------------------------------------
# RUN SERVER
# ---------------------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)