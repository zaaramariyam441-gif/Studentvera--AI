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
