import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class RegisterForm(forms.Form):
    username = forms.CharField(
        min_length=3, max_length=20, label="ユーザー名",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="メールアドレス", widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )
    password = forms.CharField(
        min_length=8, max_length=100, label="パスワード（8文字以上）",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password_confirmation = forms.CharField(
        min_length=8, max_length=100, label="パスワード（確認）",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirmation", "パスワードが一致しません")
        elif password:
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not USERNAME_RE.match(username):
            raise forms.ValidationError("ユーザー名は英数字とアンダースコアのみ使用できます")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("このユーザー名は既に使用されています")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        email = email.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")
        return email


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="メールアドレス")
    password = forms.CharField(widget=forms.PasswordInput, label="パスワード")
