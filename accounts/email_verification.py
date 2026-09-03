import html
import logging

import requests
from django.conf import settings
from django.core import signing

logger = logging.getLogger(__name__)
TOKEN_SALT = "future-score.email-verification.v1"


def make_verification_token(user) -> str:
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=TOKEN_SALT, compress=True)


def read_verification_token(token: str) -> dict:
    return signing.loads(token, salt=TOKEN_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)


def send_verification_email(user, verification_url: str) -> None:
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        raise RuntimeError("Resend email delivery is not configured")

    safe_url = html.escape(verification_url, quote=True)
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                "Idempotency-Key": f"verify-{user.pk}-{make_verification_token(user)[-32:]}",
            },
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": [user.email],
                "subject": "【FUTURE SCORE】メールアドレスを確認してください",
                "html": (
                    "<h2>FUTURE SCORE メールアドレス認証</h2>"
                    "<p>以下のボタンから24時間以内にメールアドレス認証を完了してください。</p>"
                    f'<p><a href="{safe_url}" style="display:inline-block;padding:12px 24px;'
                    'background:#4f46e5;color:#fff;text-decoration:none;border-radius:999px">'
                    "メールアドレスを認証する</a></p>"
                    "<p>この登録に心当たりがない場合は、このメールを破棄してください。</p>"
                ),
                "text": f"以下のURLから24時間以内にメールアドレスを認証してください。\n{verification_url}",
            },
            timeout=10,
        )
    except requests.RequestException as error:
        logger.error("Resend delivery failed due to a network error: %s", type(error).__name__)
        raise RuntimeError("Verification email delivery failed") from error
    if not response.ok:
        logger.error("Resend delivery failed with status %s", response.status_code)
        raise RuntimeError("Verification email delivery failed")
