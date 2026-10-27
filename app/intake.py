from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, IntakeProgram, Student, AuditLog

intake_bp = Blueprint("intake", __name__)


@intake_bp.route("/intake")
@login_required
def intake_dashboard():
    programs = IntakeProgram.query.order_by(IntakeProgram.programme_name.asc()).all()
    rows = []
    for program in programs:
        count = Student.query.filter_by(programme=program.programme_name).count()
        remaining = program.intake_limit - count if program.intake_limit > 0 else 0
        utilisation = 0 if program.intake_limit <= 0 else round((count / program.intake_limit) * 100, 2)
        if utilisation >= 100:
            status = "EXCEEDS LIMIT" if count > program.intake_limit else "AT LIMIT"
        elif utilisation > 80:
            status = "AT LIMIT"
        else:
            status = "WITHIN LIMIT"
        rows.append({
            "program": program,
            "current_count": count,
            "remaining": remaining,
            "utilisation": utilisation,
            "status": status,
        })
    return render_template("intake.html", rows=rows)


@intake_bp.route("/intake/config", methods=["GET", "POST"])
@login_required
def configure_intake():
    if current_user.role != "ADMIN":
        flash("Only administrators can configure intake limits.", "danger")
        return redirect(url_for("intake.intake_dashboard"))
    if request.method == "POST":
        for key in request.form:
            if key.startswith("limit_"):
                program_id = int(key.replace("limit_", ""))
                program = IntakeProgram.query.get_or_404(program_id)
                program.intake_limit = max(0, int(request.form.get(key, 0)))
        db.session.add(AuditLog(event_type="intake_updated", description="Intake configuration updated.", user_id=current_user.id))
        db.session.commit()
        flash("Intake limits updated successfully.", "success")
        return redirect(url_for("intake.intake_dashboard"))
    return redirect(url_for("intake.intake_dashboard"))
