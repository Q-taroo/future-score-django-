"""Vote submission + prediction lifecycle (spec §7)."""

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify as django_slugify

from core.models import AuditLog
from predictions.models import Prediction, PredictionStatus, UserPrediction, UserPredictionHistory
from predictions.providers.ai import get_ai_provider
from predictions.providers.ai.base import PredictionInputForAI
from predictions.providers.opinion import MockOpinionProvider, OpinionSignalInput
from scoring.models import UserStats
from scoring.pure import StatsSnapshot, determine_volume_badges
from scoring.services import grant_badges


class VoteError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


def close_expired_predictions() -> int:
    """MVP has no background job runner, so deadline enforcement is done
    lazily: any read path that lists/shows predictions calls this first.
    submit_vote() also independently checks status + deadline, so this is
    a UX/consistency nicety, not the sole enforcement mechanism."""
    return Prediction.objects.filter(status=PredictionStatus.OPEN, deadline__lte=timezone.now()).update(
        status=PredictionStatus.CLOSED
    )


def submit_vote(user, prediction: Prediction, selected_option: str, confidence: int | None) -> UserPrediction:
    """Rules: allowed while OPEN and before deadline; refused after.
    Only the latest vote is the "official" record; every change is also
    appended to UserPredictionHistory (append-only audit trail)."""
    if prediction.status != PredictionStatus.OPEN:
        raise VoteError("この予測は現在投票を受け付けていません", "PREDICTION_NOT_OPEN")
    if prediction.deadline <= timezone.now():
        raise VoteError("締切を過ぎているため予測を送信できません", "DEADLINE_PASSED")

    with transaction.atomic():
        up, created = UserPrediction.objects.select_for_update().get_or_create(
            user=user,
            prediction=prediction,
            defaults={"selected_option": selected_option, "confidence": confidence},
        )
        if not created:
            up.selected_option = selected_option
            up.confidence = confidence
            up.save(update_fields=["selected_option", "confidence", "updated_at"])

        UserPredictionHistory.objects.create(
            user_prediction=up, selected_option=selected_option, confidence=confidence
        )

        # total_predictions only grows on a genuinely new vote, not on an
        # edit of an existing one before the deadline.
        if created:
            stats, _ = UserStats.objects.get_or_create(user=user)
            stats.total_predictions += 1
            stats.save(update_fields=["total_predictions"])

            grant_badges(
                user,
                determine_volume_badges(
                    StatsSnapshot(
                        total_predictions=stats.total_predictions,
                        resolved_predictions=stats.resolved_predictions,
                        correct_predictions=stats.correct_predictions,
                        current_streak=stats.current_streak,
                        best_streak=stats.best_streak,
                        prediction_score=stats.prediction_score,
                        ai_beat_count=stats.ai_beat_count,
                    )
                ),
            )

    return up


def create_prediction(admin, data: dict) -> Prediction:
    """Creates a prediction and immediately seeds it with an initial AI
    prediction + opinion signal, so the detail page never shows an empty
    panel for a freshly created question."""
    prediction = Prediction.objects.create(
        slug="temp",
        title=data["title"],
        description=data["description"],
        category=data["category"],
        option_a=data.get("option_a") or "YES",
        option_b=data.get("option_b") or "NO",
        deadline=data["deadline"],
        source_url=data.get("source_url") or "",
        resolution_method=data.get("resolution_method") or "",
        min_predictions_for_ranking=data.get("min_predictions_for_ranking", 10),
        created_by=admin,
    )
    base_slug = django_slugify(data["title"])[:60] or "prediction"
    prediction.slug = f"{base_slug}-{prediction.id}"
    prediction.save(update_fields=["slug"])

    ai = get_ai_provider()
    ai_output = ai.generate_prediction(
        PredictionInputForAI(
            id=str(prediction.id),
            title=prediction.title,
            description=prediction.description,
            category=prediction.category,
            option_a=prediction.option_a,
            option_b=prediction.option_b,
            deadline=prediction.deadline,
        )
    )
    from predictions.models import AIPrediction, OpinionSignal

    AIPrediction.objects.create(
        prediction=prediction,
        provider=ai.provider_name,
        model=ai_output.model,
        yes_probability=ai_output.probability,
        no_probability=1 - ai_output.probability,
        reasoning_summary=ai_output.reasoning_summary,
    )

    opinion = MockOpinionProvider()
    opinion_result = opinion.fetch_signal(
        OpinionSignalInput(id=str(prediction.id), title=prediction.title, category=prediction.category)
    )
    OpinionSignal.objects.create(
        prediction=prediction,
        source=opinion_result.source,
        yes_probability=opinion_result.yes_probability,
        no_probability=opinion_result.no_probability,
        sample_size=opinion_result.sample_size,
    )

    AuditLog.objects.create(
        actor=admin, action="CREATE_PREDICTION", target_type="Prediction", target_id=str(prediction.id),
        metadata={"title": prediction.title},
    )

    return prediction
