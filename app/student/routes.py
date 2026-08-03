from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Note, Role, Subject
from ..utils.points import leaderboard as leaderboard_query
from ..utils.points import tier_for, total_for
from ..utils.security import can_moderate_scope, require_view_scope

student_bp = Blueprint("student", __name__)


@student_bp.route("/")
@login_required
def dashboard():
    # Route each role to its own home; this page is the student home.
    if current_user.role == Role.SUPER_ADMIN:
        return redirect(url_for("admin.dashboard"))
    if current_user.role == Role.SUBJECT_TEACHER:
        return redirect(url_for("teacher.dashboard"))
    if current_user.role == Role.CLASS_TEACHER:
        return redirect(url_for("teacher.class_dashboard"))

    if current_user.class_id is None or current_user.section_id is None:
        abort(403)
    subjects = db.session.scalars(
        db.select(Subject)
        .filter_by(
            class_id=current_user.class_id, section_id=current_user.section_id
        )
        .order_by(Subject.name)
    ).all()
    recent_notes = db.session.scalars(
        db.select(Note)
        .filter_by(
            class_id=current_user.class_id,
            section_id=current_user.section_id,
            is_hidden=False,
        )
        .order_by(Note.created_at.desc())
        .limit(8)
    ).all()
    my_points = total_for(current_user.id)
    tier_name, tier_css = tier_for(my_points)
    return render_template(
        "student/dashboard.html",
        subjects=subjects,
        recent_notes=recent_notes,
        my_points=my_points,
        tier_name=tier_name,
        tier_css=tier_css,
    )


@student_bp.route("/leaderboard")
@login_required
def leaderboard():
    if current_user.role in (Role.STUDENT, Role.CLASS_TEACHER):
        class_id, section_id = current_user.class_id, current_user.section_id
        if class_id is None or section_id is None:
            abort(403)
        section = current_user.section
    else:
        abort(403)

    rows = leaderboard_query(class_id, section_id, limit=10)
    my_points = total_for(current_user.id)
    tier_name, tier_css = tier_for(my_points)
    return render_template(
        "student/leaderboard.html",
        rows=rows,
        section=section,
        my_points=my_points,
        tier_name=tier_name,
        tier_css=tier_css,
        tier_for=tier_for,
    )


@student_bp.route("/subject/<int:subject_id>")
@login_required
def subject(subject_id):
    subj = db.get_or_404(Subject, subject_id)
    require_view_scope(subj.class_id, subj.section_id)
    return render_template("student/subject.html", subject=subj)


@student_bp.route("/chapter/<int:chapter_id>")
@login_required
def chapter(chapter_id):
    from ..models import Chapter

    chap = db.get_or_404(Chapter, chapter_id)
    subj = chap.subject
    require_view_scope(subj.class_id, subj.section_id)
    query = db.select(Note).filter_by(chapter_id=chap.id)
    if not can_moderate_scope(current_user, subj.class_id, subj.section_id):
        query = query.filter_by(is_hidden=False)
    notes = db.session.scalars(
        query.order_by(Note.is_official.desc(), Note.created_at.desc())
    ).all()
    return render_template("student/chapter.html", chapter=chap, notes=notes)
