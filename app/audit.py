from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import AuditLog

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit")
@login_required
def audit_logs():
    if current_user.role != "ADMIN":
        return render_template("error.html", message="Only administrators can access audit logs."), 403
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    return render_template("audit.html", logs=logs)
