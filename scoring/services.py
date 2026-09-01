"""DB-touching adapters around the pure logic in scoring.pure."""

from core.models import Notification
from scoring.models import Badge, UserBadge, UserStats
from scoring.pure import RankableUser, build_ranking, determine_rank_badges


def grant_badges(user, codes: list[str]) -> None:
    """Idempotently grants the given badge codes to a user — the unique
    constraint on (user, badge) makes re-granting an already-earned badge
    a no-op — and files a BADGE_EARNED notification for newly-earned
    ones."""
    if not codes:
        return

    badges = Badge.objects.filter(code__in=codes)
    existing_ids = set(UserBadge.objects.filter(user=user, badge__in=badges).values_list("badge_id", flat=True))

    for badge in badges:
        if badge.id in existing_ids:
            continue
        UserBadge.objects.create(user=user, badge=badge)
        Notification.objects.create(
            user=user,
            type=Notification.NotificationType.BADGE_EARNED,
            title="新しいバッジを獲得しました",
            body=f"「{badge.name}」バッジを獲得しました。",
        )


def refresh_ranking(min_predictions: int = 10) -> None:
    """Recomputes every user's overall_rank from current UserStats using
    the pure build_ranking() sort, then awards any newly-applicable
    rank-tier badges (TOP_100/TOP_10/TOP_1). Safe to call as often as
    needed — a full deterministic recompute, not an incremental patch."""
    all_stats = list(UserStats.objects.select_related("user").all())

    ranked = build_ranking(
        [
            RankableUser(
                user_id=s.user_id,
                prediction_score=s.prediction_score,
                accuracy=s.accuracy,
                total_predictions=s.total_predictions,
                current_streak=s.current_streak,
            )
            for s in all_stats
        ],
        min_predictions=min_predictions,
    )
    rank_by_user = {r.user_id: r.rank for r in ranked}

    for stats in all_stats:
        rank = rank_by_user.get(stats.user_id)
        if stats.overall_rank != rank:
            stats.overall_rank = rank
            stats.save(update_fields=["overall_rank"])
        if rank is not None:
            grant_badges(stats.user, determine_rank_badges(rank))
