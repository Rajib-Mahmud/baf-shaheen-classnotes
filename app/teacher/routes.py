from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from ..extensions import db
from ..models import Chapter, Note, Report, Role, Subject, User
from ..utils.images import delete_note_files
from ..utils.security import can_moderate_scope, owns_subject, roles_required
from .forms import ChapterForm, CreateStudentForm, ResetStudentPasswordForm

teacher_bp = Blueprint("teacher", __name__)


# ---------------- Subject teacher ----------------


@teacher_bp.route("/")
@roles_required(Role.SUBJECT_TEACHER)
def dashboard():
    subjects = db.session.scalars(
        db.select(Subject).filter_by(teacher_id=current_user.id)
    ).all()
    if current_user.role == Role.SUPER_ADMIN:
        subjects = db.session.scalars(db.select(Subject)).all()
    return render_template("teacher/dashboard.html", subjects=subjects)


@teacher_bp.route("/subject/<int:subject_id>/chapters", methods=["GET", "POST"])
@roles_required(Role.SUBJECT_TEACHER)
def chapters(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    if not owns_subject(current_user, subject):
        abort(403)
    form = ChapterForm()
    if form.validate_on_submit():
        chapter = Chapter(
            title=form.title.data.strip(),
            order_index=form.order_index.data or 0,
            subject_id=subject.id,
        )
        db.session.add(chapter)
        db.session.commit()
        flash("Chapter created.", "success")
        return redirect(url_for("teacher.chapters", subject_id=subject.id))
    return render_template("teacher/chapters.html", subject=subject, form=form)


@teacher_bp.route(
    "/chapter/<int:chapter_id>/edit", methods=["GET", "POST"]
)
@roles_required(Role.SUBJECT_TEACHER)
def edit_chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    if not owns_subject(current_user, chapter.subject):
        abort(403)
    form = ChapterForm(obj=chapter)
    if form.validate_on_submit():
        chapter.title = form.title.data.strip()
        chapter.order_index = form.order_index.data or 0
        db.session.commit()
        flash("Chapter updated.", "success")
        return redirect(url_for("teacher.chapters", subject_id=chapter.subject_id))
    return render_template(
        "teacher/edit_chapter.html", chapter=chapter, form=form
    )


@teacher_bp.route("/chapter/<int:chapter_id>/delete", methods=["POST"])
@roles_required(Role.SUBJECT_TEACHER)
def delete_chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    if not owns_subject(current_user, chapter.subject):
        abort(403)
    if chapter.notes:
        flash("Cannot delete: this chapter still has notes.", "error")
    else:
        subject_id = chapter.subject_id
        db.session.delete(chapter)
        db.session.commit()
        flash("Chapter deleted.", "success")
        return redirect(url_for("teacher.chapters", subject_id=subject_id))
    return redirect(url_for("teacher.chapters", subject_id=chapter.subject_id))


# ---------------- Class teacher ----------------


@teacher_bp.route("/class")
@roles_required(Role.CLASS_TEACHER)
def class_dashboard():
    if current_user.role == Role.CLASS_TEACHER and (
        current_user.class_id is None or current_user.section_id is None
    ):
        abort(403)
    students = db.session.scalars(
        db.select(User)
        .filter_by(
            role=Role.STUDENT,
            class_id=current_user.class_id,
            section_id=current_user.section_id,
        )
        .order_by(User.login_id)
    ).all()
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
            class_id=current_user.class_id, section_id=current_user.section_id
        )
        .order_by(Note.created_at.desc())
        .limit(20)
    ).all()
    open_reports = db.session.scalar(
        db.select(db.func.count(Report.id))
        .join(Note, Report.note_id == Note.id)
        .filter(
            Report.status == Report.STATUS_OPEN,
            Note.class_id == current_user.class_id,
            Note.section_id == current_user.section_id,
        )
    )
    return render_template(
        "teacher/class_dashboard.html",
        students=students,
        subjects=subjects,
        recent_notes=recent_notes,
        open_reports=open_reports,
    )


# ---------------- Moderation: reports ----------------


def _report_scope_or_403(report):
    note = report.note
    if not can_moderate_scope(current_user, note.class_id, note.section_id):
        abort(403)
    return note


@teacher_bp.route("/reports")
@roles_required(Role.CLASS_TEACHER)
def reports():
    show = request.args.get("show", "open")
    query = (
        db.select(Report)
        .join(Note, Report.note_id == Note.id)
        .order_by(Report.created_at.desc())
    )
    if show != "all":
        query = query.filter(Report.status == Report.STATUS_OPEN)
    if current_user.role == Role.CLASS_TEACHER:
        query = query.filter(
            Note.class_id == current_user.class_id,
            Note.section_id == current_user.section_id,
        )
    all_reports = db.session.scalars(query.limit(200)).all()
    return render_template("teacher/reports.html", reports=all_reports, show=show)


@teacher_bp.route("/reports/<int:report_id>/dismiss", methods=["POST"])
@roles_required(Role.CLASS_TEACHER)
def dismiss_report(report_id):
    report = db.get_or_404(Report, report_id)
    _report_scope_or_403(report)
    report.status = Report.STATUS_RESOLVED
    db.session.commit()
    flash("Report dismissed.", "success")
    return redirect(url_for("teacher.reports"))


@teacher_bp.route("/reports/<int:report_id>/hide-note", methods=["POST"])
@roles_required(Role.CLASS_TEACHER)
def hide_reported_note(report_id):
    report = db.get_or_404(Report, report_id)
    note = _report_scope_or_403(report)
    note.is_hidden = True
    report.status = Report.STATUS_RESOLVED
    db.session.commit()
    flash("Note hidden from students. You can unhide it from the note page.", "success")
    return redirect(url_for("teacher.reports"))


@teacher_bp.route("/note/<int:note_id>/unhide", methods=["POST"])
@roles_required(Role.CLASS_TEACHER)
def unhide_note(note_id):
    note = db.get_or_404(Note, note_id)
    if not can_moderate_scope(current_user, note.class_id, note.section_id):
        abort(403)
    note.is_hidden = False
    db.session.commit()
    flash("Note is visible to students again.", "success")
    return redirect(url_for("notes.view_note", note_id=note.id))


@teacher_bp.route("/reports/<int:report_id>/delete-note", methods=["POST"])
@roles_required(Role.CLASS_TEACHER)
def delete_reported_note(report_id):
    report = db.get_or_404(Report, report_id)
    note = _report_scope_or_403(report)
    delete_note_files(note, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(note)  # cascades to images, votes, and its reports
    db.session.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("teacher.reports"))


@teacher_bp.route("/class/student/new", methods=["GET", "POST"])
@roles_required(Role.CLASS_TEACHER)
def create_student():
    """Chain of command (spec §3): a class teacher issues roll-based student
    logins for their OWN class+section only — the scope is forced server-side,
    never taken from the form."""
    if current_user.role != Role.CLASS_TEACHER:
        # Super admin passing through the decorator has no own section;
        # send them to the full admin form instead.
        return redirect(url_for("admin.create_user"))
    if current_user.class_id is None or current_user.section_id is None:
        abort(403)

    form = CreateStudentForm()
    if form.validate_on_submit():
        login_id = form.login_id.data.strip()
        if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
            flash("That login ID is already taken.", "error")
            return render_template("teacher/create_student.html", form=form)
        student = User(
            login_id=login_id,
            full_name=form.full_name.data.strip(),
            role=Role.STUDENT,
            class_id=current_user.class_id,
            section_id=current_user.section_id,
            must_change_password=True,
        )
        student.set_password(form.password.data)
        db.session.add(student)
        db.session.commit()
        flash(
            f"Student '{student.full_name}' created with login ID '{login_id}'. "
            "They must change the password on first login.",
            "success",
        )
        return redirect(url_for("teacher.class_dashboard"))
    return render_template("teacher/create_student.html", form=form)


@teacher_bp.route(
    "/class/student/<int:student_id>/reset-password", methods=["GET", "POST"]
)
@roles_required(Role.CLASS_TEACHER)
def reset_student_password(student_id):
    student = db.get_or_404(User, student_id)
    if student.role != Role.STUDENT:
        abort(403)
    if current_user.role == Role.CLASS_TEACHER and (
        student.class_id != current_user.class_id
        or student.section_id != current_user.section_id
    ):
        abort(403)
    form = ResetStudentPasswordForm()
    if form.validate_on_submit():
        student.set_password(form.new_password.data)
        student.must_change_password = True
        db.session.commit()
        flash(
            f"Password reset for {student.full_name}. They must change it on "
            "next login.",
            "success",
        )
        return redirect(url_for("teacher.class_dashboard"))
    return render_template(
        "teacher/reset_student_password.html", form=form, student=student
    )
