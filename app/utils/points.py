"""Point system (Phase 2).

Rules (spec §9): +10 per upload, +2 per upvote received, +1 per unique
download of your note. Only students earn points; teachers' official notes
stay out of the leaderboard.
"""

from ..extensions import db
from ..models import PointsLog, Role, User

POINTS_UPLOAD = 10
POINTS_UPVOTE = 2
POINTS_DOWNLOAD = 1

# (min points, tier name, badge colour classes)
TIERS = [
    (300, "Champion", "bg-amber-100 text-amber-800"),
    (150, "Achiever", "bg-violet-100 text-violet-800"),
    (50, "Contributor", "bg-sky-100 text-sky-800"),
    (0, "Newcomer", "bg-slate-100 text-slate-600"),
]


def award(user, points, reason, ref_id=None):
    """Add a points entry for a student. No-op for other roles.
    Caller commits."""
    if user is None or user.role != Role.STUDENT or points == 0:
        return
    db.session.add(
        PointsLog(user_id=user.id, points=points, reason=reason, ref_id=ref_id)
    )


def total_for(user_id):
    return (
        db.session.scalar(
            db.select(db.func.coalesce(db.func.sum(PointsLog.points), 0)).filter(
                PointsLog.user_id == user_id
            )
        )
        or 0
    )


def tier_for(points):
    """Returns (name, css_classes) for a point total."""
    for threshold, name, css in TIERS:
        if points >= threshold:
            return name, css
    return TIERS[-1][1], TIERS[-1][2]


def leaderboard(class_id, section_id, limit=10):
    """Top student contributors of a class+section: [(User, points), ...]."""
    total = db.func.coalesce(db.func.sum(PointsLog.points), 0).label("total")
    rows = db.session.execute(
        db.select(User, total)
        .join(PointsLog, PointsLog.user_id == User.id)
        .filter(
            User.role == Role.STUDENT,
            User.class_id == class_id,
            User.section_id == section_id,
            User.is_active.is_(True),
        )
        .group_by(User.id)
        .order_by(total.desc(), User.full_name)
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]
