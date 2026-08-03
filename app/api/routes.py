"""JSON API for the React SPA.

Same-origin only: auth stays on the HttpOnly session cookie and every
mutating request must carry the X-CSRFToken header (Flask-WTF validates it
globally). Every scope/role rule is enforced here with the exact same
helpers the server-rendered views use.
"""

import csv
import io
import os
import secrets

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError

from ..auth.routes import LOGIN_PANELS, PANEL_FOR_ROLE, _DUMMY_HASH
from ..extensions import db, limiter
from ..models import (
    Chapter,
    Note,
    NoteDownload,
    NoteImage,
    NoteVote,
    Report,
    Role,
    SchoolClass,
    Section,
    Subject,
    User,
)
from ..utils.images import InvalidImageError, delete_note_files, process_upload
from ..utils.points import (
    POINTS_UPLOAD,
    POINTS_UPVOTE,
    award,
    leaderboard as leaderboard_query,
    tier_for,
    total_for,
)
from ..utils.security import (
    can_manage_note,
    can_moderate_scope,
    can_upload_to_chapter,
    can_view_scope,
    owns_subject,
)
from werkzeug.security import check_password_hash

api_bp = Blueprint("api", __name__)


def err(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def forbid():
    return err("You don't have access to that.", 403)


def user_json(u):
    data = {
        "id": u.id,
        "login_id": u.login_id,
        "full_name": u.full_name,
        "role": u.role,
        "role_label": u.role_label,
        "must_change_password": u.must_change_password,
        "is_active": u.is_active,
        "section_label": u.section.label if u.section else None,
        "class_id": u.class_id,
        "section_id": u.section_id,
    }
    return data


def note_json(n, detail=False):
    data = {
        "id": n.id,
        "title": n.title,
        "is_official": n.is_official,
        "is_hidden": n.is_hidden,
        "uploader": n.uploader.full_name,
        "uploader_id": n.uploader_id,
        "created_at": n.created_at.strftime("%d %b %Y"),
        "votes": len(n.votes),
        "pages": len(n.images),
        "thumb_image_id": n.images[0].id if n.images else None,
        "chapter_id": n.chapter_id,
    }
    if detail:
        data.update(
            {
                "description": n.description,
                "chapter_title": n.chapter.title,
                "subject_id": n.chapter.subject_id,
                "subject_name": n.chapter.subject.name,
                "created_at_full": n.created_at.strftime("%d %b %Y, %H:%M"),
                "images": [
                    {"id": img.id, "original_name": img.original_name}
                    for img in n.images
                ],
            }
        )
    return data


# ---------------- Auth ----------------


@api_bp.route("/csrf")
def csrf_token():
    return jsonify({"csrf_token": generate_csrf()})


@api_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 50 per hour")
def login():
    body = request.get_json(silent=True) or {}
    panel = body.get("panel", "student")
    if panel not in LOGIN_PANELS:
        return err("Unknown login panel.")
    user = db.session.scalar(
        db.select(User).filter_by(login_id=(body.get("login_id") or "").strip())
    )
    password = body.get("password") or ""
    if user is None:
        check_password_hash(_DUMMY_HASH, password)
        password_ok = False
    else:
        password_ok = user.check_password(password)
    if user is None or not user.is_active or not password_ok:
        return err("Invalid ID or password.", 401)
    if user.role not in LOGIN_PANELS[panel]["roles"]:
        correct = PANEL_FOR_ROLE[user.role]
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"This account belongs to the "
                    f"{LOGIN_PANELS[correct]['title']} — use that panel.",
                    "correct_panel": correct,
                }
            ),
            403,
        )
    session.clear()
    login_user(user)
    return jsonify(
        {"ok": True, "user": user_json(user), "csrf_token": generate_csrf()}
    )


@api_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@api_bp.route("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"user": None, "csrf_token": generate_csrf()})
    return jsonify(
        {"user": user_json(current_user), "csrf_token": generate_csrf()}
    )


@api_bp.route("/change-password", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def change_password():
    body = request.get_json(silent=True) or {}
    current = body.get("current_password") or ""
    new = body.get("new_password") or ""
    if not current_user.check_password(current):
        return err("Current password is incorrect.")
    if len(new) < 8:
        return err("New password must be at least 8 characters.")
    current_user.set_password(new)
    current_user.must_change_password = False
    db.session.commit()
    login_user(current_user._get_current_object())
    return jsonify({"ok": True, "user": user_json(current_user)})


def _require_password_changed():
    """Mirror of the HTML app's forced-change gate for data endpoints."""
    if current_user.is_authenticated and current_user.must_change_password:
        return err("Password change required.", 428)
    return None


@api_bp.before_request
def gate_password_change():
    exempt = {"api.login", "api.logout", "api.me", "api.csrf_token",
              "api.change_password"}
    if request.endpoint in exempt:
        return None
    if not current_user.is_authenticated:
        return None  # per-route @login_required responds properly
    return _require_password_changed()


# ---------------- Student / shared ----------------


@api_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == Role.STUDENT:
        subjects = db.session.scalars(
            db.select(Subject)
            .filter_by(
                class_id=current_user.class_id, section_id=current_user.section_id
            )
            .order_by(Subject.name)
        ).all()
        recent = db.session.scalars(
            db.select(Note)
            .filter_by(
                class_id=current_user.class_id,
                section_id=current_user.section_id,
                is_hidden=False,
            )
            .order_by(Note.created_at.desc())
            .limit(8)
        ).all()
        points = total_for(current_user.id)
        tier_name, tier_css = tier_for(points)
        return jsonify(
            {
                "subjects": [
                    {"id": s.id, "name": s.name, "chapters": len(s.chapters)}
                    for s in subjects
                ],
                "recent_notes": [note_json(n) for n in recent],
                "points": points,
                "tier": tier_name,
                "tier_css": tier_css,
            }
        )
    return forbid()


@api_bp.route("/subject/<int:subject_id>")
@login_required
def subject(subject_id):
    s = db.get_or_404(Subject, subject_id)
    if not can_view_scope(current_user, s.class_id, s.section_id):
        return forbid()
    return jsonify(
        {
            "id": s.id,
            "name": s.name,
            "section_label": s.section.label,
            "teacher": s.teacher.full_name if s.teacher else None,
            "chapters": [
                {"id": c.id, "title": c.title, "order_index": c.order_index,
                 "notes": len(c.notes)}
                for c in s.chapters
            ],
        }
    )


@api_bp.route("/chapter/<int:chapter_id>")
@login_required
def chapter(chapter_id):
    c = db.get_or_404(Chapter, chapter_id)
    s = c.subject
    if not can_view_scope(current_user, s.class_id, s.section_id):
        return forbid()
    query = db.select(Note).filter_by(chapter_id=c.id)
    moderator = can_moderate_scope(current_user, s.class_id, s.section_id)
    if not moderator:
        query = query.filter_by(is_hidden=False)
    notes = db.session.scalars(
        query.order_by(Note.is_official.desc(), Note.created_at.desc())
    ).all()
    return jsonify(
        {
            "id": c.id,
            "title": c.title,
            "subject": {"id": s.id, "name": s.name},
            "can_upload": can_upload_to_chapter(current_user, c),
            "notes": [note_json(n) for n in notes],
        }
    )


@api_bp.route("/note/<int:note_id>")
@login_required
def note_detail(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_view_scope(current_user, n.class_id, n.section_id):
        return forbid()
    moderator = can_moderate_scope(current_user, n.class_id, n.section_id)
    if n.is_hidden and not moderator:
        return err("Not found.", 404)
    my_vote = (
        db.session.scalar(
            db.select(NoteVote).filter_by(
                note_id=n.id, voter_id=current_user.id
            )
        )
        is not None
    )
    reported = (
        db.session.scalar(
            db.select(Report).filter_by(
                note_id=n.id,
                reporter_id=current_user.id,
                status=Report.STATUS_OPEN,
            )
        )
        is not None
    )
    data = note_json(n, detail=True)
    data.update(
        {
            "my_vote": my_vote,
            "already_reported": reported,
            "can_manage": can_manage_note(current_user, n)
            and not (n.is_hidden and not moderator),
            "is_moderator": moderator,
            "report_reasons": Report.REASONS,
        }
    )
    return jsonify(data)


@api_bp.route("/note/<int:note_id>", methods=["PUT"])
@login_required
def edit_note(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_manage_note(current_user, n):
        return forbid()
    if n.is_hidden and not can_moderate_scope(
        current_user, n.class_id, n.section_id
    ):
        return forbid()
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return err("Title is required.")
    n.title = title[:160]
    n.description = (body.get("description") or "").strip()[:2000] or None
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/note/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_manage_note(current_user, n):
        return forbid()
    if n.is_hidden and not can_moderate_scope(
        current_user, n.class_id, n.section_id
    ):
        return forbid()
    chapter_id = n.chapter_id
    delete_note_files(n, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(n)
    db.session.commit()
    return jsonify({"ok": True, "chapter_id": chapter_id})


@api_bp.route("/note/<int:note_id>/vote", methods=["POST"])
@limiter.limit("30 per minute")
@login_required
def vote(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_view_scope(current_user, n.class_id, n.section_id):
        return forbid()
    if n.is_hidden:
        return err("Not found.", 404)
    if n.uploader_id == current_user.id:
        return err("You cannot upvote your own note.")
    existing = db.session.scalar(
        db.select(NoteVote).filter_by(note_id=n.id, voter_id=current_user.id)
    )
    if existing:
        db.session.delete(existing)
        award(n.uploader, -POINTS_UPVOTE, "upvote", n.id)
        voted = False
    else:
        db.session.add(NoteVote(note_id=n.id, voter_id=current_user.id))
        award(n.uploader, POINTS_UPVOTE, "upvote", n.id)
        voted = True
    db.session.commit()
    return jsonify({"ok": True, "voted": voted, "votes": len(n.votes)})


@api_bp.route("/note/<int:note_id>/report", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def report(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_view_scope(current_user, n.class_id, n.section_id):
        return forbid()
    if n.uploader_id == current_user.id:
        return forbid()
    body = request.get_json(silent=True) or {}
    reason = body.get("reason", "")
    if reason not in Report.REASONS:
        return err("Pick a reason for the report.")
    duplicate = db.session.scalar(
        db.select(Report).filter_by(
            note_id=n.id, reporter_id=current_user.id, status=Report.STATUS_OPEN
        )
    )
    if duplicate:
        return err("You already reported this note.")
    db.session.add(
        Report(
            note_id=n.id,
            reporter_id=current_user.id,
            reason=reason,
            comment=(body.get("comment") or "").strip()[:500] or None,
        )
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/upload-targets")
@login_required
def upload_targets():
    from ..notes.routes import _uploadable_chapters

    if current_user.role == Role.CLASS_TEACHER:
        return jsonify({"chapters": []})
    return jsonify(
        {
            "chapters": [
                {"id": cid, "label": label}
                for cid, label in _uploadable_chapters(current_user)
            ]
        }
    )


@api_bp.route("/upload", methods=["POST"])
@limiter.limit("30 per hour")
@login_required
def upload():
    if current_user.role == Role.CLASS_TEACHER:
        return forbid()
    chapter_id = request.form.get("chapter_id", type=int)
    title = (request.form.get("title") or "").strip()
    if not chapter_id or not title:
        return err("Chapter and title are required.")
    c = db.session.get(Chapter, chapter_id)
    if c is None:
        return err("Chapter not found.", 404)
    if not can_upload_to_chapter(current_user, c):
        return forbid()
    files = [f for f in request.files.getlist("images") if f and f.filename]
    if not files:
        return err("Choose at least one photo.")
    max_images = current_app.config["MAX_IMAGES_PER_NOTE"]
    if len(files) > max_images:
        return err(f"At most {max_images} photos per note.")

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    processed = []
    try:
        for f in files:
            processed.append(
                process_upload(
                    f,
                    upload_folder,
                    thumb_max=current_app.config["THUMBNAIL_MAX_SIZE"],
                    max_bytes=current_app.config["MAX_IMAGE_BYTES"],
                )
            )
    except InvalidImageError as exc:
        for stored, thumb, _ in processed:
            for name in (stored, thumb):
                try:
                    os.remove(os.path.join(upload_folder, name))
                except OSError:
                    pass
        return err(str(exc))

    s = c.subject
    note = Note(
        title=title[:160],
        description=(request.form.get("description") or "").strip()[:2000]
        or None,
        chapter_id=c.id,
        uploader_id=current_user.id,
        class_id=s.class_id,
        section_id=s.section_id,
        is_official=(
            current_user.role == Role.SUBJECT_TEACHER
            and s.teacher_id == current_user.id
        ),
    )
    db.session.add(note)
    db.session.flush()
    for stored, thumb, original in processed:
        db.session.add(
            NoteImage(
                note_id=note.id,
                file_path=stored,
                thumb_path=thumb,
                original_name=original[:256],
            )
        )
    award(current_user, POINTS_UPLOAD, "upload", note.id)
    db.session.commit()
    return jsonify({"ok": True, "note_id": note.id})


@api_bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()[:100]
    results = []
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        query = (
            db.select(Note)
            .join(Chapter, Note.chapter_id == Chapter.id)
            .join(Subject, Chapter.subject_id == Subject.id)
            .filter(
                db.or_(
                    Note.title.ilike(like, escape="\\"),
                    Subject.name.ilike(like, escape="\\"),
                    Chapter.title.ilike(like, escape="\\"),
                )
            )
            .order_by(Note.created_at.desc())
        )
        if current_user.role != Role.SUPER_ADMIN:
            query = query.filter(Note.is_hidden.is_(False))
        if current_user.role in (Role.STUDENT, Role.CLASS_TEACHER):
            query = query.filter(
                Note.class_id == current_user.class_id,
                Note.section_id == current_user.section_id,
            )
        elif current_user.role == Role.SUBJECT_TEACHER:
            pairs = [
                (s.class_id, s.section_id) for s in current_user.taught_subjects
            ] or [(-1, -1)]
            query = query.filter(
                db.or_(
                    *[
                        db.and_(Note.class_id == c_, Note.section_id == s_)
                        for c_, s_ in pairs
                    ]
                )
            )
        results = db.session.scalars(query.limit(100)).all()
    return jsonify({"q": q, "results": [note_json(n) for n in results]})


@api_bp.route("/leaderboard")
@login_required
def leaderboard():
    if current_user.role not in (Role.STUDENT, Role.CLASS_TEACHER):
        return forbid()
    if current_user.class_id is None or current_user.section_id is None:
        return forbid()
    rows = leaderboard_query(
        current_user.class_id, current_user.section_id, limit=10
    )
    my_points = total_for(current_user.id)
    tier_name, tier_css = tier_for(my_points)
    return jsonify(
        {
            "section_label": current_user.section.label,
            "my_points": my_points,
            "my_tier": tier_name,
            "my_tier_css": tier_css,
            "rows": [
                {
                    "id": u.id,
                    "full_name": u.full_name,
                    "login_id": u.login_id,
                    "points": pts,
                    "tier": tier_for(pts)[0],
                    "tier_css": tier_for(pts)[1],
                }
                for u, pts in rows
            ],
        }
    )


# ---------------- Subject teacher ----------------


@api_bp.route("/teacher/subjects")
@login_required
def teacher_subjects():
    if current_user.role == Role.SUPER_ADMIN:
        subjects = db.session.scalars(db.select(Subject)).all()
    elif current_user.role == Role.SUBJECT_TEACHER:
        subjects = db.session.scalars(
            db.select(Subject).filter_by(teacher_id=current_user.id)
        ).all()
    else:
        return forbid()
    return jsonify(
        {
            "subjects": [
                {
                    "id": s.id,
                    "name": s.name,
                    "section_label": s.section.label,
                    "chapters": len(s.chapters),
                }
                for s in subjects
            ]
        }
    )


@api_bp.route("/teacher/subject/<int:subject_id>/chapters", methods=["POST"])
@login_required
def create_chapter(subject_id):
    s = db.get_or_404(Subject, subject_id)
    if not owns_subject(current_user, s):
        return forbid()
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return err("Title is required.")
    ch = Chapter(
        title=title[:160],
        order_index=int(body.get("order_index") or 0),
        subject_id=s.id,
    )
    db.session.add(ch)
    db.session.commit()
    return jsonify({"ok": True, "id": ch.id})


@api_bp.route("/teacher/chapter/<int:chapter_id>", methods=["PUT", "DELETE"])
@login_required
def modify_chapter(chapter_id):
    ch = db.get_or_404(Chapter, chapter_id)
    if not owns_subject(current_user, ch.subject):
        return forbid()
    if request.method == "DELETE":
        if ch.notes:
            return err("Cannot delete: this chapter still has notes.")
        db.session.delete(ch)
        db.session.commit()
        return jsonify({"ok": True})
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return err("Title is required.")
    ch.title = title[:160]
    ch.order_index = int(body.get("order_index") or 0)
    db.session.commit()
    return jsonify({"ok": True})


# ---------------- Class teacher ----------------


def _class_teacher_only():
    if current_user.role == Role.SUPER_ADMIN:
        return None
    if current_user.role != Role.CLASS_TEACHER:
        return forbid()
    if current_user.class_id is None or current_user.section_id is None:
        return forbid()
    return None


@api_bp.route("/teacher/class")
@login_required
def class_dashboard():
    guard = _class_teacher_only()
    if guard:
        return guard
    if current_user.role == Role.SUPER_ADMIN:
        return forbid()  # admin uses /api/admin instead
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
    recent = db.session.scalars(
        db.select(Note)
        .filter_by(
            class_id=current_user.class_id, section_id=current_user.section_id
        )
        .order_by(Note.created_at.desc())
        .limit(12)
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
    return jsonify(
        {
            "section_label": current_user.section.label,
            "students": [user_json(u) for u in students],
            "subjects": [{"id": s.id, "name": s.name} for s in subjects],
            "recent_notes": [note_json(n) for n in recent],
            "open_reports": open_reports,
        }
    )


@api_bp.route("/teacher/class/students", methods=["POST"])
@login_required
def create_student():
    guard = _class_teacher_only()
    if guard:
        return guard
    if current_user.role != Role.CLASS_TEACHER:
        return forbid()
    body = request.get_json(silent=True) or {}
    login_id = (body.get("login_id") or "").strip()
    full_name = (body.get("full_name") or "").strip()
    password = body.get("password") or ""
    if not login_id or not full_name:
        return err("Login ID and full name are required.")
    if len(password) < 8:
        return err("Password must be at least 8 characters.")
    if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
        return err("That login ID is already taken.")
    student = User(
        login_id=login_id[:64],
        full_name=full_name[:120],
        role=Role.STUDENT,
        class_id=current_user.class_id,
        section_id=current_user.section_id,
        must_change_password=True,
    )
    student.set_password(password)
    db.session.add(student)
    db.session.commit()
    return jsonify({"ok": True, "user": user_json(student)})


@api_bp.route("/teacher/student/<int:student_id>/reset-password", methods=["POST"])
@login_required
def reset_student_password(student_id):
    student = db.get_or_404(User, student_id)
    if student.role != Role.STUDENT:
        return forbid()
    if current_user.role == Role.CLASS_TEACHER:
        if (
            student.class_id != current_user.class_id
            or student.section_id != current_user.section_id
        ):
            return forbid()
    elif current_user.role != Role.SUPER_ADMIN:
        return forbid()
    body = request.get_json(silent=True) or {}
    password = body.get("new_password") or ""
    if len(password) < 8:
        return err("Password must be at least 8 characters.")
    student.set_password(password)
    student.must_change_password = True
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/teacher/reports")
@login_required
def reports():
    if current_user.role not in (Role.CLASS_TEACHER, Role.SUPER_ADMIN):
        return forbid()
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
    items = db.session.scalars(query.limit(200)).all()
    return jsonify(
        {
            "reports": [
                {
                    "id": r.id,
                    "reason": r.reason,
                    "reason_label": r.reason_label,
                    "comment": r.comment,
                    "status": r.status,
                    "created_at": r.created_at.strftime("%d %b %Y, %H:%M"),
                    "reporter": r.reporter.full_name,
                    "note": note_json(r.note),
                    "note_section": r.note.chapter.subject.section.label,
                    "note_subject": r.note.chapter.subject.name,
                }
                for r in items
            ]
        }
    )


def _moderatable_report(report_id):
    r = db.get_or_404(Report, report_id)
    if not can_moderate_scope(
        current_user, r.note.class_id, r.note.section_id
    ):
        return None, forbid()
    return r, None


@api_bp.route("/teacher/reports/<int:report_id>/dismiss", methods=["POST"])
@login_required
def dismiss_report(report_id):
    r, guard = _moderatable_report(report_id)
    if guard:
        return guard
    r.status = Report.STATUS_RESOLVED
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/teacher/reports/<int:report_id>/hide-note", methods=["POST"])
@login_required
def hide_note(report_id):
    r, guard = _moderatable_report(report_id)
    if guard:
        return guard
    r.note.is_hidden = True
    r.status = Report.STATUS_RESOLVED
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/teacher/reports/<int:report_id>/delete-note", methods=["POST"])
@login_required
def delete_reported_note(report_id):
    r, guard = _moderatable_report(report_id)
    if guard:
        return guard
    note = r.note
    delete_note_files(note, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(note)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/teacher/note/<int:note_id>/unhide", methods=["POST"])
@login_required
def unhide_note(note_id):
    n = db.get_or_404(Note, note_id)
    if not can_moderate_scope(current_user, n.class_id, n.section_id):
        return forbid()
    n.is_hidden = False
    db.session.commit()
    return jsonify({"ok": True})


# ---------------- Super admin ----------------


def _admin_only():
    if current_user.role != Role.SUPER_ADMIN:
        return forbid()
    return None


@api_bp.route("/admin/overview")
@login_required
def admin_overview():
    guard = _admin_only()
    if guard:
        return guard
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
    classes = db.session.scalars(
        db.select(SchoolClass).order_by(SchoolClass.name)
    ).all()
    sections = db.session.scalars(
        db.select(Section).join(SchoolClass).order_by(SchoolClass.name, Section.name)
    ).all()
    subjects = db.session.scalars(
        db.select(Subject)
        .join(Section, Subject.section_id == Section.id)
        .join(SchoolClass, Subject.class_id == SchoolClass.id)
        .order_by(SchoolClass.name, Section.name, Subject.name)
    ).all()
    teachers = db.session.scalars(
        db.select(User)
        .filter_by(role=Role.SUBJECT_TEACHER, is_active=True)
        .order_by(User.full_name)
    ).all()
    return jsonify(
        {
            "stats": stats,
            "classes": [
                {"id": c.id, "name": c.name, "sections": len(c.sections)}
                for c in classes
            ],
            "sections": [
                {"id": s.id, "label": s.label, "class_id": s.class_id,
                 "name": s.name}
                for s in sections
            ],
            "subjects": [
                {
                    "id": s.id,
                    "name": s.name,
                    "section_id": s.section_id,
                    "section_label": s.section.label,
                    "teacher_id": s.teacher_id,
                    "teacher": s.teacher.full_name if s.teacher else None,
                    "chapters": len(s.chapters),
                }
                for s in subjects
            ],
            "teachers": [
                {"id": t.id, "full_name": t.full_name} for t in teachers
            ],
        }
    )


@api_bp.route("/admin/classes", methods=["POST"])
@login_required
def admin_create_class():
    guard = _admin_only()
    if guard:
        return guard
    name = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not name:
        return err("Name is required.")
    if db.session.scalar(db.select(SchoolClass).filter_by(name=name)):
        return err("That class already exists.")
    db.session.add(SchoolClass(name=name[:64]))
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/classes/<int:class_id>", methods=["DELETE"])
@login_required
def admin_delete_class(class_id):
    guard = _admin_only()
    if guard:
        return guard
    c = db.get_or_404(SchoolClass, class_id)
    in_use = db.session.scalar(
        db.select(db.func.count(User.id)).filter_by(class_id=class_id)
    ) or db.session.scalar(
        db.select(db.func.count(Note.id)).filter_by(class_id=class_id)
    )
    if in_use:
        return err("Cannot delete: users or notes still belong to this class.")
    db.session.delete(c)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/sections", methods=["POST"])
@login_required
def admin_create_section():
    guard = _admin_only()
    if guard:
        return guard
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    class_id = body.get("class_id")
    if not name or not class_id:
        return err("Name and class are required.")
    if db.session.get(SchoolClass, class_id) is None:
        return err("Class not found.", 404)
    if db.session.scalar(
        db.select(Section).filter_by(class_id=class_id, name=name)
    ):
        return err("That section already exists in this class.")
    db.session.add(Section(name=name[:32], class_id=class_id))
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/sections/<int:section_id>", methods=["DELETE"])
@login_required
def admin_delete_section(section_id):
    guard = _admin_only()
    if guard:
        return guard
    s = db.get_or_404(Section, section_id)
    in_use = db.session.scalar(
        db.select(db.func.count(User.id)).filter_by(section_id=section_id)
    ) or db.session.scalar(
        db.select(db.func.count(Note.id)).filter_by(section_id=section_id)
    )
    if in_use:
        return err("Cannot delete: users or notes still belong to this section.")
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/subjects", methods=["POST"])
@login_required
def admin_create_subject():
    guard = _admin_only()
    if guard:
        return guard
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    section = db.session.get(Section, body.get("section_id") or 0)
    if not name or section is None:
        return err("Name and section are required.")
    if db.session.scalar(
        db.select(Subject).filter_by(section_id=section.id, name=name)
    ):
        return err("That subject already exists in this section.")
    teacher_id = body.get("teacher_id") or None
    if teacher_id:
        t = db.session.get(User, teacher_id)
        if t is None or t.role != Role.SUBJECT_TEACHER:
            return err("That user is not a subject teacher.")
    db.session.add(
        Subject(
            name=name[:64],
            class_id=section.class_id,
            section_id=section.id,
            teacher_id=teacher_id,
        )
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/subjects/<int:subject_id>", methods=["PUT", "DELETE"])
@login_required
def admin_modify_subject(subject_id):
    guard = _admin_only()
    if guard:
        return guard
    s = db.get_or_404(Subject, subject_id)
    if request.method == "DELETE":
        note_count = db.session.scalar(
            db.select(db.func.count(Note.id))
            .join(Chapter, Note.chapter_id == Chapter.id)
            .filter(Chapter.subject_id == subject_id)
        )
        if note_count:
            return err("Cannot delete: this subject still has notes.")
        db.session.delete(s)
        db.session.commit()
        return jsonify({"ok": True})
    body = request.get_json(silent=True) or {}
    teacher_id = body.get("teacher_id") or None
    if teacher_id:
        t = db.session.get(User, teacher_id)
        if t is None or t.role != Role.SUBJECT_TEACHER:
            return err("That user is not a subject teacher.")
    s.teacher_id = teacher_id
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/users")
@login_required
def admin_users():
    guard = _admin_only()
    if guard:
        return guard
    role = request.args.get("role")
    query = db.select(User).order_by(User.role, User.login_id)
    if role in Role.ALL:
        query = query.filter_by(role=role)
    return jsonify(
        {"users": [user_json(u) for u in db.session.scalars(query).all()]}
    )


@api_bp.route("/admin/users", methods=["POST"])
@login_required
def admin_create_user():
    guard = _admin_only()
    if guard:
        return guard
    body = request.get_json(silent=True) or {}
    login_id = (body.get("login_id") or "").strip()
    full_name = (body.get("full_name") or "").strip()
    role = body.get("role")
    password = body.get("password") or ""
    if role not in (Role.STUDENT, Role.CLASS_TEACHER, Role.SUBJECT_TEACHER):
        return err("Invalid role.")
    if not login_id or not full_name:
        return err("Login ID and full name are required.")
    if len(password) < 8:
        return err("Password must be at least 8 characters.")
    if db.session.scalar(db.select(User).filter_by(login_id=login_id)):
        return err("That login ID is already taken.")
    section = None
    if body.get("section_id"):
        section = db.session.get(Section, body["section_id"])
    if role in (Role.STUDENT, Role.CLASS_TEACHER) and section is None:
        return err("Students and class teachers need a class & section.")
    user = User(
        login_id=login_id[:64],
        full_name=full_name[:120],
        role=role,
        class_id=section.class_id if section else None,
        section_id=section.id if section else None,
        must_change_password=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True, "user": user_json(user)})


@api_bp.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
def admin_toggle_active(user_id):
    guard = _admin_only()
    if guard:
        return guard
    u = db.get_or_404(User, user_id)
    if u.id == current_user.id:
        return err("You cannot deactivate your own account.")
    u.is_active = not u.is_active
    db.session.commit()
    return jsonify({"ok": True, "is_active": u.is_active})


@api_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
def admin_reset_password(user_id):
    guard = _admin_only()
    if guard:
        return guard
    u = db.get_or_404(User, user_id)
    body = request.get_json(silent=True) or {}
    password = body.get("new_password") or ""
    if len(password) < 8:
        return err("Password must be at least 8 characters.")
    u.set_password(password)
    u.must_change_password = True
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/admin/import-students", methods=["POST"])
@login_required
def admin_import_students():
    guard = _admin_only()
    if guard:
        return guard
    section = db.session.get(Section, request.form.get("section_id", type=int) or 0)
    if section is None:
        return err("Section is required.")
    file = request.files.get("csv_file")
    if file is None or not (file.filename or "").lower().endswith(".csv"):
        return err("A .csv file is required.")
    try:
        text = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return err("CSV must be UTF-8 encoded.")
    created, errors = [], []
    for lineno, row in enumerate(csv.reader(io.StringIO(text)), start=1):
        row = [cell.strip() for cell in row]
        if not row or not any(row):
            continue
        if lineno == 1 and row[0].lower() in ("login_id", "roll", "id"):
            continue
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
            login_id=login_id[:64],
            full_name=full_name[:120],
            role=Role.STUDENT,
            class_id=section.class_id,
            section_id=section.id,
            must_change_password=True,
        )
        student.set_password(password)
        db.session.add(student)
        db.session.flush()
        created.append(
            {"login_id": login_id, "full_name": full_name, "password": password}
        )
    db.session.commit()
    return jsonify({"ok": True, "created": created, "errors": errors})
