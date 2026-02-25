from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Bracket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entry_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    bracket_data = db.Column(db.JSON, nullable=False)
    score = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='brackets')

class TournamentResult(db.Model):
    """Stores each official game winner by round container ID and slot index.
    This mirrors the bracket.js structure exactly:
      round_id   = the .matchups div ID  (e.g. "west_r64", "championship")
      slot_index = which matchup in that container (0-based)
      winner_name = the winning team name string
    """
    id = db.Column(db.Integer, primary_key=True)
    round_id    = db.Column(db.String(30),  nullable=False)
    slot_index  = db.Column(db.Integer,     nullable=False)
    winner_name = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('round_id', 'slot_index', name='uq_round_slot'),
    )