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
