import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import db, User, Student, AppSetting, IntakeProgram, AuditLog
from werkzeug.security import generate_password_hash


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        AppSetting.query.delete()
        User.query.delete()
        Student.query.delete()
        IntakeProgram.query.delete()
        AuditLog.query.delete()

        AppSetting.query.filter_by(key="institution_name").delete()
        AppSetting.query.filter_by(key="academic_year").delete()
        AppSetting.query.filter_by(key="apaar_rule").delete()
        AppSetting.query.filter_by(key="demo_banner").delete()

        db.session.add(AppSetting(key="institution_name", value="AICTE Demo Institution"))
        db.session.add(AppSetting(key="academic_year", value="2026-27"))
        db.session.add(AppSetting(key="apaar_rule", value=r"^[A-Z0-9]{12}$"))
        db.session.add(AppSetting(key="demo_banner", value="DEMONSTRATION ENVIRONMENT — FICTIONAL DATA"))

        admin = User(username="admin", email="admin@demo.local", role="ADMIN")
        admin.set_password("Admin@123")
        operator = User(username="operator", email="operator@demo.local", role="INSTITUTION_OPERATOR")
        operator.set_password("Operator@123")
        db.session.add_all([admin, operator])
        db.session.commit()

        programmes = [
            ("Bachelor of Computer Applications", 90),
            ("B.Tech Computer Science", 120),
            ("B.Tech Information Technology", 110),
            ("Master of Computer Applications", 60),
        ]
        for name, limit in programmes:
            db.session.add(IntakeProgram(programme_name=name, intake_limit=limit, description="Fictional demonstration programme"))

        students = [
            Student(student_id="STU-1001", name="Aarav Sharma", apara_id="AARV20240601", programme="Bachelor of Computer Applications", department="Computer Science", academic_year="2026-27", admission_date=date(2026, 6, 12), admission_status="ADMITTED", validation_status="PASS"),
            Student(student_id="STU-1002", name="Meera Nair", apara_id="MEER20240602", programme="Bachelor of Computer Applications", department="Computer Science", academic_year="2026-27", admission_date=date(2026, 6, 13), admission_status="ADMITTED", validation_status="REVIEW REQUIRED"),
            Student(student_id="STU-1003", name="Kabir Singh", apara_id="DUPL20240001", programme="B.Tech Computer Science", department="Computer Science", academic_year="2026-27", admission_date=date(2026, 6, 15), admission_status="ADMITTED", validation_status="DUPLICATE FLAG"),
            Student(student_id="STU-1004", name="Ishita Rao", apara_id="DUPL20240001", programme="B.Tech Information Technology", department="Information Technology", academic_year="2026-27", admission_date=date(2026, 6, 16), admission_status="ADMITTED", validation_status="DUPLICATE FLAG"),
            Student(student_id="STU-1005", name="Rohan Verma", apara_id="ROHA20240605", programme="B.Tech Computer Science", department="Computer Science", academic_year="2025-26", admission_date=date(2026, 6, 18), admission_status="ADMITTED", validation_status="REVIEW REQUIRED"),
            Student(student_id="STU-1006", name="Ananya Das", apara_id="ANAN20240606", programme="Master of Computer Applications", department="Computer Applications", academic_year="2026-27", admission_date=date(2026, 6, 20), admission_status="WAITLISTED", validation_status="INCOMPLETE"),
            Student(student_id="STU-1007", name="Vikram Iyer", apara_id="BAD-20240607", programme="B.Tech Information Technology", department="Information Technology", academic_year="2026-27", admission_date=date(2026, 6, 21), admission_status="ADMITTED", validation_status="REVIEW REQUIRED"),
        ]
        db.session.add_all(students)
        db.session.commit()

        db.session.add(AuditLog(event_type="demo_seeded", description="Demo dataset seeded for demonstration purposes.", user_id=admin.id))
        db.session.commit()
        print("Demo data seeded successfully.")
        print("Admin login: admin@demo.local / Admin@123")
        print("Operator login: operator@demo.local / Operator@123")


if __name__ == "__main__":
    seed()
