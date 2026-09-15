from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Note, NoteVote
from app.utils.points import POINTS_UPVOTE, award
from app.utils.security import can_view_scope


class VoteError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status


def toggle_vote(user, note_id):
    """Returns (note, voted: bool, vote_count: int). Raises VoteError on any rejection."""
    note = db.session.get(Note, note_id)
    if note is None:
        raise VoteError("Not found.", 404)

    # Same status for out-of-scope AND hidden AND missing — no scope enumeration.
    if note.is_hidden or not can_view_scope(user, note.class_id, note.section_id):
        raise VoteError("Not found.", 404)

    if note.uploader_id == user.id:
        raise VoteError("You cannot upvote your own note.", 400)

    if note.uploader is None:
        raise VoteError("Note has no active uploader.", 409)

    # Row-level lock stops the concurrent-unvote double-award race.
    existing = db.session.scalar(
        db.select(NoteVote)
        .filter_by(note_id=note.id, voter_id=user.id)
        .with_for_update()
    )

    if existing:
        deleted = db.session.execute(
            db.delete(NoteVote).filter_by(id=existing.id)
        ).rowcount
        if deleted:
            award(note.uploader, -POINTS_UPVOTE, "upvote", note.id)
        voted = False
    else:
        try:
            db.session.add(
                NoteVote(
                    note_id=note.id,
                    voter_id=user.id,
                )
            )
            award(note.uploader, POINTS_UPVOTE, "upvote", note.id)
            db.session.flush()
            voted = True
        except IntegrityError:
            db.session.rollback()
            voted = True  # concurrent insert won

    db.session.commit()

    vote_count = db.session.scalar(
        db.select(db.func.count()).select_from(NoteVote).filter_by(note_id=note.id)
    ) or 0

    return note, voted, vote_count
