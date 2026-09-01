from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from core.services.analytics import track_event
from predictions.models import FINANCE_CATEGORIES
from scoring.models import ScoreEvent, UserStats
from scoring.pure import DEFAULT_MIN_PREDICTIONS_FOR_RANKING, RankableUser, build_ranking

User = get_user_model()

CATEGORY_TABS = [{"key": "overall", "label": "総合", "category": None}] + [
    {"key": c.value, "label": c.label, "category": c.value} for c in FINANCE_CATEGORIES
]


def ranking(request):
    tab_key = request.GET.get("tab", "overall")
    tab = next((t for t in CATEGORY_TABS if t["key"] == tab_key), CATEGORY_TABS[0])

    track_event("ranking_viewed", user=request.user)

    if tab["category"] is None:
        rows = _overall_ranking()
    else:
        rows = _category_ranking(tab["category"])

    return render(request, "scoring/ranking.html", {"tabs": CATEGORY_TABS, "active_tab": tab, "rows": rows})


def _overall_ranking(min_predictions: int = DEFAULT_MIN_PREDICTIONS_FOR_RANKING):
    all_stats = list(UserStats.objects.select_related("user"))
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
    stats_by_user = {s.user_id: s for s in all_stats}
    rows = []
    for r in ranked:
        s = stats_by_user[r.user_id]
        rows.append(
            {
                "rank": r.rank,
                "username": s.user.username,
                "prediction_score": s.prediction_score,
                "accuracy": s.accuracy,
                "rating": s.rating,
            }
        )
    return rows


def _category_ranking(category: str, min_resolved: int = 3):
    all_stats = list(UserStats.objects.select_related("user"))
    rows = []
    for s in all_stats:
        cat = (s.category_stats or {}).get(category)
        if not cat or cat.get("resolved", 0) < min_resolved:
            continue
        resolved = cat["resolved"]
        correct = cat.get("correct", 0)
        rows.append(
            {
                "username": s.user.username,
                "accuracy": correct / resolved if resolved else 0,
                "resolved": resolved,
                "correct": correct,
            }
        )
    rows.sort(key=lambda r: (-r["accuracy"], -r["resolved"]))
    for idx, row in enumerate(rows):
        row["rank"] = idx + 1
    return rows


def profile(request, username: str):
    user = get_object_or_404(User, username=username)
    stats = getattr(user, "stats", None)
    badges = user.badges.select_related("badge").order_by("-earned_at")
    history = (
        user.predictions_voted.select_related("prediction").order_by("-created_at")[:20]
    )

    track_event("profile_viewed", user=request.user, metadata={"profile_username": username})

    return render(
        request,
        "scoring/profile.html",
        {"profile_user": user, "stats": stats, "badges": badges, "history": history},
    )


@login_required
def me_dashboard(request):
    user = request.user
    stats, _ = UserStats.objects.get_or_create(user=user)

    monthly_accuracy = _monthly_accuracy(user)
    cumulative_score = _cumulative_score(user)

    return render(
        request,
        "scoring/dashboard.html",
        {
            "stats": stats,
            "monthly_accuracy": monthly_accuracy,
            "cumulative_score": cumulative_score,
        },
    )


def _monthly_accuracy(user):
    rows = user.predictions_voted.exclude(is_correct=None).exclude(scored_at=None).order_by("scored_at")
    by_month: dict[str, dict] = {}
    for row in rows:
        key = row.scored_at.strftime("%Y-%m")
        entry = by_month.setdefault(key, {"correct": 0, "total": 0})
        entry["total"] += 1
        if row.is_correct:
            entry["correct"] += 1
    months = list(by_month.items())[-6:]
    return [{"month": m, "accuracy": round(v["correct"] / v["total"] * 100) if v["total"] else 0} for m, v in months]


def _cumulative_score(user):
    events = ScoreEvent.objects.filter(user=user).order_by("created_at")
    running = 0
    result = []
    for e in events:
        running += e.points
        result.append({"date": e.created_at.strftime("%Y-%m-%d"), "score": running})
    return result
