from flask import Blueprint, render_template, redirect, request, flash
from models import db, User
from flask_bcrypt import Bcrypt
from flask_login import login_user, logout_user

bcrypt = Bcrypt()
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect('/bracket')

        flash("Invalid login.")
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(username=username).first():
            flash("Username already taken.")
            return redirect('/register')

        user = User(username=username, password_hash=password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect('/bracket')

    return render_template('register.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect('/')