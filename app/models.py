from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="INSTITUTION_OPERATOR")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    apara_id = db.Column(db.String(80), nullable=False)
    programme = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    admission_date = db.Column(db.Date, nullable=False)
    admission_status = db.Column(db.String(40), nullable=False)
    validation_status = db.Column(db.String(40), nullable=False, default="PASS")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "apara_id": self.apara_id,
            "programme": self.programme,
            "department": self.department,
            "academic_year": self.academic_year,
            "admission_date": self.admission_date.strftime("%Y-%m-%d") if self.admission_date else "",
            "admission_status": self.admission_status,
            "validation_status": self.validation_status,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class IntakeProgram(db.Model):
    __tablename__ = "intake_programs"
    id = db.Column(db.Integer, primary_key=True)
    programme_name = db.Column(db.String(150), nullable=False, unique=True)
    intake_limit = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def utilisation_percent(self):
        if self.intake_limit <= 0:
            return 0
        count = Student.query.filter_by(programme=self.programme_name).count()
        return round((count / self.intake_limit) * 100, 2)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    related_record_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])


class AppSetting(db.Model):
    __tablename__ = "app_settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSetting {self.key}>"
