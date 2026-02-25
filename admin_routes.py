import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from simulation import SEED_REGION_MAPPING, REGION_TO_ROUND_ID
from models import TournamentResult, Bracket
from flask import Blueprint, render_template, redirect, request, flash
from models import db, User


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