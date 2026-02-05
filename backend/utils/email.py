"""
Email utility functions
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional

from backend.core.config import settings


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Send email using SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body (optional)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"[EMAIL] SMTP not configured. Would send to {to_email}: {subject}")
        print(f"[EMAIL] Content: {text_content or html_content}")
        return True

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = Header(subject, "utf-8")
        # 한글 이름은 RFC 2047 인코딩 필요
        from_name = Header(settings.SMTP_FROM_NAME, "utf-8").encode()
        message["From"] = f"{from_name} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        if text_content:
            message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        # 네이버 등 일부 SMTP는 SSL 컨텍스트가 필요
        context = ssl.create_default_context()

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, message.as_string())

        print(f"[EMAIL] Successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send password reset email

    Args:
        to_email: Recipient email address
        reset_token: Password reset token

    Returns:
        True if email sent successfully
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "[자치법규 정비 시스템] 비밀번호 재설정"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: 'Malgun Gothic', sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 30px; border-radius: 10px;">
            <h2 style="color: #667eea; margin-bottom: 20px;">비밀번호 재설정</h2>
            <p>안녕하세요,</p>
            <p>비밀번호 재설정을 요청하셨습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정하세요.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}"
                   style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white;
                          padding: 12px 30px;
                          text-decoration: none;
                          border-radius: 5px;
                          display: inline-block;">
                    비밀번호 재설정
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">
                이 링크는 30분 후에 만료됩니다.<br>
                본인이 요청하지 않은 경우, 이 이메일을 무시하세요.
            </p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">자치법규 정비 시스템</p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
비밀번호 재설정

안녕하세요,

비밀번호 재설정을 요청하셨습니다. 아래 링크를 클릭하여 새 비밀번호를 설정하세요.

{reset_url}

이 링크는 30분 후에 만료됩니다.
본인이 요청하지 않은 경우, 이 이메일을 무시하세요.

자치법규 정비 시스템
    """

    return await send_email(to_email, subject, html_content, text_content)
