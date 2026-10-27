from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from .models import db, User, AuditLog

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = (
            request.form.get("username") or request.form.get("email", "")
        ).strip().lower()
        password = request.form.get("password", "")
        if not identifier or not password:
            current_app.logger.warning(
                "Login rejected (stage=form_fields, reason=missing_required_field)"
            )
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        try:
            identifier_column = User.email if "@" in identifier else User.username
            user = User.query.filter(
                db.func.lower(identifier_column) == identifier
            ).first()
        except SQLAlchemyError as error:
            current_app.logger.error(
                "Login failed (stage=account_lookup, error_type=%s)",
                type(error).__name__,
            )
            raise

        if user is None:
            current_app.logger.warning(
                "Login rejected (stage=account_lookup, reason=no_matching_identifier)"
            )
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        try:
            password_matches = user.check_password(password)
        except (TypeError, ValueError) as error:
            current_app.logger.error(
                "Login failed (stage=password_verification, error_type=%s)",
                type(error).__name__,
            )
            raise

        if password_matches:
            login_user(user)
            db.session.add(AuditLog(event_type="login", description=f"Successful login for {user.email}", user_id=user.id))
            db.session.commit()
            flash("Login successful.", "success")
            return redirect(url_for("dashboard.overview"))
        current_app.logger.warning(
            "Login rejected (stage=password_verification, reason=mismatch)"
        )
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
