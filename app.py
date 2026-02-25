import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from simulation import simulate_tournament, chalk_bracket, random_bracket, random_probabilistic_bracket, ranking_bracket
from simulation import SEED_REGION_MAPPING, REGION_TO_ROUND_ID
from scoring import score_bracket
from models import TournamentResult, Bracket

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


@app.route("/submit_bracket", methods=["POST"])
@login_required
def submit_bracket():
    data = request.get_json(force=True)
    bracket_data = data.get("bracket")

    if not bracket_data:
        return jsonify({"error": "No bracket data provided"}), 400

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

def _build_true_results() -> dict:
    """Pull all TournamentResult rows and shape them into the same dict format
    as a user bracket: { "west_r32": ["Florida", "St. John's", ...], ... }"""
    results = TournamentResult.query.all()
    shaped = {}
    for r in results:
        if r.round_id not in shaped:
            shaped[r.round_id] = []
        # Extend list to fit slot_index
        while len(shaped[r.round_id]) <= r.slot_index:
            shaped[r.round_id].append(None)
        shaped[r.round_id][r.slot_index] = r.winner_name
    return shaped


def _rescore_all_brackets():
    """Recompute scores for every bracket based on current results."""
    true_results = _build_true_results()
    if not true_results:
        return
    for bracket in Bracket.query.all():
        bracket.score = score_bracket(bracket.bracket_data, true_results)
    db.session.commit()

# ---------------------------------------
# RUN SERVER
# ---------------------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)