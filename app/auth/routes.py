from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, limiter
from ..models import Role, User
from .forms import ChangePasswordForm, LoginForm

auth_bp = Blueprint("auth", __name__)

# Compared against when the login ID does not exist, so a failed login takes
# the same time either way (no user-enumeration timing side channel).
_DUMMY_HASH = generate_password_hash("timing-equalizer-not-a-real-password")


def safe_next_url(target):
    """Only same-site relative paths. Rejects //host, /\\host (browsers
    normalise backslashes to slashes) and anything with a scheme."""
    if not target:
        return None
    if (
        target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
        and "\r" not in target
        and "\n" not in target
    ):
        return target
    return None


def home_for(user):
    if user.role == Role.SUPER_ADMIN:
        return url_for("admin.dashboard")
    if user.role == Role.SUBJECT_TEACHER:
        return url_for("teacher.dashboard")
    if user.role == Role.CLASS_TEACHER:
        return url_for("teacher.class_dashboard")
    return url_for("student.dashboard")


# Which roles may sign in through which panel.
LOGIN_PANELS = {
    "student": {
        "roles": (Role.STUDENT,),
        "title": "Student Login",
        "hint": "Sign in with your roll-based ID.",
    },
    "teacher": {
        "roles": (Role.SUBJECT_TEACHER, Role.CLASS_TEACHER),
        "title": "Teacher Login",
        "hint": "For subject teachers and class teachers.",
    },
    "admin": {
        "roles": (Role.SUPER_ADMIN,),
        "title": "Admin Login",
        "hint": "Authorised administrators only.",
    },
}

PANEL_FOR_ROLE = {
    Role.STUDENT: "student",
    Role.SUBJECT_TEACHER: "teacher",
    Role.CLASS_TEACHER: "teacher",
    Role.SUPER_ADMIN: "admin",
}


@auth_bp.route("/login", methods=["GET", "POST"], defaults={"panel": "student"})
@auth_bp.route("/login/<panel>", methods=["GET", "POST"])
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login(panel):
    if panel not in LOGIN_PANELS:
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        return redirect(home_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).filter_by(login_id=form.login_id.data.strip())
        )
        # Generic error: never reveal which field was wrong. Always burn one
        # hash comparison so timing does not reveal whether the ID exists.
        if user is None:
            check_password_hash(_DUMMY_HASH, form.password.data)
            password_ok = False
        else:
            password_ok = user.check_password(form.password.data)
        if user is None or not user.is_active or not password_ok:
            flash("Invalid ID or password.", "error")
            return render_template("auth/login.html", form=form, panel=panel)

        # Right credentials, wrong panel: point them to their own panel.
        if user.role not in LOGIN_PANELS[panel]["roles"]:
            correct = PANEL_FOR_ROLE[user.role]
            flash(
                f"This account belongs to the {LOGIN_PANELS[correct]['title']} — "
                "please use that panel.",
                "error",
            )
            return redirect(url_for("auth.login", panel=correct))

        # Drop any pre-auth session state before issuing the logged-in session.
        session.clear()
        login_user(user)
        if user.must_change_password:
            return redirect(url_for("auth.change_password"))
        next_url = safe_next_url(
            request.args.get("next") or request.form.get("next")
        )
        if next_url:
            return redirect(next_url)
        return redirect(home_for(user))

    return render_template("auth/login.html", form=form, panel=panel)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "error")
            return render_template("auth/change_password.html", form=form)
        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()
        # The session token is bound to the password hash: re-issue this
        # session so the user stays logged in while every OTHER session
        # (e.g. a stolen one) dies immediately. Unwrap the LocalProxy —
        # login_user must receive the real User object.
        login_user(current_user._get_current_object())
        flash("Password changed.", "success")
        return redirect(home_for(current_user))

    return render_template(
        "auth/change_password.html",
        form=form,
        forced=current_user.must_change_password,
    )
