import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from .models import db, Student, AuditLog, AppSetting

verification_bp = Blueprint("verification", __name__)


def get_apaar_rule():
    setting = AppSetting.query.filter_by(key="apaar_rule").first()
    if setting:
        try:
            return re.compile(setting.value)
        except re.error:
            return re.compile(r"^[A-Z0-9]{12}$")
    return re.compile(r"^[A-Z0-9]{12}$")


def validate_student_record(student):
    rule = get_apaar_rule()
    reasons = []
    status = "PASS"
    required_fields = ["student_id", "name", "apara_id", "programme", "academic_year", "admission_status"]
    for field in required_fields:
        value = getattr(student, field, "") or ""
        if not str(value).strip():
            reasons.append(f"Missing required field: {field}.")
            status = "INCOMPLETE"
    if hasattr(student, "department") and not str(student.department).strip():
        reasons.append("Missing required field: department.")
        status = "INCOMPLETE"
    if student.admission_date is None:
        reasons.append("Missing required field: admission_date.")
        status = "INCOMPLETE"
    if str(student.apara_id).strip() and not rule.fullmatch(str(student.apara_id).strip()):
        reasons.append("APAAR format check failed. Format: demonstration rule using uppercase letters/digits, 12 chars.")
        status = "REVIEW REQUIRED"
    dup_by_student_id = Student.query.filter(Student.student_id == student.student_id, Student.id != student.id).first()
    if dup_by_student_id:
        reasons.append("Duplicate student ID detected.")
        status = "DUPLICATE FLAG"
    dup_by_apara = Student.query.filter(Student.apara_id == student.apara_id, Student.id != student.id).first()
    if dup_by_apara:
        reasons.append("Duplicate APAAR ID detected.")
        status = "DUPLICATE FLAG"
    if not student.programme or not student.programme.strip():
        reasons.append("Programme is missing or unrecognised.")
        status = "INCOMPLETE"
    if not re.fullmatch(r"\d{4}[-/]\d{2}", student.academic_year or ""):
        reasons.append("Academic year format is invalid. Use YYYY-YY or YYYY/YY format.")
        status = "REVIEW REQUIRED"
    if not student.admission_status or not str(student.admission_status).strip():
        reasons.append("Admission status is missing or invalid.")
        status = "INCOMPLETE"
    if not reasons:
        student.validation_status = "PASS"
    elif status == "DUPLICATE FLAG":
        student.validation_status = "DUPLICATE FLAG"
    elif status == "INCOMPLETE":
        student.validation_status = "INCOMPLETE"
    else:
        student.validation_status = "REVIEW REQUIRED"
    return {"status": student.validation_status, "reasons": reasons}


@verification_bp.route("/verification")
@login_required
def verification_page():
    students = Student.query.order_by(Student.name.asc()).all()
    return render_template("verification.html", students=students)


@verification_bp.route("/verification/run", methods=["POST"])
@login_required
def run_verification():
    selected_ids = request.form.getlist("student_ids")
    if selected_ids:
        students = Student.query.filter(Student.id.in_(selected_ids)).all()
    else:
        students = Student.query.all()
    results = []
    for student in students:
        result = validate_student_record(student)
        results.append({"student_id": student.id, "name": student.name, "status": result["status"], "reasons": result["reasons"]})
    db.session.commit()
    db.session.add(AuditLog(event_type="validation_run", description=f"Validation run for {len(students)} student records.", user_id=current_user.id))
    db.session.commit()
    flash(f"Validation run completed for {len(students)} records.", "success")
    return redirect(url_for("verification.verification_page"))


@verification_bp.route("/verification/export")
@login_required
def export_validation_csv():
    students = Student.query.all()
    rows = []
    for student in students:
        result = validate_student_record(student)
        rows.append({"student_id": student.student_id, "name": student.name, "status": result["status"], "reasons": "; ".join(result["reasons"])})
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_id", "name", "status", "reasons"])
    for row in rows:
        writer.writerow([row["student_id"], row["name"], row["status"], row["reasons"]])
    from flask import Response
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=studentvera_validation_report.csv"
    return response
