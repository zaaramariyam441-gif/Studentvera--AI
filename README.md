# STUDENTVERA AI

Less spreadsheet archaeology. Fewer duplicate records. More intelligent verification. Because academic administration deserves better plotlines. | SIH 2026.

STUDENTVERA AI is a prototype for APAAR ID-based student data management and verification for AICTE-approved institutions.

## Important disclaimer

This project is a prototype for demonstration and local testing only. It is not an official APAAR verification system and does not connect to government or institutional identity services. Use fictional data only.

## Tech stack

- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- PostgreSQL for deployed environments
- SQLite fallback for local development only
- Gunicorn for Linux production hosting

## Local setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set a local `SECRET_KEY`. Leave `APP_ENV=development`.
4. For local PostgreSQL, set:
   ```env
   DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/studentvera
   ```
   Create the database if needed with `createdb studentvera`. For local SQLite, omit `DATABASE_URL` or set `DATABASE_URL=sqlite:///studentvera_dev.db`.
5. Start the development server:
   ```bash
   python run.py
   ```
   Open http://127.0.0.1:5000/login.

## Render deployment

Set these Render environment variables:

- `APP_ENV=production`
- `SECRET_KEY` to a long, random value. Never commit the real value.
- `DATABASE_URL` to the Render PostgreSQL database's internal connection URL.
- `DEMO_MODE=true` only if this is an isolated, public demonstration instance.
- `DEMO_ADMIN_PASSWORD` and `DEMO_OPERATOR_PASSWORD` only for that isolated demo. Use the public demo passwords shown on the login screen, and never enable them on an instance containing real student records.

The app handles Render's `postgres://` and `postgresql://` URL schemes using psycopg 3. In production, startup fails clearly if `DATABASE_URL` or a non-default `SECRET_KEY` is missing instead of silently falling back to SQLite.

Use this Render start command:

```bash
gunicorn run:app
```

`run.py` exports the Flask application as `app`. Gunicorn is not supported on Windows; use `python run.py` for local Windows development.

### Initialize demo accounts

Demo accounts are not automatically created at web-server startup. In the Render service Shell, after setting `DEMO_MODE=true`, `DEMO_ADMIN_PASSWORD`, and `DEMO_OPERATOR_PASSWORD`, run:

```bash
flask --app run init-demo-users
```

This command targets the database configured by `DATABASE_URL`. It requires demo mode and both passwords, hashes credentials using the existing `User.set_password()` method, creates only missing accounts, and preserves existing passwords and roles on subsequent runs. It stops if the expected email or username is already assigned to a different account.

These are public fictional demo credentials and are insecure by design. Keep the demo instance separate from real student information. For a private/production deployment, leave `DEMO_MODE=false` and use a controlled account-provisioning process.

### Sign in and diagnose a failed Render login

Sign in with the account username and password. Email addresses are also accepted for existing accounts. Both identifiers are matched case-insensitively; passwords are checked against the stored Werkzeug hash.

The login route logs only the failure stage and reason; it never logs the submitted username, email, password, password hash, session cookie, or database URL. In Render's service Logs:

- `stage=account_lookup, reason=no_matching_identifier` means no account matched the submitted username/email in the selected database.
- `stage=password_verification, reason=mismatch` means an account was found but its stored hash did not verify the submitted password.
- `stage=account_lookup, error_type=...` means the account query failed; check the database connection and `users` table/schema.

To confirm which kind of database the deployed service uses and whether the account exists, open the service Shell and run `flask --app run shell`, then:

```python
from sqlalchemy import func
from app.models import User, db

url = db.engine.url
print({
    "driver": url.drivername,
    "host_configured": bool(url.host),
    "database_configured": bool(url.database),
    "user_count": User.query.count(),
})
identifier = input("Account username or email to check: ").strip().lower()
print({
    "matching_accounts": User.query.filter(
        (func.lower(User.username) == identifier)
        | (func.lower(User.email) == identifier)
    ).count(),
})
```

Do not print or share `DATABASE_URL`; in the Render dashboard, verify it points to the intended PostgreSQL database. The query above does not read or display password hashes. If no account matches, verify the intended production account rather than resetting the database or disabling verification.

The demo passwords shown on the login screen work only if those demo accounts were initialized in the database with those passwords. `init-demo-users` preserves existing accounts, including their passwords; running it again does not reset them.

#### Reset an existing administrator password

Deploy the application code containing the `reset-admin-password` CLI command first. In the Render service's Environment settings, temporarily set:

- `ADMIN_RESET_USERNAME` to the current username of the administrator account.
- `ADMIN_RESET_PASSWORD` to a new unique password of at least 12 characters.
- `CONFIRM_ADMIN_PASSWORD_RESET=YES` to explicitly authorize the change.
- Optionally, `ADMIN_RESET_NEW_USERNAME` to change that account's username; omit it to keep the current username.

Do not put the password in source control or in a command-line argument. Use the Render Shell for the same web service, confirm its `DATABASE_URL` is configured for the intended production database (do not print or share the URL), and run:

```bash
flask --app run reset-admin-password
```

The command updates exactly one existing account whose current username matches and whose role is `ADMIN`. It rejects missing/ambiguous targets, a username already used by another account, missing confirmation, or a password shorter than 12 characters. It changes no other users, email addresses, roles, or records; the password is hashed using `User.set_password()`. After success, remove `ADMIN_RESET_USERNAME`, `ADMIN_RESET_NEW_USERNAME` (if set), `ADMIN_RESET_PASSWORD`, and `CONFIRM_ADMIN_PASSWORD_RESET` from Render's environment, then sign in using the resulting username and new password. Verify login in the deployed application; the CLI success message alone does not confirm the browser login.

If no administrator account exists, use the `bootstrap-admin` creation procedure below instead. That command refuses to overwrite an existing administrator. Neither procedure resets the database.

### Bootstrap a production administrator

Web startup does not create an administrator. To create the first administrator in the Render database without resetting records:

1. In the Render service environment, temporarily set `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_EMAIL`, and a unique `BOOTSTRAP_ADMIN_PASSWORD` of at least 12 characters. Do not put the password in source control or in a command-line argument.
2. Open the deployed service Shell and run:
   ```bash
   flask --app run bootstrap-admin
   ```
3. Sign in using the configured email and password.
4. Remove all three `BOOTSTRAP_ADMIN_*` variables from the Render environment.

The one-time command creates an `ADMIN` account in the database selected by `DATABASE_URL`, hashes the password, and refuses to run if an administrator already exists or if the username/email is already assigned. It never resets an existing account. If an administrator already exists but its credentials are unknown, use the reset procedure above rather than rerunning bootstrap. Do not use the destructive seed script on a database with records to preserve.

The legacy `scripts/seed_demo_data.py` script drops and recreates tables and data. It is for disposable local databases only; never run it against Render or a database containing records you need.

## Features

- Login, logout, and role-based access control
- Student record management and validation
- Intake monitoring and dashboard metrics
- CSV reports and audit logs
- Institution settings

## Notes

- All sample data is fictional.
- Validation is a local format/consistency check, not an official APAAR verification.
- Charts and statistics are generated from application database records.
