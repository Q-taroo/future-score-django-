from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.forms import EmailLoginForm, RegisterForm
from core.rate_limit import check_rate_limit, client_ip
from core.services.analytics import track_event
from scoring.models import UserStats

User = get_user_model()


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
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            UserStats.objects.get_or_create(user=user)
            track_event("signup_completed", user=user)
            login(request, user)
            messages.success(request, "登録が完了しました")
            return redirect("scoring:me_dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


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
