from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, AppSetting, IntakeProgram, AuditLog

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    if current_user.role != "ADMIN":
        return render_template("error.html", message="Only administrators can manage settings."), 403
    if request.method == "POST":
        for key in [
            "institution_name",
            "institution_tagline",
            "institution_email",
            "institution_phone",
            "institution_city",
            "academic_year",
            "apaar_rule",
            "verification_policy",
            "demo_banner",
        ]:
            value = request.form.get(key, "")
            setting = AppSetting.query.filter_by(key=key).first()
            if not setting:
                setting = AppSetting(key=key, value=value)
                db.session.add(setting)
            else:
                setting.value = value
        db.session.add(AuditLog(event_type="settings_changed", description="Application settings updated.", user_id=current_user.id))
        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings.settings_page"))
    settings = {item.key: item.value for item in AppSetting.query.all()}
    programmes = IntakeProgram.query.order_by(IntakeProgram.programme_name.asc()).all()
    return render_template("settings.html", settings=settings, programmes=programmes)
