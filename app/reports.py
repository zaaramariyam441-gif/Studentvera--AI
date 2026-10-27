import csv
import io
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from .models import Student, AuditLog

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
@login_required
def reports_page():
    report_type = request.args.get("type", "summary")
    if report_type == "summary":
        rows = Student.query.all()
    elif report_type == "duplicates":
        rows = []
        seen_ids = set()
        seen_apaar = set()
        for student in Student.query.all():
            if student.student_id in seen_ids:
                rows.append(student)
            else:
                seen_ids.add(student.student_id)
            if student.apara_id in seen_apaar:
                rows.append(student)
            else:
                seen_apaar.add(student.apara_id)
    elif report_type == "incomplete":
        rows = [s for s in Student.query.all() if s.validation_status in ("INCOMPLETE", "REVIEW REQUIRED")]
    else:
        rows = Student.query.all()
    return render_template("reports.html", report_type=report_type, rows=rows)


@reports_bp.route("/reports/export")
@login_required
def export_report_csv():
    report_type = request.args.get("type", "summary")
    rows = Student.query.all()
    if report_type == "duplicate":
        rows = [s for s in Student.query.all() if s.validation_status == "DUPLICATE FLAG"]
    elif report_type == "incomplete":
        rows = [s for s in Student.query.all() if s.validation_status == "INCOMPLETE"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_id", "name", "programme", "department", "academic_year", "validation_status"])
    for student in rows:
        writer.writerow([student.student_id, student.name, student.programme, student.department, student.academic_year, student.validation_status])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=studentvera_{report_type}_report.csv"
    db_session = __import__("app.models", fromlist=["db"]).db
    db_session.session.add(AuditLog(event_type="report_generated", description=f"Report exported: {report_type}", user_id=current_user.id))
    db_session.session.commit()
    return response
