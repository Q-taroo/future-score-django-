from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from adminpanel.forms import CreatePredictionForm, ResolveForm
from adminpanel.kpi import get_kpi_summary
from core.decorators import admin_required
from core.models import AuditLog
from predictions.models import AIPrediction, OpinionSignal, Prediction, PredictionStatus
from predictions.services import create_prediction
from scoring.resolution import ResolutionConflictError, resolve_prediction

User = get_user_model()


@admin_required
def dashboard(request):
    tab = request.GET.get("tab", "kpi")

    context = {"tab": tab}

    if tab == "kpi":
        context["kpi"] = get_kpi_summary()
    elif tab == "predictions":
        context["predictions"] = (
            Prediction.objects.order_by("-created_at").annotate(participant_count=Count("user_predictions"))
        )
    elif tab == "create":
        context["form"] = CreatePredictionForm()
    elif tab == "users":
        context["users"] = User.objects.select_related("stats").order_by("-date_joined")[:200]
    elif tab == "signals":
        context["ai_predictions"] = AIPrediction.objects.select_related("prediction").order_by("-created_at")[:50]
        context["opinion_signals"] = OpinionSignal.objects.select_related("prediction").order_by("-captured_at")[:50]
    elif tab == "audit":
        context["audit_logs"] = AuditLog.objects.select_related("actor").order_by("-created_at")[:50]

    return render(request, "adminpanel/dashboard.html", context)


@admin_required
@require_POST
def create_prediction_view(request):
    form = CreatePredictionForm(request.POST)
    if form.is_valid():
        create_prediction(request.user, form.cleaned_data)
        messages.success(request, "予測を作成しました")
        return redirect("/admin-panel/?tab=predictions")

    messages.error(request, "入力内容に誤りがあります")
    return render(request, "adminpanel/dashboard.html", {"tab": "create", "form": form})


@admin_required
@require_POST
def resolve_view(request, prediction_id: int):
    form = ResolveForm(request.POST)
    if form.is_valid():
        try:
            resolve_prediction(prediction_id, form.cleaned_data["correct_option"], request.user)
            messages.success(request, "結果を確定しました")
        except ResolutionConflictError as exc:
            messages.error(request, str(exc))
    return redirect("/admin-panel/?tab=predictions")


@admin_required
@require_POST
def cancel_prediction_view(request, prediction_id: int):
    prediction = get_object_or_404(Prediction, id=prediction_id)
    prediction.status = PredictionStatus.CANCELLED
    prediction.save(update_fields=["status"])
    AuditLog.objects.create(
        actor=request.user, action="CANCEL_PREDICTION", target_type="Prediction", target_id=str(prediction.id)
    )
    messages.success(request, "キャンセルしました")
    return redirect("/admin-panel/?tab=predictions")


@admin_required
@require_POST
def toggle_user_active_view(request, user_id: int):
    user = get_object_or_404(User, id=user_id)
    if user.role != User.Role.ADMIN:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        AuditLog.objects.create(
            actor=request.user,
            action="REACTIVATE_USER" if user.is_active else "SUSPEND_USER",
            target_type="User",
            target_id=str(user.id),
        )
        messages.success(request, "更新しました")
    return redirect("/admin-panel/?tab=users")
