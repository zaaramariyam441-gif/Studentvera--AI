import pytest

from app import create_app
from app.models import db, User, Student, AuditLog, IntakeProgram


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
    response = client.post('/login', data={'email': 'admin@demo.local', 'password': 'Admin@123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data


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
