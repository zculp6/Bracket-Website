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