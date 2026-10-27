from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from .models import db, Student, IntakeProgram, AuditLog, User

dashboard_bp = Blueprint("dashboard", __name__)


def compute_dashboard_metrics():
    total_records = Student.query.count()
    valid_records = Student.query.filter_by(validation_status="PASS").count()
    review_records = Student.query.filter_by(validation_status="REVIEW REQUIRED").count()
    duplicate_records = Student.query.filter_by(validation_status="DUPLICATE FLAG").count()
    intake_programs = IntakeProgram.query.all()
    total_limit = sum(program.intake_limit for program in intake_programs)
    current_total = Student.query.count()
    intake_util = 0
    if total_limit > 0:
        intake_util = round((current_total / total_limit) * 100, 2)
    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "review_records": review_records,
        "duplicate_records": duplicate_records,
        "intake_utilisation": intake_util,
    }


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def overview():
    metrics = compute_dashboard_metrics()
    validation_distribution = db.session.query(Student.validation_status, func.count(Student.id)).group_by(Student.validation_status).all()
    department_distribution = db.session.query(Student.department, func.count(Student.id)).group_by(Student.department).all()
    recent_activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    intake_programs = IntakeProgram.query.all()
    return render_template(
        "dashboard.html",
        metrics=metrics,
        validation_distribution=validation_distribution,
        department_distribution=department_distribution,
        recent_activity=recent_activity,
        intake_programs=intake_programs,
        current_user=current_user,
    )
