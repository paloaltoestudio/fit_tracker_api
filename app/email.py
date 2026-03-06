import resend
from app.config import settings


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email via Resend."""
    resend.api_key = settings.resend_api_key
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    resend.Emails.send({
        "from": settings.email_from,
        "to": to_email,
        "subject": "Reset your Fit Tracker password",
        "html": f"""
        <p>Click the link below to reset your password. It expires in <strong>15 minutes</strong>.</p>
        <p><a href="{reset_link}">Reset password</a></p>
        <p>If you didn't request this, ignore this email.</p>
        """,
        "text": f"Reset your password (expires in 15 minutes):\n\n{reset_link}\n\nIf you didn't request this, ignore this email.",
    })
