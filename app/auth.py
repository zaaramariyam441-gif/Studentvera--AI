from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from .models import db, User, AuditLog

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            db.session.add(AuditLog(event_type="login", description=f"Successful login for {user.email}", user_id=user.id))
            db.session.commit()
            flash("Login successful.", "success")
            return redirect(url_for("dashboard.overview"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    user = current_user
    user_name = getattr(user, 'email', 'unknown')
    user_id = user.get_id()
    logout_user()
    if user_id is not None:
        db.session.add(AuditLog(event_type="logout", description=f"User {user_name} logged out.", user_id=int(user_id)))
        db.session.commit()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
