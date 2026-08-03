import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

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
)
from ..utils.images import (
    MIME_BY_EXT,
    InvalidImageError,
    delete_note_files,
    process_upload,
)
from ..utils.points import POINTS_DOWNLOAD, POINTS_UPLOAD, POINTS_UPVOTE, award
from ..utils.security import (
    can_manage_note,
    can_moderate_scope,
    can_upload_to_chapter,
    can_view_scope,
    require_view_scope,
)
from .forms import NoteEditForm, NoteUploadForm

notes_bp = Blueprint("notes", __name__)


def _uploadable_chapters(user):
    """Chapters the current user may upload into, grouped for the select."""
    if user.role == Role.SUBJECT_TEACHER:
        subjects = db.session.scalars(
            db.select(Subject).filter_by(teacher_id=user.id)
        ).all()
    elif user.role == Role.STUDENT:
        subjects = db.session.scalars(
            db.select(Subject)
            .filter_by(class_id=user.class_id, section_id=user.section_id)
            .order_by(Subject.name)
        ).all()
    elif user.role == Role.SUPER_ADMIN:
        subjects = db.session.scalars(db.select(Subject)).all()
    else:
        subjects = []
    chapters = []
    for subject in subjects:
        for chapter in subject.chapters:
            label = f"{subject.name} — {chapter.title}"
            if user.role in (Role.SUPER_ADMIN, Role.SUBJECT_TEACHER):
                label = f"{subject.section.label} · {label}"
            chapters.append((chapter.id, label))
    return chapters


@notes_bp.route("/upload", methods=["GET", "POST"])
@notes_bp.route("/teacher/upload", methods=["GET", "POST"], endpoint="teacher_upload")
@limiter.limit("30 per hour", methods=["POST"])  # caps disk-fill abuse
@login_required
def upload():
    if current_user.role == Role.CLASS_TEACHER:
        abort(403)
    form = NoteUploadForm()
    form.chapter_id.choices = _uploadable_chapters(current_user)
    if not form.chapter_id.choices:
        flash("No chapters available to upload into yet.", "error")
        return redirect(url_for("student.dashboard"))

    if request.method == "GET":
        preselect = request.args.get("chapter", type=int)
        if preselect and any(preselect == c[0] for c in form.chapter_id.choices):
            form.chapter_id.data = preselect

    if form.validate_on_submit():
        chapter = db.get_or_404(Chapter, form.chapter_id.data)
        if not can_upload_to_chapter(current_user, chapter):
            abort(403)

        files = [f for f in form.images.data if f and f.filename]
        max_images = current_app.config["MAX_IMAGES_PER_NOTE"]
        if len(files) > max_images:
            flash(f"At most {max_images} photos per note.", "error")
            return render_template("notes/upload.html", form=form)

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
            # Roll back any files already written for this note.
            for stored, thumb, _ in processed:
                for name in (stored, thumb):
                    try:
                        os.remove(os.path.join(upload_folder, name))
                    except OSError:
                        pass
            flash(str(exc), "error")
            return render_template("notes/upload.html", form=form)

        subject = chapter.subject
        is_official = (
            current_user.role == Role.SUBJECT_TEACHER
            and subject.teacher_id == current_user.id
        )
        note = Note(
            title=form.title.data.strip(),
            description=(form.description.data or "").strip() or None,
            chapter_id=chapter.id,
            uploader_id=current_user.id,
            class_id=subject.class_id,
            section_id=subject.section_id,
            is_official=is_official,
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
        flash("Note uploaded.", "success")
        return redirect(url_for("notes.view_note", note_id=note.id))

    return render_template("notes/upload.html", form=form)


@notes_bp.route("/note/<int:note_id>")
@login_required
def view_note(note_id):
    note = db.get_or_404(Note, note_id)
    require_view_scope(note.class_id, note.section_id)
    is_moderator = can_moderate_scope(current_user, note.class_id, note.section_id)
    if note.is_hidden and not is_moderator:
        abort(404)
    my_vote = db.session.scalar(
        db.select(NoteVote).filter_by(note_id=note.id, voter_id=current_user.id)
    )
    already_reported = db.session.scalar(
        db.select(Report).filter_by(
            note_id=note.id, reporter_id=current_user.id, status=Report.STATUS_OPEN
        )
    )
    return render_template(
        "notes/view.html",
        note=note,
        can_manage=can_manage_note(current_user, note),
        is_moderator=is_moderator,
        my_vote=my_vote is not None,
        already_reported=already_reported is not None,
        report_reasons=Report.REASONS,
    )


@notes_bp.route("/note/<int:note_id>/vote", methods=["POST"])
@limiter.limit("30 per minute")
@login_required
def vote_note(note_id):
    note = db.get_or_404(Note, note_id)
    require_view_scope(note.class_id, note.section_id)
    if note.is_hidden:
        abort(404)
    if note.uploader_id == current_user.id:
        flash("You cannot upvote your own note.", "error")
        return redirect(url_for("notes.view_note", note_id=note.id))

    existing = db.session.scalar(
        db.select(NoteVote).filter_by(note_id=note.id, voter_id=current_user.id)
    )
    if existing:
        db.session.delete(existing)
        award(note.uploader, -POINTS_UPVOTE, "upvote", note.id)
        flash("Upvote removed.", "success")
    else:
        db.session.add(NoteVote(note_id=note.id, voter_id=current_user.id))
        award(note.uploader, POINTS_UPVOTE, "upvote", note.id)
        flash("Upvoted!", "success")
    db.session.commit()
    return redirect(url_for("notes.view_note", note_id=note.id))


@notes_bp.route("/note/<int:note_id>/report", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def report_note(note_id):
    note = db.get_or_404(Note, note_id)
    require_view_scope(note.class_id, note.section_id)
    if note.uploader_id == current_user.id:
        abort(403)

    reason = request.form.get("reason", "")
    if reason not in Report.REASONS:
        flash("Pick a reason for the report.", "error")
        return redirect(url_for("notes.view_note", note_id=note.id))
    comment = (request.form.get("comment") or "").strip()[:500] or None

    duplicate = db.session.scalar(
        db.select(Report).filter_by(
            note_id=note.id, reporter_id=current_user.id, status=Report.STATUS_OPEN
        )
    )
    if duplicate:
        flash("You already reported this note — a teacher will review it.", "error")
        return redirect(url_for("notes.view_note", note_id=note.id))

    db.session.add(
        Report(
            note_id=note.id,
            reporter_id=current_user.id,
            reason=reason,
            comment=comment,
        )
    )
    db.session.commit()
    flash("Report submitted. Your class teacher will review it.", "success")
    return redirect(url_for("notes.view_note", note_id=note.id))


@notes_bp.route("/note/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    note = db.get_or_404(Note, note_id)
    if not can_manage_note(current_user, note):
        abort(403)
    # A note under moderation is frozen for its owner: only moderators may
    # touch it while hidden (prevents tampering with reported content).
    if note.is_hidden and not can_moderate_scope(
        current_user, note.class_id, note.section_id
    ):
        abort(403)
    form = NoteEditForm(obj=note)
    if form.validate_on_submit():
        note.title = form.title.data.strip()
        note.description = (form.description.data or "").strip() or None
        db.session.commit()
        flash("Note updated.", "success")
        return redirect(url_for("notes.view_note", note_id=note.id))
    return render_template("notes/edit.html", form=form, note=note)


@notes_bp.route("/note/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    if not can_manage_note(current_user, note):
        abort(403)
    if note.is_hidden and not can_moderate_scope(
        current_user, note.class_id, note.section_id
    ):
        abort(403)
    chapter_id = note.chapter_id
    delete_note_files(note, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("student.chapter", chapter_id=chapter_id))


@notes_bp.route("/image/<int:image_id>")
@login_required
def serve_image(image_id):
    """Scope-checked image serving. Files live outside the web root and are
    only ever streamed through this route."""
    image = db.get_or_404(NoteImage, image_id)
    note = image.note
    require_view_scope(note.class_id, note.section_id)
    if note.is_hidden and not can_moderate_scope(
        current_user, note.class_id, note.section_id
    ):
        abort(404)

    download = request.args.get("download") == "1"
    # +1 point to the uploader on another user's FIRST download of this note.
    if download and note.uploader_id != current_user.id:
        seen = db.session.scalar(
            db.select(NoteDownload).filter_by(
                note_id=note.id, user_id=current_user.id
            )
        )
        if not seen:
            try:
                db.session.add(
                    NoteDownload(note_id=note.id, user_id=current_user.id)
                )
                award(note.uploader, POINTS_DOWNLOAD, "download", note.id)
                db.session.commit()
            except IntegrityError:
                # Concurrent duplicate: the unique constraint already
                # guarantees the point was only awarded once.
                db.session.rollback()

    name = image.thumb_path if request.args.get("thumb") == "1" else image.file_path
    # Stored names are uuid-generated by us, but never trust a path anyway.
    if os.path.basename(name) != name:
        abort(404)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
    if not os.path.isfile(path):
        abort(404)

    ext = name.rsplit(".", 1)[-1].lower()
    mimetype = MIME_BY_EXT.get(ext, "application/octet-stream")
    response = send_file(
        path,
        mimetype=mimetype,
        as_attachment=download,
        download_name=image.original_name if download else None,
        conditional=True,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@notes_bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()[:100]
    results = []
    if q:
        # Escape LIKE wildcards so user input matches literally.
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
        # Hidden notes stay out of search except for Super Admin (class
        # teachers see them flagged on their own dashboard instead).
        if current_user.role != Role.SUPER_ADMIN:
            query = query.filter(Note.is_hidden.is_(False))
        # Scope the search to what the current user may see.
        if current_user.role in (Role.STUDENT, Role.CLASS_TEACHER):
            query = query.filter(
                Note.class_id == current_user.class_id,
                Note.section_id == current_user.section_id,
            )
        elif current_user.role == Role.SUBJECT_TEACHER:
            pairs = [
                (s.class_id, s.section_id) for s in current_user.taught_subjects
            ]
            if not pairs:
                pairs = [(-1, -1)]
            query = query.filter(
                db.or_(
                    *[
                        db.and_(Note.class_id == c, Note.section_id == s)
                        for c, s in pairs
                    ]
                )
            )
        results = db.session.scalars(query.limit(100)).all()
    return render_template("notes/search.html", q=q, results=results)
