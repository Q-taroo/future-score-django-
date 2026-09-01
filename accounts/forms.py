import re

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class RegisterForm(forms.Form):
    username = forms.CharField(min_length=3, max_length=20, label="ユーザー名")
    email = forms.EmailField(label="メールアドレス")
    password = forms.CharField(min_length=8, max_length=100, widget=forms.PasswordInput, label="パスワード（8文字以上）")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not USERNAME_RE.match(username):
            raise forms.ValidationError("ユーザー名は英数字とアンダースコアのみ使用できます")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("このユーザー名は既に使用されています")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")
        return email


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="メールアドレス")
    password = forms.CharField(widget=forms.PasswordInput, label="パスワード")
