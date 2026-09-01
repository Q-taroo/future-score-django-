from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Spec §22. MVP persists to DB only — no email/push delivery yet."""

    class NotificationType(models.TextChoices):
        PREDICTION_DEADLINE = "PREDICTION_DEADLINE", "予測締切"
        PREDICTION_RESOLVED = "PREDICTION_RESOLVED", "結果確定"
        RANKING_CHANGED = "RANKING_CHANGED", "ランキング変動"
        BADGE_EARNED = "BADGE_EARNED", "バッジ獲得"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    prediction = models.ForeignKey(
        "predictions.Prediction", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_read"])]
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """Every admin-facing mutation should write here (spec §23)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=64)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor"]),
        ]
        ordering = ["-created_at"]


class AnalyticsEvent(models.Model):
    """Spec §30. Thin abstraction: swap for Segment/PostHog/BigQuery later
    by changing only core.services.analytics.track_event()."""

    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events"
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["user"])]


class Subscription(models.Model):
    """Monetization-ready, not billed in MVP (spec §28)."""

    class Plan(models.TextChoices):
        FREE = "FREE", "FREE"
        PRO = "PRO", "PRO"
        PREMIUM = "PREMIUM", "PREMIUM"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
