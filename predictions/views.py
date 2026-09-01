import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from core.errors import AppError, handle_exception
from core.services.analytics import track_event
from predictions.models import Category, FINANCE_CATEGORIES, Prediction, PredictionStatus, UserPrediction
from predictions.services import VoteError, close_expired_predictions, submit_vote


def _vote_split(prediction_id: int) -> dict:
    yes = UserPrediction.objects.filter(prediction_id=prediction_id, selected_option="YES").count()
    no = UserPrediction.objects.filter(prediction_id=prediction_id, selected_option="NO").count()
    total = yes + no
    yes_percent = (yes / total * 100) if total else 50
    return {"yes": yes, "no": no, "total": total, "yes_percent": yes_percent, "no_percent": 100 - yes_percent}


def _vote_splits_bulk(prediction_ids: list[int]) -> dict[int, dict]:
    if not prediction_ids:
        return {}
    rows = (
        UserPrediction.objects.filter(prediction_id__in=prediction_ids)
        .values("prediction_id", "selected_option")
        .annotate(count=Count("id"))
    )
    splits = {pid: {"yes": 0, "no": 0} for pid in prediction_ids}
    for row in rows:
        splits[row["prediction_id"]][row["selected_option"].lower()] = row["count"]
    result = {}
    for pid, s in splits.items():
        total = s["yes"] + s["no"]
        yes_percent = (s["yes"] / total * 100) if total else 50
        result[pid] = {"yes": s["yes"], "no": s["no"], "total": total, "yes_percent": yes_percent, "no_percent": 100 - yes_percent}
    return result


def home(request):
    close_expired_predictions()
    predictions = (
        Prediction.objects.filter(status=PredictionStatus.OPEN)
        .order_by("-is_featured", "deadline")[:6]
        .prefetch_related("ai_predictions")
        .annotate(participant_count=Count("user_predictions"))
    )
    splits = _vote_splits_bulk([p.id for p in predictions])
    return render(
        request,
        "predictions/home.html",
        {"predictions": predictions, "splits": splits, "categories": FINANCE_CATEGORIES},
    )


def prediction_list(request):
    close_expired_predictions()
    category = request.GET.get("category")
    status = request.GET.get("status", PredictionStatus.OPEN)

    qs = Prediction.objects.all()
    if category and category in Category.values:
        qs = qs.filter(category=category)
    if status in PredictionStatus.values:
        qs = qs.filter(status=status)

    predictions = qs.order_by("-is_featured", "deadline").prefetch_related("ai_predictions").annotate(
        participant_count=Count("user_predictions")
    )
    splits = _vote_splits_bulk([p.id for p in predictions])

    return render(
        request,
        "predictions/list.html",
        {
            "predictions": predictions,
            "splits": splits,
            "categories": FINANCE_CATEGORIES,
            "selected_category": category,
            "selected_status": status,
            "status_labels": [("OPEN", "受付中"), ("CLOSED", "締切済み"), ("RESOLVED", "確定済み")],
        },
    )


def prediction_detail(request, slug: str):
    close_expired_predictions()
    prediction = get_object_or_404(
        Prediction.objects.prefetch_related("ai_predictions", "opinion_signals").annotate(
            participant_count=Count("user_predictions")
        ),
        slug=slug,
    )

    ai = prediction.ai_predictions.order_by("-created_at").first()
    opinion = prediction.opinion_signals.order_by("-captured_at").first()
    split = _vote_split(prediction.id)

    my_vote = None
    if request.user.is_authenticated:
        my_vote = UserPrediction.objects.filter(user=request.user, prediction=prediction).first()

    track_event("prediction_viewed", user=request.user, metadata={"prediction_id": prediction.id})

    return render(
        request,
        "predictions/detail.html",
        {
            "prediction": prediction,
            "ai": ai,
            "opinion": opinion,
            "split": split,
            "my_vote": my_vote,
            "is_open": prediction.status == PredictionStatus.OPEN,
        },
    )


@login_required
@require_POST
def vote(request, slug: str):
    """JSON endpoint used by the vote panel's fetch() call — kept
    separate from the page render so voting doesn't need a full page
    reload (progressive enhancement over a plain form fallback)."""
    try:
        prediction = get_object_or_404(Prediction, slug=slug)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            raise AppError("不正なリクエストです", 400, "BAD_REQUEST")

        selected_option = body.get("selected_option")
        if selected_option not in ("YES", "NO"):
            raise AppError("選択肢が不正です", 400, "VALIDATION_ERROR")

        confidence = body.get("confidence")
        if confidence is not None:
            try:
                confidence = int(confidence)
            except (TypeError, ValueError):
                raise AppError("自信度が不正です", 400, "VALIDATION_ERROR")
            if not (50 <= confidence <= 100):
                raise AppError("自信度は50〜100の範囲で入力してください", 400, "VALIDATION_ERROR")

        try:
            up = submit_vote(request.user, prediction, selected_option, confidence)
        except VoteError as exc:
            raise AppError(exc.message, 400, exc.code)

        track_event(
            "prediction_submitted", user=request.user, metadata={"prediction_id": prediction.id, "selected_option": selected_option}
        )

        return JsonResponse(
            {"ok": True, "selected_option": up.selected_option, "confidence": up.confidence}
        )
    except Exception as exc:  # noqa: BLE001
        return handle_exception(exc)
