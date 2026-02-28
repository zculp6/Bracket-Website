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
    entry_number = db.Column(db.Integer, nullable=False, default=0)  # 1 or 2 for submitted; 0 for saved drafts
    bracket_name = db.Column(db.String(100), nullable=False, default='My Bracket')
    bracket_data = db.Column(db.JSON, nullable=False)
    score = db.Column(db.Integer, default=0)
    is_submitted = db.Column(db.Boolean, default=False, nullable=False)  # True = locked in for leaderboard

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

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    owner = db.relationship('User', backref='owned_groups', foreign_keys=[owner_id])


class GroupMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    group = db.relationship('Group', backref='memberships')
    user = db.relationship('User', backref='group_memberships')

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='uq_group_user_membership'),
    )


class GroupBracketSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bracket_id = db.Column(db.Integer, db.ForeignKey('bracket.id'), nullable=False)

    group = db.relationship('Group', backref='selections')
    user = db.relationship('User', backref='group_bracket_selections')
    bracket = db.relationship('Bracket', backref='group_selections')

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', 'bracket_id', name='uq_group_user_bracket'),
    )