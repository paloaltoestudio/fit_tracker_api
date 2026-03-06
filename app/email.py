import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email via Gmail SMTP."""
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Reset your Fit Tracker password"
    message["From"] = settings.gmail_user
    message["To"] = to_email

    text = f"Click the link below to reset your password (expires in 15 minutes):\n\n{reset_link}"
    html = f"""
    <p>Click the link below to reset your password. It expires in <strong>15 minutes</strong>.</p>
    <p><a href="{reset_link}">Reset password</a></p>
    <p>If you didn't request this, ignore this email.</p>
    """

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(settings.gmail_user, settings.gmail_app_password)
        server.sendmail(settings.gmail_user, to_email, message.as_string())
