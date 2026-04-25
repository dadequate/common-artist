"""
Email delivery. Supports SMTP (default) and Brevo HTTP API.
Set EMAIL_PROVIDER=smtp|brevo|log (log = dev mode, prints to stdout).
"""
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.monitor import logger

_PROVIDER = os.environ.get("EMAIL_PROVIDER", "log")
_FROM     = os.environ.get("EMAIL_FROM", "noreply@example.com")
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
_GALLERY  = os.environ.get("GALLERY_NAME", "CommonArtist Gallery")


def _send_smtp(to: str, subject: str, html: str, text: str) -> None:
    host     = os.environ.get("SMTP_HOST", "")
    port     = int(os.environ.get("SMTP_PORT", "587"))
    user     = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = _FROM
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.ehlo()
        s.starttls(context=ctx)
        if user:
            s.login(user, password)
        s.sendmail(_FROM, [to], msg.as_string())


def _send_brevo(to: str, subject: str, html: str, text: str) -> None:
    import urllib.request
    import json

    api_key = os.environ.get("BREVO_API_KEY", "")
    payload = json.dumps({
        "sender":    {"email": _FROM, "name": _GALLERY},
        "to":        [{"email": to}],
        "subject":   subject,
        "htmlContent": html,
        "textContent": text,
    }).encode()

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Brevo API error {resp.status}")


def send_email(to: str, subject: str, html: str, text: str) -> None:
    try:
        if _PROVIDER == "smtp":
            _send_smtp(to, subject, html, text)
        elif _PROVIDER == "brevo":
            _send_brevo(to, subject, html, text)
        else:
            logger.info("commonartist.email.dev", to=to, subject=subject, text=text[:200])
            return
        logger.info("commonartist.email.sent", to=to, subject=subject, provider=_PROVIDER)
    except Exception as e:
        logger.error("commonartist.email.failed", to=to, error=str(e))
        raise


def send_magic_link(to: str, token: str) -> None:
    url  = f"{_BASE_URL}/portal/auth?token={token}"
    subj = f"Your login link for {_GALLERY}"
    html = f"""<!doctype html><html><body style="font-family:sans-serif;max-width:480px;margin:40px auto;padding:20px;color:#333;">
<h2 style="color:#7C3AED;">{_GALLERY}</h2>
<p style="font-size:15px;margin:16px 0;">Click the button below to log in to your artist portal. This link expires in 30 minutes.</p>
<a href="{url}" style="display:inline-block;background:#7C3AED;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Log In to Portal</a>
<p style="font-size:12px;color:#999;margin-top:24px;">Or copy this link: {url}<br>If you didn't request this, ignore this email.</p>
</body></html>"""
    text = f"Log in to your {_GALLERY} artist portal:\n\n{url}\n\nExpires in 30 minutes."
    send_email(to, subj, html, text)
