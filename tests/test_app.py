import re

import pytest

from app import create_app
from app.models import db, User, Student, AuditLog, IntakeProgram
from config import normalize_database_url


@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(username='admin', email='admin@demo.local', role='ADMIN')
        admin.set_password('Admin@123')
        operator = User(username='operator', email='operator@demo.local', role='INSTITUTION_OPERATOR')
        operator.set_password('Operator@123')
        db.session.add_all([admin, operator])
        db.session.add_all([
            IntakeProgram(programme_name='Bachelor of Computer Applications', intake_limit=10),
            IntakeProgram(programme_name='B.Tech Computer Science', intake_limit=8),
        ])
        db.session.commit()
    with app.test_client() as client:
        yield client


def test_login_and_logout(client):
    response = client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')
    response = client.get(response.headers['Location'], follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


@pytest.mark.parametrize(('email', 'password'), [
    ('admin@demo.local', 'wrong-password'),
    ('unknown@demo.local', 'Admin@123'),
])
def test_login_rejects_invalid_password_and_unknown_email(client, email, password):
    response = client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password.' in response.data
    assert b'Logout' not in response.data


def test_demo_user_initialization_is_explicit_idempotent_and_preserves_existing_credentials():
    app = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'DEMO_MODE': True,
        'DEMO_ADMIN_PASSWORD': 'Admin@123',
        'DEMO_OPERATOR_PASSWORD': 'Operator@123',
    })
    runner = app.test_cli_runner()

    result = runner.invoke(args=['init-demo-users'])
    assert result.exit_code == 0, result.output
    assert '2 created, 0 existing account(s) preserved' in result.output

    with app.app_context():
        admin = User.query.filter_by(email='admin@demo.local').one()
        operator = User.query.filter_by(email='operator@demo.local').one()
        assert admin.role == 'ADMIN'
        assert admin.check_password('Admin@123')
        assert admin.password_hash != 'Admin@123'
        assert operator.role == 'INSTITUTION_OPERATOR'
        assert operator.check_password('Operator@123')
        admin.set_password('Changed-by-admin')
        admin.role = 'INSTITUTION_OPERATOR'
        db.session.commit()
        stored_hash = admin.password_hash

    result = runner.invoke(args=['init-demo-users'])
    assert result.exit_code == 0, result.output
    assert '0 created, 2 existing account(s) preserved' in result.output
    with app.app_context():
        admin = User.query.filter_by(email='admin@demo.local').one()
        assert User.query.count() == 2
        assert admin.password_hash == stored_hash
        assert admin.role == 'INSTITUTION_OPERATOR'
        assert admin.check_password('Changed-by-admin')


def test_demo_user_initialization_requires_demo_mode(client):
    result = client.application.test_cli_runner().invoke(args=['init-demo-users'])
    assert result.exit_code != 0
    assert 'requires DEMO_MODE=true' in result.output


def test_login_csrf_protection_remains_enabled():
    app = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    with app.app_context():
        admin = User(username='admin', email='admin@demo.local', role='ADMIN')
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()

    client = app.test_client()
    response = client.post('/login', data={
        'email': 'admin@demo.local',
        'password': 'Admin@123',
    })
    assert response.status_code == 400
    response = client.get('/login')
    csrf_token = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert csrf_token is not None
    response = client.post('/login', data={
        'email': 'admin@demo.local',
        'password': 'Admin@123',
        'csrf_token': csrf_token.group(1).decode(),
    })
    assert response.status_code == 302


@pytest.mark.parametrize(('url', 'expected'), [
    ('postgres://user:pass@host:5432/studentvera', 'postgresql+psycopg://user:pass@host:5432/studentvera'),
    ('postgresql://user:pass@host:5432/studentvera', 'postgresql+psycopg://user:pass@host:5432/studentvera'),
    ('sqlite:///studentvera_dev.db', 'sqlite:///studentvera_dev.db'),
])
def test_database_url_normalization(url, expected):
    assert normalize_database_url(url) == expected


def test_role_based_access(client):
    client.post('/login', data={'email': 'operator@demo.local', 'password': 'Operator@123'}, follow_redirects=True)
    response = client.get('/audit', follow_redirects=False)
    assert response.status_code == 403


def test_student_creation_and_update(client):
    client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    response = client.post('/students/new', data={
        'student_id': 'STU-001',
        'name': 'Amit Rao',
        'apara_id': 'AMIT20240601',
        'programme': 'Bachelor of Computer Applications',
        'department': 'Computer Science',
        'academic_year': '2026-27',
        'admission_date': '2026-07-01',
        'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    assert response.status_code == 200
    with client.application.app_context():
        student = Student.query.filter_by(student_id='STU-001').first()
        assert student is not None
        student.validation_status = 'PASS'
        db.session.commit()
        student_id = student.id
    response = client.post(f'/students/{student_id}/edit', data={
        'student_id': 'STU-001',
        'name': 'Amit R. Rao',
        'apara_id': 'AMIT20240601',
        'programme': 'Bachelor of Computer Applications',
        'department': 'Computer Science',
        'academic_year': '2026-27',
        'admission_date': '2026-07-01',
        'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_required_field_and_duplicate_validation(client):
    client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    client.post('/students/new', data={
        'student_id': 'STU-002', 'name': 'Bharat Patel', 'apara_id': 'BHAR20240602',
        'programme': 'Bachelor of Computer Applications', 'department': 'Computer Science',
        'academic_year': '2026-27', 'admission_date': '2026-07-02', 'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    response = client.post('/students/new', data={
        'student_id': 'STU-003', 'name': 'Neha Shah', 'apara_id': 'BHAR20240602',
        'programme': 'Bachelor of Computer Applications', 'department': 'Computer Science',
        'academic_year': '2026-27', 'admission_date': '2026-07-03', 'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    assert response.status_code == 200
    response = client.post('/students/new', data={
        'student_id': '', 'name': '', 'apara_id': '',
        'programme': '', 'department': '', 'academic_year': '',
        'admission_date': '', 'admission_status': ''
    }, follow_redirects=True)
    assert b'Student ID is required' in response.data
    with client.application.app_context():
        students = Student.query.all()
        assert len(students) >= 2


def test_intake_and_audit_logs(client):
    client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    client.post('/students/new', data={
        'student_id': 'STU-004', 'name': 'Chetan Joshi', 'apara_id': 'CHET20240604',
        'programme': 'Bachelor of Computer Applications', 'department': 'Computer Science',
        'academic_year': '2026-27', 'admission_date': '2026-07-04', 'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    response = client.get('/intake')
    assert response.status_code == 200
    assert b'Bachelor of Computer Applications' in response.data
    with client.application.app_context():
        assert AuditLog.query.count() >= 1


def test_reports_export(client):
    client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    response = client.get('/reports/export?type=summary')
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('text/csv')
    assert b'student_id' in response.data


def test_verification_run(client):
    client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    client.post('/students/new', data={
        'student_id': 'STU-005', 'name': 'Disha Sharma', 'apara_id': 'BAD-123',
        'programme': 'B.Tech Computer Science', 'department': 'Computer Science',
        'academic_year': '2025-26', 'admission_date': '2026-07-05', 'admission_status': 'ADMITTED'
    }, follow_redirects=True)
    response = client.post('/verification/run', data={'student_ids': ['1']}, follow_redirects=True)
    assert response.status_code == 200
