import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from simulation import simulate_tournament, chalk_bracket, random_bracket, random_probabilistic_bracket, ranking_bracket
from simulation import SEED_REGION_MAPPING, REGION_TO_ROUND_ID, TEAMS
from scoring import score_bracket
from models import TournamentResult, Bracket
import pandas as pd

# To reset the database in terminal:
# psql postgresql://bracket_db_jqvw_user:qbJb8ZCDQRNyRg5BLE9BCxG59VfIapvh@dpg-d6f0qho8tnhs73b5vpeg-a.ohio-postgres.render.com/bracket_db_jqvw
# DROP SCHEMA public CASCADE;
# CREATE SCHEMA public;
# GRANT ALL ON SCHEMA public TO bracket_db_jqvw_user;

team_strengths_2025 = pd.read_csv("team_strengths_2025.csv")

try:
    cbb_25 = pd.read_csv("cbb_25.csv")
    rankings_stats = pd.merge(team_strengths_2025, cbb_25, how="left", on="team")
except FileNotFoundError:
    rankings_stats = team_strengths_2025.copy()

# Add a rank column based on strength
rankings_stats = rankings_stats[rankings_stats['team'].isin(TEAMS)].reset_index(drop=True)
rankings_stats = rankings_stats.sort_values('strength', ascending=False).reset_index(drop=True)
rankings_stats['ranking'] = rankings_stats.index + 1

# ---------------------------------------
# APP INIT
# ---------------------------------------
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "alohamora123")
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
# PAGE ROUTES
# ---------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/bracket")
@login_required
def bracket_page():
    standard_order = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]
    regions = ["west", "south", "east", "midwest"]

    region_teams = {r: {} for r in regions}

    for team, (seed, region) in SEED_REGION_MAPPING.items():
        key = region.lower()
        if seed not in region_teams[key]:
            region_teams[key][seed] = {"seed": seed, "name": team}
        else:
            existing = region_teams[key][seed]["name"]
            region_teams[key][seed]["name"] = f"{existing} / {team}"

    teams_by_region = {}
    for region in regions:
        seed_map = region_teams[region]
        ordered = []
        for seed in standard_order:
            if seed in seed_map:
                ordered.append(seed_map[seed])
        teams_by_region[region] = ordered

    return render_template("bracket.html", teams=teams_by_region)

@app.route("/bracket/<int:bracket_id>")
def view_bracket(bracket_id):
    bracket = Bracket.query.get_or_404(bracket_id)
    true_results = _build_true_results()
    return render_template("view_bracket.html", brackets=[bracket], true_results=true_results)


@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/contact")
def contact_page():
    return render_template("contact.html")

@app.route("/leaderboard")
def leaderboard_page():
    brackets = Bracket.query.order_by(Bracket.score.desc()).all()
    return render_template("leaderboard.html", brackets=brackets)

@app.route("/rankings_stats")
def rankings_stats_page():
    # Send the merged data to the frontend
    data_json = rankings_stats.to_dict(orient="records")
    return render_template("ranking_stats.html", data=data_json)


# ---------------------------------------
# API ENDPOINTS
# ---------------------------------------
@app.route("/autofill_bracket", methods=["POST"])
@login_required
def autofill_bracket():
    data     = request.get_json(force=True)
    strategy = data.get("strategy", "simulation")  # single default value only
    weight   = float(data.get("weight", 0.25))

    try:
        if strategy == "chalk":
            bracket = chalk_bracket()
        elif strategy == "random":
            bracket = random_bracket()
        elif strategy == "probabilistic (by seed)":
            bracket = random_probabilistic_bracket()
        elif strategy == "by ranking":
            bracket = ranking_bracket()
        else:
            # "simulation" or anything unrecognised
            bracket = simulate_tournament(weight=weight)
    except Exception as e:
        print("Autofill error:", e)
        return jsonify({"error": str(e)}), 500

    return jsonify(bracket)

# -------------------------------------------------------
# ADMIN HELPER: verify secret
# -------------------------------------------------------
def _check_admin(request):
    secret = request.headers.get("X-Admin-Secret", "")
    return secret == os.environ.get("ADMIN_SECRET", "alohamora123")


# -------------------------------------------------------
# ADMIN HELPER: build true results dict from DB
# -------------------------------------------------------
def _build_true_results():
    """
    Returns { "west_r64": ["Florida", "Auburn", ...], ... }
    indexed by slot, matching the bracket.js container IDs.
    """
    results = TournamentResult.query.all()
    shaped = {}
    for r in results:
        if r.round_id not in shaped:
            shaped[r.round_id] = []
        while len(shaped[r.round_id]) <= r.slot_index:
            shaped[r.round_id].append(None)
        shaped[r.round_id][r.slot_index] = r.winner_name
    return shaped


# -------------------------------------------------------
# ADMIN HELPER: rescore every bracket
# -------------------------------------------------------
def _rescore_all_brackets():
    from scoring import score_bracket
    true_results = _build_true_results()
    if not true_results:
        return 0, 0
    brackets = Bracket.query.all()
    top = 0
    for b in brackets:
        b.score = score_bracket(b.bracket_data, true_results)
        if b.score > top:
            top = b.score
    db.session.commit()
    return len(brackets), top


# -------------------------------------------------------
# ADMIN PAGE
# -------------------------------------------------------
@app.route("/admin")
@login_required
def admin_page():
    # Build a flat list of all teams with seeds for the autocomplete
    teams_json = []
    seen = set()
    for team, (seed, region) in SEED_REGION_MAPPING.items():
        if team not in seen:
            teams_json.append({"name": team, "seed": seed, "region": region})
            seen.add(team)
    teams_json.sort(key=lambda t: (t["seed"], t["name"]))
    return render_template("admin.html", teams_json=teams_json)


# -------------------------------------------------------
# ADMIN: SAVE A SINGLE GAME RESULT
# -------------------------------------------------------
@app.route("/admin/set_result", methods=["POST"])
@login_required
def set_result():
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized — wrong admin secret."}), 403

    data        = request.get_json(force=True)
    round_id    = data.get("round_id", "").strip()
    slot_index  = data.get("slot_index")
    winner_name = data.get("winner_name", "").strip()

    if not round_id or slot_index is None or not winner_name:
        return jsonify({"error": "round_id, slot_index, and winner_name are required."}), 400

    # Upsert
    existing = TournamentResult.query.filter_by(
        round_id=round_id, slot_index=int(slot_index)
    ).first()

    if existing:
        existing.winner_name = winner_name
    else:
        db.session.add(TournamentResult(
            round_id=round_id,
            slot_index=int(slot_index),
            winner_name=winner_name
        ))

    db.session.commit()

    # Rescore immediately
    brackets_scored, top_score = _rescore_all_brackets()

    return jsonify({
        "message": f"{winner_name} saved. {brackets_scored} bracket(s) rescored.",
        "brackets_scored": brackets_scored,
        "top_score": top_score
    })


# -------------------------------------------------------
# ADMIN: MANUAL RESCORE TRIGGER
# -------------------------------------------------------
@app.route("/admin/rescore", methods=["POST"])
@login_required
def rescore():
    if not _check_admin(request):
        return jsonify({"error": "Unauthorized — wrong admin secret."}), 403

    brackets_scored, top_score = _rescore_all_brackets()
    return jsonify({
        "message": f"{brackets_scored} bracket(s) rescored.",
        "brackets_scored": brackets_scored,
        "top_score": top_score
    })


# -------------------------------------------------------
# ADMIN: GET ALL LOGGED RESULTS (to populate the UI on load)
# -------------------------------------------------------
@app.route("/admin/get_results")
@login_required
def get_results():
    results = TournamentResult.query.all()
    brackets = Bracket.query.all()
    top = max((b.score for b in brackets), default=0)
    return jsonify({
        "results": [
            {
                "round_id":    r.round_id,
                "slot_index":  r.slot_index,
                "winner_name": r.winner_name
            }
            for r in results
        ],
        "brackets_scored": len(brackets),
        "top_score": top
    })


@app.route("/save_bracket", methods=["POST"])
@login_required
def save_bracket():
    """Save a draft bracket (not submitted to leaderboard). Up to 25 total brackets per user."""
    data = request.get_json(force=True)
    bracket_data = data.get("bracket")
    bracket_name = (data.get("bracket_name") or "My Bracket").strip()

    if len(bracket_name) > 50:
        return jsonify({"error": "Bracket name must be 50 characters or fewer"}), 400

    if not bracket_data:
        return jsonify({"error": "No bracket data provided"}), 400

    total = Bracket.query.filter_by(user_id=current_user.id).count()
    if total >= 25:
        return jsonify({"error": "You have reached the maximum of 25 saved brackets."}), 400

    new_bracket = Bracket(
        user_id=current_user.id,
        entry_number=0,           # 0 = draft/saved, not on leaderboard
        bracket_name=bracket_name,
        bracket_data=bracket_data,
        is_submitted=False
    )
    db.session.add(new_bracket)
    db.session.commit()

    return jsonify({"message": "Bracket saved!", "bracket_id": new_bracket.id})


@app.route("/submit_bracket", methods=["POST"])
@login_required
def submit_bracket():
    """
    Lock a bracket into the leaderboard. Max 2 submitted per user.
    Can submit an existing saved bracket by passing bracket_id,
    or create a new one from scratch.
    """
    data = request.get_json(force=True)
    bracket_data = data.get("bracket")
    bracket_name = (data.get("bracket_name") or "My Bracket").strip()
    bracket_id   = data.get("bracket_id")   # optional: submit an existing saved bracket

    if len(bracket_name) > 50:
        return jsonify({"error": "Bracket name must be 50 characters or fewer"}), 400

    # Count how many are already submitted
    submitted_count = Bracket.query.filter_by(
        user_id=current_user.id, is_submitted=True
    ).count()

    if submitted_count >= 2:
        return jsonify({"error": "You have already submitted 2 brackets. That's the maximum."}), 400

    entry_number = submitted_count + 1  # will be 1 or 2

    if bracket_id:
        # Promote an existing saved bracket to submitted
        b = Bracket.query.filter_by(id=bracket_id, user_id=current_user.id).first()
        if not b:
            return jsonify({"error": "Bracket not found."}), 404
        if b.is_submitted:
            return jsonify({"error": "This bracket is already submitted."}), 400
        b.is_submitted  = True
        b.entry_number  = entry_number
        b.bracket_name  = bracket_name
        db.session.commit()
    else:
        # Create a brand-new submitted bracket
        if not bracket_data:
            return jsonify({"error": "No bracket data provided"}), 400

        total = Bracket.query.filter_by(user_id=current_user.id).count()
        if total >= 25:
            return jsonify({"error": "You have reached the maximum of 25 saved brackets."}), 400

        b = Bracket(
            user_id=current_user.id,
            entry_number=entry_number,
            bracket_name=bracket_name,
            bracket_data=bracket_data,
            is_submitted=True
        )
        db.session.add(b)
        db.session.commit()

    # Rescore immediately so submitted bracket gets a score
    _rescore_all_brackets()

    return jsonify({"message": "Bracket submitted!", "bracket_id": b.id})


@app.route("/my_brackets")
@login_required
def my_brackets_page():
    all_brackets = (Bracket.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Bracket.is_submitted.desc(), Bracket.entry_number, Bracket.id)
                    .all())
    submitted = [b for b in all_brackets if b.is_submitted]
    saved     = [b for b in all_brackets if not b.is_submitted]
    true_results = _build_true_results()
    return render_template(
        "my_brackets.html",
        submitted=submitted,
        saved=saved,
        brackets=submitted,      # kept for backward compat with view rendering
        true_results=true_results
    )

@app.route("/delete_bracket", methods=["POST"])
@login_required
def delete_bracket():
    """Delete a saved (non-submitted) bracket."""
    data = request.get_json(force=True)
    bracket_id = data.get("bracket_id")

    if not bracket_id:
        return jsonify({"error": "bracket_id required"}), 400

    b = Bracket.query.filter_by(id=bracket_id, user_id=current_user.id).first()
    if not b:
        return jsonify({"error": "Bracket not found."}), 404

    if b.is_submitted:
        return jsonify({"error": "Submitted brackets cannot be deleted."}), 400

    db.session.delete(b)
    db.session.commit()
    return jsonify({"message": "Bracket deleted."})
# ---------------------------------------
# RUN SERVER
# ---------------------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)