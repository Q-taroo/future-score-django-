"""PredictionResolver (spec §18) — settles a prediction: locks in the
correct option, scores every voter, updates their running stats
(accuracy/streak/score/rating), awards newly-earned badges, notifies
participants, and refreshes the leaderboard — inside one DB transaction
so a crash mid-way never leaves the prediction "resolved" with some users
unscored.

Idempotency: calling this twice with the same (prediction, correct_option)
is a safe no-op on the second call. Calling it twice with a *different*
correct_option is refused (ResolutionConflictError) rather than silently
double-crediting or corrupting a user's stats — an admin who needs to fix
a mistake must go through an explicit re-open flow, intentionally not
exposed in MVP.
"""

from django.db import transaction
from django.utils import timezone

from core.models import AuditLog, Notification
from predictions.models import AIPrediction, Prediction, PredictionStatus, UserPrediction
from scoring.models import ScoreEvent, ScoreEventType, UserStats
from scoring.pure import (
    StatsSnapshot,
    calculate_accuracy,
    calculate_rating,
    calculate_score,
    calculate_streak,
    determine_volume_badges,
    did_beat_ai,
)
from scoring.services import grant_badges, refresh_ranking


class ResolutionConflictError(Exception):
    pass


def resolve_prediction(prediction_id: int, correct_option: str, admin) -> dict:
    prediction = Prediction.objects.select_related(None).get(id=prediction_id)

    if prediction.status == PredictionStatus.CANCELLED:
        raise ResolutionConflictError("キャンセル済みの予測は確定できません")

    if prediction.status == PredictionStatus.RESOLVED:
        if prediction.correct_option == correct_option:
            return {"already_resolved": True}
        raise ResolutionConflictError(
            "この予測は既に異なる結果で確定済みです。結果を変更するには手動での再オープンが必要です。"
        )

    with transaction.atomic():
        prediction.status = PredictionStatus.RESOLVED
        prediction.correct_option = correct_option
        prediction.resolved_at = timezone.now()
        prediction.resolved_by = admin
        prediction.save(update_fields=["status", "correct_option", "resolved_at", "resolved_by"])

        user_predictions = list(
            UserPrediction.objects.select_related("user").filter(prediction=prediction, is_correct__isnull=True)
        )
        latest_ai = AIPrediction.objects.filter(prediction=prediction).order_by("-created_at").first()

        for up in user_predictions:
            result = calculate_score(up.selected_option, correct_option, up.confidence)

            up.is_correct = result.is_correct
            up.scored_at = timezone.now()
            up.save(update_fields=["is_correct", "scored_at"])

            # Unique(user, prediction, type) makes this insert itself
            # idempotent-safe: if this ever ran twice it would raise
            # rather than silently double-award points.
            ScoreEvent.objects.create(
                user=up.user,
                prediction=prediction,
                type=ScoreEventType.PREDICTION_CORRECT if result.is_correct else ScoreEventType.PREDICTION_INCORRECT,
                points=result.points,
                reason="予測的中" if result.is_correct else "予測不的中",
            )

            stats, _ = UserStats.objects.get_or_create(user=up.user)

            resolved = stats.resolved_predictions + 1
            correct = stats.correct_predictions + (1 if result.is_correct else 0)
            accuracy = calculate_accuracy(correct, resolved)
            streak = calculate_streak(stats.current_streak, stats.best_streak, result.is_correct)
            beat_ai = latest_ai is not None and did_beat_ai(up.selected_option, correct_option, latest_ai.yes_probability)
            ai_beat_count = stats.ai_beat_count + (1 if beat_ai else 0)
            prediction_score = stats.prediction_score + result.points
            rating = calculate_rating(accuracy, resolved)

            category_stats = dict(stats.category_stats or {})
            cat = dict(category_stats.get(prediction.category, {"correct": 0, "resolved": 0}))
            cat["resolved"] = cat.get("resolved", 0) + 1
            if result.is_correct:
                cat["correct"] = cat.get("correct", 0) + 1
            category_stats[prediction.category] = cat

            stats.resolved_predictions = resolved
            stats.correct_predictions = correct
            stats.accuracy = accuracy
            stats.current_streak = streak.current_streak
            stats.best_streak = streak.best_streak
            stats.ai_beat_count = ai_beat_count
            stats.prediction_score = prediction_score
            stats.rating = rating
            stats.category_stats = category_stats
            stats.save()

            grant_badges(
                up.user,
                determine_volume_badges(
                    StatsSnapshot(
                        total_predictions=stats.total_predictions,
                        resolved_predictions=resolved,
                        correct_predictions=correct,
                        current_streak=streak.current_streak,
                        best_streak=streak.best_streak,
                        prediction_score=prediction_score,
                        ai_beat_count=ai_beat_count,
                    )
                ),
            )

            Notification.objects.create(
                user=up.user,
                type=Notification.NotificationType.PREDICTION_RESOLVED,
                prediction=prediction,
                title="予測の結果が確定しました",
                body=(
                    f"「{prediction.title}」の結果は{correct_option}でした。"
                    f"あなたの予測は{'的中' if result.is_correct else '不的中'}でした（+{result.points}pt）。"
                ),
            )

        AuditLog.objects.create(
            actor=admin,
            action="RESOLVE_PREDICTION",
            target_type="Prediction",
            target_id=str(prediction.id),
            metadata={"correct_option": correct_option, "scored_users": len(user_predictions)},
        )

    # Ranking is a global recomputation over all users; running it outside
    # the per-prediction transaction keeps that transaction's lock window
    # small. A ranking-refresh failure doesn't roll back the scoring that
    # already committed — the safer failure mode.
    refresh_ranking()

    return {"already_resolved": False, "scored_users": len(user_predictions)}
