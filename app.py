import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from simulation import simulate_tournament, chalk_bracket
from simulation import SEED_REGION_MAPPING, REGION_TO_ROUND_ID

# ---------------------------------------
# APP INIT
# ---------------------------------------
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Build the database URL with the correct driver
database_url = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/bracketdb")

# Fix Render's postgres:// prefix
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Tell SQLAlchemy to use psycopg3 driver
if "postgresql://" in database_url and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

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
    # Build the initial teams structure for the bracket
    teams_by_region = {"west": [], "south": [], "east": [], "midwest": []}
    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]

    # Group teams by region
    region_teams = {"West": [], "South": [], "East": [], "Midwest": []}
    for team, (seed, region) in SEED_REGION_MAPPING.items():
        region_teams[region].append({"seed": seed, "name": team})

    # Sort each region by standard bracket order
    for region, teams in region_teams.items():
        key = region.lower()
        teams_by_region[key] = sorted(
            teams, key=lambda t: standard_order.index(t["seed"]) if t["seed"] in standard_order else 99
        )

    return render_template("bracket.html", teams=teams_by_region)

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
    weight   = float(request.json.get("weight", 0.25))  # optional, defaults to 0.25

    if strategy == "chalk":
        bracket = chalk_bracket()

    elif strategy == "simulation":
        # weight: 0 = pure historical seed odds, 1 = pure team strength
        bracket = simulate_tournament(weight=weight)

    elif strategy == "random":
        # Fully random — reuse simulate_tournament with weight=1 and noisy strengths
        bracket = simulate_tournament(weight=1.0)

    else:
        return jsonify({"error": f"Unknown strategy: {strategy}"}), 400

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