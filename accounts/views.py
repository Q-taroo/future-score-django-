from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core import signing
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.forms import EmailLoginForm, RegisterForm
from accounts.email_verification import make_verification_token, read_verification_token, send_verification_email
from core.rate_limit import check_rate_limit, client_ip
from core.services.analytics import track_event
from scoring.models import UserStats

User = get_user_model()


def _send_verification(request, user):
    token = make_verification_token(user)
    url = request.build_absolute_uri(reverse("accounts:verify_email", args=[token]))
    send_verification_email(user, url)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("scoring:me_dashboard")

    if request.method == "POST":
        ip = client_ip(request)
        if not check_rate_limit(f"register:{ip}", 5, 60):
            messages.error(request, "リクエストが多すぎます。しばらくしてから再度お試しください。")
            return render(request, "accounts/register.html", {"form": RegisterForm(request.POST)})

        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    is_active=not settings.EMAIL_VERIFICATION_ENABLED,
                )
            except IntegrityError:
                messages.error(request, "登録情報が既に使用されています。内容をご確認ください。")
                return render(request, "accounts/register.html", {"form": form}, status=409)
            UserStats.objects.get_or_create(user=user)
            if settings.EMAIL_VERIFICATION_ENABLED:
                request.session["pending_verification_user_id"] = user.pk
                try:
                    _send_verification(request, user)
                    messages.success(request, "認証メールを送信しました")
                except RuntimeError:
                    messages.error(request, "認証メールを送信できませんでした。再送をお試しください。")
                return redirect("accounts:verification_sent")
            track_event("signup_completed", user=user)
            login(request, user)
            messages.success(request, "登録が完了しました")
            return redirect("scoring:me_dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def verification_sent_view(request):
    if not settings.EMAIL_VERIFICATION_ENABLED:
        return redirect("accounts:register")
    return render(request, "accounts/verification_sent.html")


def resend_verification_view(request):
    if request.method != "POST" or not settings.EMAIL_VERIFICATION_ENABLED:
        return redirect("accounts:register")
    user_id = request.session.get("pending_verification_user_id")
    user = User.objects.filter(pk=user_id, is_active=False).first()
    if user and check_rate_limit(f"verify-email:{user.pk}", 3, 900):
        try:
            _send_verification(request, user)
        except RuntimeError:
            messages.error(request, "認証メールを送信できませんでした。時間をおいて再度お試しください。")
        else:
            messages.success(request, "認証メールを再送しました")
    else:
        messages.info(request, "送信済みの場合はメールをご確認ください。再送はしばらく待ってからお試しください。")
    return redirect("accounts:verification_sent")


def verify_email_view(request, token):
    try:
        payload = read_verification_token(token)
        user = User.objects.get(pk=payload["uid"], email__iexact=payload["email"])
    except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError):
        return render(request, "accounts/verification_result.html", {"verified": False}, status=400)

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
        UserStats.objects.get_or_create(user=user)
        track_event("signup_completed", user=user)
    request.session.pop("pending_verification_user_id", None)
    return render(request, "accounts/verification_result.html", {"verified": True})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("scoring:me_dashboard")

    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            try:
                candidate = User.objects.get(email=email)
            except User.DoesNotExist:
                candidate = None

            user = authenticate(request, username=candidate.username, password=password) if candidate else None
            if user is not None and user.is_active:
                login(request, user)
                return redirect("scoring:me_dashboard")
            form.add_error(None, "メールアドレスまたはパスワードが正しくありません")
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("predictions:home")
