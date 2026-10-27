# STUDENTVERA AI

Less spreadsheet archaeology. Fewer duplicate records. More intelligent verification. Because academic administration deserves better plotlines. | SIH 2026.

STUDENTVERA AI is a prototype for an APAAR ID-based student data management and verification platform for AICTE-approved institutions.

## Important disclaimer

This project is a prototype for demonstration and local testing only. It is not an official APAAR verification system, and the application does not connect to any official governmental or institutional identity services.

## Tech stack

- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- PostgreSQL (primary and documented)
- SQLite fallback for local demo when PostgreSQL is unavailable

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
3. Copy the sample env file and adjust as needed:
   ```bash
   copy .env.example .env
   ```
4. Configure DATABASE_URL in `.env`.

### PostgreSQL (recommended)

```env
DATABASE_URL=postgresql://studentvera:studentvera@localhost:5432/studentvera
```

Create the database if needed:

```bash
createdb studentvera
```

### SQLite fallback

If PostgreSQL is unavailable, set:

```env
DATABASE_URL=sqlite:///studentvera_dev.db
```

The project will use the SQLite file automatically if PostgreSQL is not available.

## Seed demo data

Run the seeding script to populate the database with fictional demo records and user accounts.

```bash
python scripts/seed_demo_data.py
```

## Run the app

For local development on Windows:

```bash
python run.py
```

Open:

http://127.0.0.1:5000/login

For production deployment on a supported Linux environment, install dependencies and run Gunicorn from the project root:

```bash
gunicorn --bind 0.0.0.0:8000 run:app
```

Gunicorn is a production WSGI server and is not supported on Windows; use the development command above for local Windows development.

## Demo login credentials

- Admin: admin@demo.local / Admin@123
- Institution Operator: operator@demo.local / Operator@123

## Features included

- Login and logout
- Role-based access control
- Student record management
- Validation engine with APAAR format checks and duplicate detection
- Intake monitoring
- Dashboard metrics
- CSV export
- Audit log
- Settings and demo-data reset support

## Notes

- The application uses fictional data only.
- All charts and stats are generated from actual database rows.
- The application is intentionally designed as a local prototype for Smart India Hackathon demonstration.
