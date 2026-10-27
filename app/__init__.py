import click
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from .models import db, User, AppSetting

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
csrf = CSRFProtect()
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    @app.context_processor
    def inject_settings():
        settings = {item.key: item.value for item in AppSetting.query.all()}
        return {"settings": settings}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return render_template("login.html")

    @app.route("/")
    def index():
        if User.query.first() is None:
            return render_template("login.html")
        return render_template("login.html")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="The requested page could not be found."), 404

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", message="You do not have permission to access this page."), 403

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("error.html", message="Something went wrong. Please try again."), 500

    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .students import students_bp
    from .verification import verification_bp
    from .intake import intake_bp
    from .reports import reports_bp
    from .audit import audit_bp
    from .settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(intake_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(settings_bp)

    @app.cli.command("init-demo-users")
    def init_demo_users_command():
        if not app.config.get("DEMO_MODE"):
            raise click.ClickException("Demo-user initialization requires DEMO_MODE=true.")

        credentials = [
            ("admin", "admin@demo.local", "ADMIN", app.config.get("DEMO_ADMIN_PASSWORD")),
            ("operator", "operator@demo.local", "INSTITUTION_OPERATOR", app.config.get("DEMO_OPERATOR_PASSWORD")),
        ]
        if any(not password for _, _, _, password in credentials):
            raise click.ClickException(
                "Set DEMO_ADMIN_PASSWORD and DEMO_OPERATOR_PASSWORD before initializing demo accounts."
            )

        created = 0
        preserved = 0
        try:
            for username, email, role, password in credentials:
                email_user = User.query.filter_by(email=email).first()
                username_user = User.query.filter_by(username=username).first()
                if email_user or username_user:
                    if email_user is None or username_user is None or email_user.id != username_user.id:
                        db.session.rollback()
                        raise click.ClickException(
                            f"Cannot initialize {email}: its email or username is already assigned to another account."
                        )
                    preserved += 1
                    continue

                user = User(username=username, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                created += 1

            db.session.commit()
        except SQLAlchemyError as error:
            db.session.rollback()
            app.logger.exception("Demo-user initialization failed.")
            raise click.ClickException(
                "Demo-user initialization failed. Check database connectivity and schema, then retry."
            ) from error

        click.echo(f"Demo-user initialization complete: {created} created, {preserved} existing account(s) preserved.")

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        if User.query.filter_by(role="ADMIN").first():
            raise click.ClickException(
                "An administrator account already exists; bootstrap will not modify existing accounts."
            )

        username = (app.config.get("BOOTSTRAP_ADMIN_USERNAME") or "").strip()
        email = (app.config.get("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
        password = app.config.get("BOOTSTRAP_ADMIN_PASSWORD") or ""
        if not username or not email or not password:
            raise click.ClickException(
                "Set BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_EMAIL, and BOOTSTRAP_ADMIN_PASSWORD before running this command."
            )
        if len(password) < 12:
            raise click.ClickException("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters.")

        existing_account = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_account:
            raise click.ClickException(
                "The configured username or email is already assigned; bootstrap will not modify existing accounts."
            )

        user = User(username=username, email=email, role="ADMIN")
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.error("Administrator bootstrap failed because of a database error.")
            raise click.ClickException(
                "Administrator bootstrap failed. Check database connectivity and schema, then retry."
            ) from None

        click.echo("Administrator account created. Remove the bootstrap credentials from the environment now.")

    @app.cli.command("reset-admin-password")
    def reset_admin_password_command():
        if app.config.get("CONFIRM_ADMIN_PASSWORD_RESET") != "YES":
            raise click.ClickException(
                "Set CONFIRM_ADMIN_PASSWORD_RESET=YES to authorize an administrator password reset."
            )

        target_username = (app.config.get("ADMIN_RESET_USERNAME") or "").strip().lower()
        new_username = (
            app.config.get("ADMIN_RESET_NEW_USERNAME") or target_username
        ).strip()
        password = app.config.get("ADMIN_RESET_PASSWORD") or ""
        if not target_username or not new_username or not password:
            raise click.ClickException(
                "Set ADMIN_RESET_USERNAME, ADMIN_RESET_PASSWORD, and optionally ADMIN_RESET_NEW_USERNAME."
            )
        if len(password) < 12:
            raise click.ClickException("ADMIN_RESET_PASSWORD must be at least 12 characters.")
        if len(new_username) > 120:
            raise click.ClickException("Administrator usernames must be 120 characters or fewer.")

        matching_admins = User.query.filter(
            db.func.lower(User.username) == target_username,
            User.role == "ADMIN",
        ).all()
        if len(matching_admins) != 1:
            raise click.ClickException(
                "The target username must match exactly one existing administrator account."
            )
        admin = matching_admins[0]

        username_collision = User.query.filter(
            db.func.lower(User.username) == new_username.lower(),
            User.id != admin.id,
        ).first()
        if username_collision:
            raise click.ClickException(
                "The requested administrator username is already assigned to another account."
            )

        admin.username = new_username
        admin.set_password(password)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.error("Administrator password reset failed because of a database error.")
            raise click.ClickException(
                "Administrator password reset failed. Check database connectivity and retry."
            ) from None

        click.echo(
            "Administrator credentials updated. Remove the reset variables from the environment now."
        )

    with app.app_context():
        db.create_all()
        ensure_defaults()

    return app


def ensure_defaults():
    default_keys = {
        "institution_name": "AICTE Demo Institution",
        "institution_tagline": "Excellence in student intelligence and compliance",
        "institution_email": "admissions@aictedemo.edu.in",
        "institution_phone": "+91 98765 43210",
        "institution_city": "Bengaluru, Karnataka",
        "academic_year": "2026-27",
        "apaar_rule": r"^[A-Z0-9]{12}$",
        "verification_policy": "APAAR records are reviewed for format consistency, duplicate checks, and academic completeness before approval.",
        "demo_banner": "DEMONSTRATION ENVIRONMENT — FICTIONAL DATA",
    }
    for key, value in default_keys.items():
        if not AppSetting.query.filter_by(key=key).first():
            db.session.add(AppSetting(key=key, value=value))
    db.session.commit()
