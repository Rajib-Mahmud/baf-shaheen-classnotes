import hashlib
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Role:
    SUPER_ADMIN = "super_admin"
    CLASS_TEACHER = "class_teacher"
    SUBJECT_TEACHER = "subject_teacher"
    STUDENT = "student"

    ALL = (SUPER_ADMIN, CLASS_TEACHER, SUBJECT_TEACHER, STUDENT)

    LABELS = {
        SUPER_ADMIN: "Super Admin",
        CLASS_TEACHER: "Class Teacher",
        SUBJECT_TEACHER: "Subject Teacher",
        STUDENT: "Student",
    }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    school_class = db.relationship("SchoolClass", foreign_keys=[class_id])
    section = db.relationship("Section", foreign_keys=[section_id])
    taught_subjects = db.relationship(
        "Subject", back_populates="teacher", foreign_keys="Subject.teacher_id"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def session_key(self):
        """One-way digest of the password hash. Changes whenever the password
        does, without exposing hash material in the (readable, signed)
        session cookie."""
        return hashlib.sha256(self.password_hash.encode()).hexdigest()[:16]

    def get_id(self):
        # Binding the session to the password means every password change or
        # admin reset invalidates all of this user's existing sessions.
        return f"{self.id}.{self.session_key}"

    @property
    def role_label(self):
        return Role.LABELS.get(self.role, self.role)

    def __repr__(self):
        return f"<User {self.login_id} ({self.role})>"


class SchoolClass(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    sections = db.relationship(
        "Section", back_populates="school_class", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Class {self.name}>"


class Section(db.Model):
    __tablename__ = "sections"
    __table_args__ = (db.UniqueConstraint("class_id", "name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)

    school_class = db.relationship("SchoolClass", back_populates="sections")
    subjects = db.relationship(
        "Subject", back_populates="section", cascade="all, delete-orphan"
    )

    @property
    def label(self):
        return f"{self.school_class.name} — {self.name}"

    def __repr__(self):
        return f"<Section {self.label}>"


class Subject(db.Model):
    __tablename__ = "subjects"
    __table_args__ = (db.UniqueConstraint("section_id", "name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    school_class = db.relationship("SchoolClass", foreign_keys=[class_id])
    section = db.relationship(
        "Section", back_populates="subjects", foreign_keys=[section_id]
    )
    teacher = db.relationship(
        "User", back_populates="taught_subjects", foreign_keys=[teacher_id]
    )
    chapters = db.relationship(
        "Chapter",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )

    def __repr__(self):
        return f"<Subject {self.name}>"


class Chapter(db.Model):
    __tablename__ = "chapters"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)

    subject = db.relationship("Subject", back_populates="chapters")
    notes = db.relationship(
        "Note", back_populates="chapter", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chapter {self.title}>"


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Denormalised from the chapter's subject for fast per-request scope checks.
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    is_official = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    chapter = db.relationship("Chapter", back_populates="notes")
    uploader = db.relationship("User", foreign_keys=[uploader_id])
    images = db.relationship(
        "NoteImage",
        back_populates="note",
        cascade="all, delete-orphan",
        order_by="NoteImage.id",
    )
    votes = db.relationship(
        "NoteVote", back_populates="note", cascade="all, delete-orphan"
    )
    downloads = db.relationship(
        "NoteDownload", back_populates="note", cascade="all, delete-orphan"
    )
    reports = db.relationship(
        "Report", back_populates="note", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Note {self.title}>"


class NoteVote(db.Model):
    """One upvote per user per note."""

    __tablename__ = "note_votes"
    __table_args__ = (db.UniqueConstraint("note_id", "voter_id"),)

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    note = db.relationship("Note", back_populates="votes")
    voter = db.relationship("User", foreign_keys=[voter_id])


class NoteDownload(db.Model):
    """First download of a note per user — dedups download points."""

    __tablename__ = "note_downloads"
    __table_args__ = (db.UniqueConstraint("note_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    note = db.relationship("Note", back_populates="downloads")


class PointsLog(db.Model):
    __tablename__ = "points_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(20), nullable=False)  # upload | upvote | download
    ref_id = db.Column(db.Integer, nullable=True)  # note id the points relate to
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", foreign_keys=[user_id])


class Report(db.Model):
    __tablename__ = "reports"

    REASONS = {
        "wrong_info": "Wrong information",
        "inappropriate": "Inappropriate",
        "unreadable": "Unreadable / broken",
        "other": "Other",
    }
    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(10), nullable=False, default=STATUS_OPEN)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    note = db.relationship("Note", back_populates="reports")
    reporter = db.relationship("User", foreign_keys=[reporter_id])

    @property
    def reason_label(self):
        return self.REASONS.get(self.reason, self.reason)


class NoteImage(db.Model):
    __tablename__ = "note_images"

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable=False)
    file_path = db.Column(db.String(256), nullable=False)
    thumb_path = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    note = db.relationship("Note", back_populates="images")

    def __repr__(self):
        return f"<NoteImage {self.file_path}>"
