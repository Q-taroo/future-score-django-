"""Analytics Service (spec §30).

Thin abstraction over "wherever analytics events end up." MVP writes to
Postgres (AnalyticsEvent); swapping to Segment/PostHog/BigQuery later
means changing this one function, not every call site. Never raises —
analytics must never break a user-facing request.
"""

import logging

from core.models import AnalyticsEvent

logger = logging.getLogger(__name__)

EVENT_NAMES = (
    "prediction_viewed",
    "prediction_started",
    "prediction_submitted",
    "prediction_resolved",
    "ranking_viewed",
    "profile_viewed",
    "signup_completed",
)


def track_event(name: str, *, user=None, session_id: str = "", metadata: dict | None = None) -> None:
    try:
        AnalyticsEvent.objects.create(
            name=name,
            user=user if user and user.is_authenticated else None,
            session_id=session_id or None,
            metadata=metadata or None,
        )
    except Exception:  # noqa: BLE001 - analytics is best-effort by design
        logger.exception("failed to record analytics event %s", name)
