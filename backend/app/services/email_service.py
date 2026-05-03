"""
Email Service

Sends transactional emails via Resend API.
Uses httpx (already in requirements) — no extra dependencies needed.
"""

import httpx
from app.core.config import settings

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "Mentis <noreply@mentis.forzone.uk>"


async def send_password_reset_code(email: str, code: str, first_name: str) -> None:
    """
    Send a 6-digit password reset code to the user's email.

    Raises:
        RuntimeError: If Resend API returns a non-2xx status.
    """
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <h2 style="color: #3b82f6; margin-bottom: 8px;">Mentis</h2>
      <h3 style="margin-bottom: 24px;">Password Reset</h3>
      <p>Hi {first_name},</p>
      <p>Use the code below to reset your password. It expires in <strong>10 minutes</strong>.</p>
      <div style="
        font-size: 36px;
        font-weight: bold;
        letter-spacing: 8px;
        text-align: center;
        padding: 24px;
        background: #f1f5f9;
        border-radius: 12px;
        margin: 24px 0;
        color: #1e293b;
      ">{code}</div>
      <p style="color: #64748b; font-size: 14px;">
        If you didn't request a password reset, you can safely ignore this email.
      </p>
    </div>
    """

    payload = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": f"{code} — Mentis password reset code",
        "html": html_body,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESEND_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Resend API error {response.status_code}: {response.text}"
        )


async def send_verification_email(email: str, code: str, first_name: str) -> None:
    """
    Send a 6-digit email verification code on registration.
    """
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <h2 style="color: #3b82f6; margin-bottom: 8px;">Mentis</h2>
      <h3 style="margin-bottom: 24px;">Confirm your email</h3>
      <p>Hi {first_name}, welcome to Mentis!</p>
      <p>Enter this code to verify your email address. It expires in <strong>15 minutes</strong>.</p>
      <div style="
        font-size: 36px;
        font-weight: bold;
        letter-spacing: 8px;
        text-align: center;
        padding: 24px;
        background: #f1f5f9;
        border-radius: 12px;
        margin: 24px 0;
        color: #1e293b;
      ">{code}</div>
      <p style="color: #64748b; font-size: 14px;">
        If you didn't create a Mentis account, you can safely ignore this email.
      </p>
    </div>
    """

    payload = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": f"{code} — Confirm your Mentis email",
        "html": html_body,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESEND_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Resend API error {response.status_code}: {response.text}"
        )
