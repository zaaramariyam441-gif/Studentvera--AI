import csv
import io
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from sqlalchemy import or_
from .models import db, Student, AuditLog, AppSetting
from .verification import validate_student_record

students_bp = Blueprint("students", __name__)


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


@students_bp.route("/students")
@login_required
def list_students():
    query = request.args.get("q", "")
    programme = request.args.get("programme", "")
    year = request.args.get("year", "")
    validation_status = request.args.get("validation_status", "")
    sort = request.args.get("sort", "name")
    page = request.args.get("page", 1, type=int)
    per_page = 10

    stmt = Student.query
    if query:
        like = f"%{query}%"
        stmt = stmt.filter(or_(Student.name.ilike(like), Student.student_id.ilike(like), Student.apara_id.ilike(like)))
    if programme:
        stmt = stmt.filter_by(programme=programme)
    if year:
        stmt = stmt.filter_by(academic_year=year)
    if validation_status:
        stmt = stmt.filter_by(validation_status=validation_status)

    sort_map = {
        "name": Student.name.asc(),
        "student_id": Student.student_id.asc(),
        "programme": Student.programme.asc(),
        "created_at": Student.created_at.desc(),
    }
    stmt = stmt.order_by(sort_map.get(sort, Student.name.asc()))
    pagination = stmt.paginate(page=page, per_page=per_page, error_out=False)
    programmes = sorted({s.programme for s in Student.query.all()})
    years = sorted({s.academic_year for s in Student.query.all()})
    return render_template(
        "students.html",
        students=pagination.items,
        pagination=pagination,
        query=query,
        programme=programme,
        year=year,
        validation_status=validation_status,
        sort=sort,
        programmes=programmes,
        years=years,
    )


@students_bp.route("/students/new", methods=["GET", "POST"])
@login_required
def create_student():
    if request.method == "POST":
        # extra role enforcement done centrally on routes as needed
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        apara_id = request.form.get("apara_id", "").strip()
        programme = request.form.get("programme", "").strip()
        department = request.form.get("department", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        admission_date = parse_date(request.form.get("admission_date", ""))
        admission_status = request.form.get("admission_status", "").strip()

        errors = []
        if not student_id:
            errors.append("Student ID is required.")
        if not name:
            errors.append("Student name is required.")
        if not apara_id:
            errors.append("APAAR ID is required.")
        if not programme:
            errors.append("Programme is required.")
        if not department:
            errors.append("Department is required.")
        if not academic_year:
            errors.append("Academic year is required.")
        if not admission_date:
            errors.append("Admission date is required.")
        if not admission_status:
            errors.append("Admission status is required.")

        duplicate_warnings = []
        if Student.query.filter_by(student_id=student_id).first() and student_id:
            duplicate_warnings.append("A student record with this Student ID already exists; the record will be flagged for review.")
        if Student.query.filter_by(apara_id=apara_id).first() and apara_id:
            duplicate_warnings.append("A student record with this APAAR ID already exists; the record will be flagged for duplicate review.")

        if errors:
            flash("; ".join(errors), "danger")
            return render_template("add_student.html", form_data=request.form)

        validation_status = "REVIEW REQUIRED"
        if duplicate_warnings:
            validation_status = "DUPLICATE FLAG"

        student = Student(
            student_id=student_id,
            name=name,
            apara_id=apara_id,
            programme=programme,
            department=department,
            academic_year=academic_year,
            admission_date=admission_date,
            admission_status=admission_status,
            validation_status=validation_status,
        )
        db.session.add(student)
        db.session.flush()
        if duplicate_warnings:
            for warning in duplicate_warnings:
                flash(warning, "warning")
        db.session.add(AuditLog(event_type="student_created", description=f"Student record created: {student.name}", user_id=current_user.id, related_record_id=student.id))
        db.session.commit()
        flash("Student record added successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("add_student.html")


@students_bp.route("/students/<int:student_id>")
@login_required
def view_student(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template("student_detail.html", student=student)


@students_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        student.student_id = request.form.get("student_id", "").strip()
        student.name = request.form.get("name", "").strip()
        student.apara_id = request.form.get("apara_id", "").strip()
        student.programme = request.form.get("programme", "").strip()
        student.department = request.form.get("department", "").strip()
        student.academic_year = request.form.get("academic_year", "").strip()
        student.admission_date = parse_date(request.form.get("admission_date", ""))
        student.admission_status = request.form.get("admission_status", "").strip()
        student.validation_status = "REVIEW REQUIRED"
        db.session.add(AuditLog(event_type="student_updated", description=f"Student record updated: {student.name}", user_id=current_user.id, related_record_id=student.id))
        db.session.commit()
        flash("Student record updated.", "success")
        return redirect(url_for("students.view_student", student_id=student.id))
    return render_template("edit_student.html", student=student)


@students_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.add(AuditLog(event_type="student_deleted", description=f"Student record deleted: {student.name}", user_id=current_user.id, related_record_id=student.id))
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("students.list_students"))


@students_bp.route("/students/export")
@login_required
def export_students_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "student_id", "name", "apara_id", "programme", "department", "academic_year", "admission_date", "admission_status", "validation_status"])
    for student in Student.query.all():
        writer.writerow([
            student.id,
            student.student_id,
            student.name,
            student.apara_id,
            student.programme,
            student.department,
            student.academic_year,
            student.admission_date.strftime("%Y-%m-%d") if student.admission_date else "",
            student.admission_status,
            student.validation_status,
        ])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=studentvera_students.csv"
    return response
