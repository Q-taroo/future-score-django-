from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.core import signing
from django.test import SimpleTestCase, override_settings

from accounts.email_verification import (
    make_verification_token,
    read_verification_token,
    send_verification_email,
)
from accounts.forms import RegisterForm


@override_settings(EMAIL_VERIFICATION_MAX_AGE=86400)
class EmailVerificationTokenTests(SimpleTestCase):
    def test_token_round_trip_keeps_user_and_email(self):
        user = SimpleNamespace(pk=42, email="person@example.com")
        payload = read_verification_token(make_verification_token(user))
        self.assertEqual(payload, {"uid": 42, "email": "person@example.com"})

    def test_tampered_token_is_rejected(self):
        user = SimpleNamespace(pk=42, email="person@example.com")
        token = make_verification_token(user)
        with self.assertRaises(signing.BadSignature):
            read_verification_token(f"{token}tampered")


@override_settings(
    RESEND_API_KEY="secret-test-key",
    RESEND_FROM_EMAIL="FUTURE SCORE <verify@example.com>",
)
class ResendDeliveryTests(SimpleTestCase):
    @patch("accounts.email_verification.requests.post")
    def test_sends_html_and_plain_text_with_idempotency(self, post):
        post.return_value = Mock(ok=True, status_code=200)
        user = SimpleNamespace(pk=7, email="person@example.com")
        send_verification_email(user, "https://example.com/verify/token")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["json"]["to"], ["person@example.com"])
        self.assertIn("html", kwargs["json"])
        self.assertIn("text", kwargs["json"])
        self.assertIn("Idempotency-Key", kwargs["headers"])
        self.assertEqual(kwargs["timeout"], 10)

    @patch("accounts.email_verification.requests.post")
    def test_network_failure_becomes_safe_delivery_error(self, post):
        post.side_effect = requests.Timeout("timed out")
        user = SimpleNamespace(pk=7, email="person@example.com")
        with self.assertRaises(RuntimeError):
            send_verification_email(user, "https://example.com/verify/token")


class RegisterFormTests(SimpleTestCase):
    @patch("accounts.forms.User.objects.filter")
    def test_email_is_normalized_and_checked_case_insensitively(self, user_filter):
        user_filter.return_value.exists.return_value = False
        form = RegisterForm(
            data={
                "username": "new_user",
                "email": " Person@Example.COM ",
                "password": "A-strong-password-934!",
                "password_confirmation": "A-strong-password-934!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "person@example.com")
        user_filter.assert_any_call(email__iexact="person@example.com")

    @patch("accounts.forms.User.objects.filter")
    def test_password_confirmation_must_match(self, user_filter):
        user_filter.return_value.exists.return_value = False
        form = RegisterForm(
            data={
                "username": "new_user",
                "email": "person@example.com",
                "password": "A-strong-password-934!",
                "password_confirmation": "different-password",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password_confirmation", form.errors)
