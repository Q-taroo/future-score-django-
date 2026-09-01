from django.conf import settings
from django.db import models

from predictions.models import Prediction


class ScoreEventType(models.TextChoices):
    PREDICTION_CORRECT = "PREDICTION_CORRECT", "予測的中"
    PREDICTION_INCORRECT = "PREDICTION_INCORRECT", "予測不的中"
    BONUS = "BONUS", "ボーナス"
    ADJUSTMENT = "ADJUSTMENT", "調整"


class ScoreEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="score_events")
    prediction = models.ForeignKey(
        Prediction, null=True, blank=True, on_delete=models.SET_NULL, related_name="score_events"
    )
    type = models.CharField(max_length=25, choices=ScoreEventType.choices)
    points = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Belt-and-suspenders idempotency guard alongside the app-level
        # "already RESOLVED -> no-op" check in resolution.py: even if
        # resolution somehow ran twice, this constraint refuses to
        # double-insert a scoring event for the same user+prediction+type.
        constraints = [models.UniqueConstraint(fields=["user", "prediction", "type"], name="uniq_score_event")]
        indexes = [models.Index(fields=["user"])]


class UserStats(models.Model):
    """Denormalized, continuously-updated aggregate per user. Rebuilt by
    the Ranking/Resolution services; safe to fully recompute from
    ScoreEvent + UserPrediction at any time."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats")
    prediction_score = models.IntegerField(default=0)
    total_predictions = models.IntegerField(default=0)
    resolved_predictions = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0)
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    ai_beat_count = models.IntegerField(default=0)
    rating = models.CharField(max_length=2, default="C")
    overall_rank = models.PositiveIntegerField(null=True, blank=True)
    category_stats = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["prediction_score"])]


class BadgeCode(models.TextChoices):
    FIRST_PREDICTION = "FIRST_PREDICTION", "はじめての予測"
    PREDICTIONS_10 = "PREDICTIONS_10", "予測10回達成"
    PREDICTIONS_50 = "PREDICTIONS_50", "予測50回達成"
    PREDICTIONS_100 = "PREDICTIONS_100", "予測100回達成"
    STREAK_10 = "STREAK_10", "10連続的中"
    AI_KILLER = "AI_KILLER", "AI KILLER"
    TOP_100 = "TOP_100", "TOP 100"
    TOP_10 = "TOP_10", "TOP 10"
    TOP_1 = "TOP_1", "TOP 1"


class Badge(models.Model):
    code = models.CharField(max_length=20, choices=BadgeCode.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    icon = models.CharField(max_length=10, default="🏅")

    def __str__(self) -> str:
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="user_badges")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "badge"], name="uniq_user_badge")]
