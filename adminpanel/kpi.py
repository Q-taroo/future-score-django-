"""KPI Dashboard queries (spec §27).

DAU/WAU/MAU are approximated from AnalyticsEvent activity (any tracked
event counts as "active") since MVP has no dedicated session-tracking
table — good enough for an early product, and the abstraction
(core.services.analytics.track_event) means a real analytics warehouse
can replace this module later without changing the KPI page.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from core.models import AnalyticsEvent
from predictions.models import Prediction, PredictionStatus, UserPrediction

User = get_user_model()


def _days_ago(n: int):
    return timezone.now() - timedelta(days=n)


def _active_user_count(since_days: int) -> int:
    return AnalyticsEvent.objects.filter(created_at__gte=_days_ago(since_days), user__isnull=False).values(
        "user_id"
    ).distinct().count()


def _retention(days: int) -> float:
    cohort_cutoff = _days_ago(days)
    cohort_user_ids = list(User.objects.filter(date_joined__lte=cohort_cutoff).values_list("id", flat=True))
    if not cohort_user_ids:
        return 0.0
    active = (
        AnalyticsEvent.objects.filter(created_at__gte=_days_ago(days), user_id__in=cohort_user_ids)
        .values("user_id")
        .distinct()
        .count()
    )
    return active / len(cohort_user_ids)


def get_kpi_summary() -> dict:
    total_users = User.objects.count()
    total_votes = UserPrediction.objects.count()
    total_predictions = Prediction.objects.count()
    resolved_predictions = Prediction.objects.filter(status=PredictionStatus.RESOLVED).count()
    completion_rate = resolved_predictions / total_predictions if total_predictions else 0.0

    votes_by_category = {}
    for p in Prediction.objects.annotate(vote_count=Count("user_predictions")):
        votes_by_category[p.category] = votes_by_category.get(p.category, 0) + p.vote_count

    return {
        "dau": _active_user_count(1),
        "wau": _active_user_count(7),
        "mau": _active_user_count(30),
        "total_users": total_users,
        "total_votes": total_votes,
        "total_predictions": total_predictions,
        "resolved_predictions": resolved_predictions,
        "completion_rate": completion_rate,
        "retention_7d": _retention(7),
        "retention_30d": _retention(30),
        "votes_by_category": sorted(votes_by_category.items(), key=lambda kv: -kv[1]),
    }
