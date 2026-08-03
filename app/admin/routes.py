import csv
import io
import secrets

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from ..extensions import db
from ..models import (
    Chapter,
    Note,
    Report,
    Role,
    SchoolClass,
    Section,
    Subject,
    User,
)
from ..utils.images import delete_note_files
from ..utils.security import roles_required
from .forms import (
    ClassForm,
    ResetPasswordForm,
    SectionForm,
    StudentCSVForm,
    SubjectForm,
    UserForm,
)

admin_bp = Blueprint("admin", __name__)

admin_only = roles_required()  # only Super Admin passes


def _section_choices():
    sections = db.session.scalars(
        db.select(Section).join(SchoolClass).order_by(SchoolClass.name, Section.name)
    ).all()
    return [(s.id, s.label) for s in sections]


def _teacher_choices():
    teachers = db.session.scalars(
        db.select(User)
        .filter_by(role=Role.SUBJECT_TEACHER, is_active=True)
        .order_by(User.full_name)
    ).all()
    return [(0, "— Unassigned —")] + [(t.id, t.full_name) for t in teachers]


@admin_bp.route("/")
@admin_only
def dashboard():
    stats = {
        "classes": db.session.scalar(db.select(db.func.count(SchoolClass.id))),
        "sections": db.session.scalar(db.select(db.func.count(Section.id))),
        "subjects": db.session.scalar(db.select(db.func.count(Subject.id))),
        "students": db.session.scalar(
            db.select(db.func.count(User.id)).filter_by(role=Role.STUDENT)
        ),
        "teachers": db.session.scalar(
            db.select(db.func.count(User.id)).filter(
                User.role.in_([Role.SUBJECT_TEACHER, Role.CLASS_TEACHER])
            )
        ),
        "notes": db.session.scalar(db.select(db.func.count(Note.id))),
        "open_reports": db.session.scalar(
            db.select(db.func.count(Report.id)).filter_by(
                status=Report.STATUS_OPEN
            )
        ),
    }
    return render_template("admin/dashboard.html", stats=stats)


# ---------------- Classes ----------------


@admin_bp.route("/classes", methods=["GET", "POST"])
@admin_only
def classes():
    form = ClassForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if db.session.scalar(db.select(SchoolClass).filter_by(name=name)):
            flash("That class already exists.", "error")
        else:
            db.session.add(SchoolClass(name=name))
            db.session.commit()
            flash(f"Class '{name}' created.", "success")
        return redirect(url_for("admin.classes"))
    all_classes = db.session.scalars(
        db.select(SchoolClass).order_by(SchoolClass.name)
    ).all()
    return render_template("admin/classes.html", form=form, classes=all_classes)


@admin_bp.route("/classes/<int:class_id>/delete", methods=["POST"])
@admin_only
def delete_class(class_id):
    school_class = db.get_or_404(SchoolClass, class_id)
    in_use = db.session.scalar(
        db.select(db.func.count(User.id)).filter_by(class_id=class_id)
    ) or db.session.scalar(
        db.select(db.func.count(Note.id)).filter_by(class_id=class_id)
    )
    if in_use:
        flash("Cannot delete: users or notes still belong to this class.", "error")
    else:
        db.session.delete(school_class)
        db.session.commit()
        flash("Class deleted.", "success")
    return redirect(url_for("admin.classes"))


# ---------------- Sections ----------------


@admin_bp.route("/sections", methods=["GET", "POST"])
@admin_only
def sections():
    form = SectionForm()
    form.class_id.choices = [
        (c.id, c.name)
        for c in db.session.scalars(
            db.select(SchoolClass).order_by(SchoolClass.name)
        ).all()
    ]
    if not form.class_id.choices:
        flash("Create a class first.", "error")
        return redirect(url_for("admin.classes"))
    if form.validate_on_submit():
        name = form.name.data.strip()
        exists = db.session.scalar(
            db.select(Section).filter_by(class_id=form.class_id.data, name=name)
        )
        if exists:
            flash("That section already exists in this class.", "error")
        else:
            db.session.add(Section(name=name, class_id=form.class_id.data))
            db.session.commit()
            flash(f"Section '{name}' created.", "success")
        return redirect(url_for("admin.sections"))
    all_sections = db.session.scalars(
        db.select(Section).join(SchoolClass).order_by(SchoolClass.name, Section.name)
    ).all()
    return render_template("admin/sections.html", form=form, sections=all_sections)


@admin_bp.route("/sections/<int:section_id>/delete", methods=["POST"])
@admin_only
def delete_section(section_id):
    section = db.get_or_404(Section, section_id)
    in_use = db.session.scalar(
        db.select(db.func.count(User.id)).filter_by(section_id=section_id)
    ) or db.session.scalar(
        db.select(db.func.count(Note.id)).filter_by(section_id=section_id)
    )
    if in_use:
        flash("Cannot delete: users or notes still belong to this section.", "error")
    else:
        db.session.delete(section)
        db.session.commit()
        flash("Section deleted.", "success")
    return redirect(url_for("admin.sections"))


# ---------------- Subjects ----------------


@admin_bp.route("/subjects", methods=["GET", "POST"])
@admin_only
def subjects():
    form = SubjectForm()
    form.section_id.choices = _section_choices()
    form.teacher_id.choices = _teacher_choices()
    if not form.section_id.choices:
        flash("Create a class and section first.", "error")
        return redirect(url_for("admin.sections"))
    if form.validate_on_submit():
        section = db.get_or_404(Section, form.section_id.data)
        name = form.name.data.strip()
        exists = db.session.scalar(
            db.select(Subject).filter_by(section_id=section.id, name=name)
        )
        if exists:
            flash("That subject already exists in this section.", "error")
        else:
            subject = Subject(
                name=name,
                class_id=section.class_id,
                section_id=section.id,
                teacher_id=form.teacher_id.data or None,
            )
            db.session.add(subject)
            db.session.commit()
            flash(f"Subject '{name}' created.", "success")
        return redirect(url_for("admin.subjects"))
    all_subjects = db.session.scalars(
        db.select(Subject)
        .join(Section, Subject.section_id == Section.id)
        .join(SchoolClass, Subject.class_id == SchoolClass.id)
        .order_by(SchoolClass.name, Section.name, Subject.name)
    ).all()
    return render_template("admin/subjects.html", form=form, subjects=all_subjects)


@admin_bp.route("/subjects/<int:subject_id>/assign", methods=["POST"])
@admin_only
def assign_teacher(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    teacher_id = request.form.get("teacher_id", type=int) or 0
    if teacher_id == 0:
        subject.teacher_id = None
    else:
        teacher = db.get_or_404(User, teacher_id)
        if teacher.role != Role.SUBJECT_TEACHER:
            flash("That user is not a subject teacher.", "error")
            return redirect(url_for("admin.subjects"))
        subject.teacher_id = teacher.id
    db.session.commit()
    flash("Teacher assignment updated.", "success")
    return redirect(url_for("admin.subjects"))


@admin_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@admin_only
def delete_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    note_count = db.session.scalar(
        db.select(db.func.count(Note.id))
        .join(Chapter, Note.chapter_id == Chapter.id)
        .filter(Chapter.subject_id == subject_id)
    )
    if note_count:
        flash("Cannot delete: this subject still has notes.", "error")
    else:
        db.session.delete(subject)
        db.session.commit()
        flash("Subject deleted.", "success")
    return redirect(url_for("admin.subjects"))


# ---------------- Users ----------------


@admin_bp.route("/users")
@admin_only
def users():
    role = request.args.get("role")
    query = db.select(User).order_by(User.role, User.login_id)
    if role in Role.ALL:
        query = query.filter_by(role=role)
    all_users = db.session.scalars(query).all()
    return render_template("admin/users.html", users=all_users, role_filter=role)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_only
def create_user():
    form = UserForm()
    form.section_id.choices = [(0, "— None —")] + _section_choices()
    if form.validate_on_submit():
        login_id = form.login_id.data.strip()
        if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
            flash("That login ID is already taken.", "error")
            return render_template("admin/create_user.html", form=form)

        role = form.role.data
        section = None
        if form.section_id.data:
            section = db.get_or_404(Section, form.section_id.data)
        if role in (Role.STUDENT, Role.CLASS_TEACHER) and section is None:
            flash("Students and class teachers need a class & section.", "error")
            return render_template("admin/create_user.html", form=form)

        user = User(
            login_id=login_id,
            full_name=form.full_name.data.strip(),
            role=role,
            class_id=section.class_id if section else None,
            section_id=section.id if section else None,
            must_change_password=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(
            f"{user.role_label} '{user.full_name}' created with login ID "
            f"'{login_id}'. They must change the password on first login.",
            "success",
        )
        return redirect(url_for("admin.users"))
    return render_template("admin/create_user.html", form=form)


@admin_bp.route("/users/import", methods=["GET", "POST"])
@admin_only
def import_students():
    """Bulk CSV import. Columns: login_id, full_name[, password].
    Missing passwords are generated and shown once in the result."""
    form = StudentCSVForm()
    form.section_id.choices = _section_choices()
    if not form.section_id.choices:
        flash("Create a class and section first.", "error")
        return redirect(url_for("admin.sections"))
    if form.validate_on_submit():
        section = db.get_or_404(Section, form.section_id.data)
        raw = form.csv_file.data.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            flash("CSV too large (max 2 MB).", "error")
            return render_template("admin/import_students.html", form=form)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            flash("CSV must be UTF-8 encoded.", "error")
            return render_template("admin/import_students.html", form=form)

        created, errors = [], []
        reader = csv.reader(io.StringIO(text))
        for lineno, row in enumerate(reader, start=1):
            row = [cell.strip() for cell in row]
            if not row or not any(row):
                continue
            if lineno == 1 and row[0].lower() in ("login_id", "roll", "id"):
                continue  # header row
            if len(row) < 2 or not row[0] or not row[1]:
                errors.append(f"Line {lineno}: need at least login_id, full_name.")
                continue
            login_id, full_name = row[0], row[1]
            password = row[2] if len(row) > 2 and row[2] else secrets.token_urlsafe(8)
            if len(password) < 8:
                errors.append(f"Line {lineno}: password shorter than 8 characters.")
                continue
            if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
                errors.append(f"Line {lineno}: login ID '{login_id}' already taken.")
                continue
            student = User(
                login_id=login_id,
                full_name=full_name,
                role=Role.STUDENT,
                class_id=section.class_id,
                section_id=section.id,
                must_change_password=True,
            )
            student.set_password(password)
            db.session.add(student)
            db.session.flush()
            created.append((login_id, full_name, password))

        db.session.commit()
        return render_template(
            "admin/import_result.html",
            created=created,
            errors=errors,
            section=section,
        )
    return render_template("admin/import_students.html", form=form)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_only
def toggle_active(user_id):
    from flask_login import current_user

    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        state = "activated" if user.is_active else "deactivated"
        flash(f"'{user.full_name}' {state}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@admin_only
def reset_password(user_id):
    user = db.get_or_404(User, user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        user.must_change_password = True
        db.session.commit()
        flash(
            f"Password reset for '{user.full_name}'. They must change it on "
            "next login.",
            "success",
        )
        return redirect(url_for("admin.users"))
    return render_template("admin/reset_password.html", form=form, user=user)


@admin_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@admin_only
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    delete_note_files(note, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "success")
    # Never redirect to the (attacker-controllable) Referer header.
    return redirect(url_for("admin.dashboard"))
