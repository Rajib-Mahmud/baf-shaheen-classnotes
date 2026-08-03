"""Role and scope checks.

Every rule here is enforced server-side on every request. UI hiding is
never relied upon for protection.
"""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from ..models import Role


def roles_required(*roles):
    """Allow only the given roles (Super Admin always passes)."""

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role == Role.SUPER_ADMIN:
                return fn(*args, **kwargs)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def can_view_scope(user, class_id, section_id):
    """Can `user` read content belonging to class_id/section_id?

    - Super Admin: everything.
    - Class Teacher / Student: only their own class+section.
    - Subject Teacher: any class+section where they have an assigned subject.
    """
    if user.role == Role.SUPER_ADMIN:
        return True
    if user.role in (Role.STUDENT, Role.CLASS_TEACHER):
        return user.class_id == class_id and user.section_id == section_id
    if user.role == Role.SUBJECT_TEACHER:
        return any(
            s.class_id == class_id and s.section_id == section_id
            for s in user.taught_subjects
        )
    return False


def require_view_scope(class_id, section_id):
    if not can_view_scope(current_user, class_id, section_id):
        abort(403)


def can_upload_to_chapter(user, chapter):
    """Can `user` create a note under `chapter`?

    - Super Admin: yes.
    - Subject Teacher: only chapters of subjects assigned to them.
    - Student: any chapter within their own class+section.
    - Class Teacher: no (they moderate, not upload).
    """
    subject = chapter.subject
    if user.role == Role.SUPER_ADMIN:
        return True
    if user.role == Role.SUBJECT_TEACHER:
        return subject.teacher_id == user.id
    if user.role == Role.STUDENT:
        return (
            user.class_id == subject.class_id
            and user.section_id == subject.section_id
        )
    return False


def can_manage_note(user, note):
    """Edit/delete rights: owner, Super Admin, or the Class Teacher of the
    note's class+section (moderation)."""
    if user.role == Role.SUPER_ADMIN:
        return True
    if note.uploader_id == user.id:
        return True
    if user.role == Role.CLASS_TEACHER:
        return (
            user.class_id == note.class_id and user.section_id == note.section_id
        )
    return False


def can_moderate_scope(user, class_id, section_id):
    """Moderation rights (reports, hidden notes): Super Admin everywhere,
    Class Teacher within their own class+section."""
    if user.role == Role.SUPER_ADMIN:
        return True
    return (
        user.role == Role.CLASS_TEACHER
        and user.class_id == class_id
        and user.section_id == section_id
    )


def owns_subject(user, subject):
    """Is `user` the assigned subject teacher (or Super Admin)?"""
    if user.role == Role.SUPER_ADMIN:
        return True
    return user.role == Role.SUBJECT_TEACHER and subject.teacher_id == user.id
