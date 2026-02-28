"""通过 QQ邮箱 SMTP（587 + STARTTLS）发送邮件（验证码等）。"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.services.email_code_store import set_code as store_set_code

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str) -> None:
    """
    生成 6 位验证码并发送到邮箱；验证码存入内存供注册时校验。
    未配置 SMTP 时抛出 BusinessError。
    """
    if not settings.smtp_user or not settings.smtp_password:
        raise BusinessError(
            code="EMAIL_NOT_CONFIGURED",
            message="邮件服务未配置，请联系管理员",
        )
    code = store_set_code(to_email)
    subject = "【肆幺捌 CRM系统】邮箱验证码"
    body = f"您的验证码为：{code}，5分钟内有效。如非本人操作请忽略。"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            if settings.smtp_use_starttls:
                server.starttls()
                server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], to_email, msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        logger.exception("QQ邮箱 SMTP 认证失败（请检查邮箱、应用密码与安全设置）")
        raise BusinessError(
            code="EMAIL_SEND_FAILED",
            message="邮箱认证失败，请检查 SMTP 账号与应用密码",
        ) from e
    except smtplib.SMTPException as e:
        logger.exception("QQ邮箱 SMTP 错误: %s", e)
        raise BusinessError(
            code="EMAIL_SEND_FAILED",
            message="验证码发送失败，请稍后重试",
        ) from e
    except OSError as e:
        logger.exception("连接 QQ邮箱 SMTP 失败（网络/端口/防火墙）: %s", e)
        raise BusinessError(
            code="EMAIL_SEND_FAILED",
            message="无法连接邮件服务器，请检查网络或稍后重试",
        ) from e
    except Exception as e:
        logger.exception("发送验证码邮件时出错: %s", e)
        raise BusinessError(
            code="EMAIL_SEND_FAILED",
            message="验证码发送失败，请稍后重试",
        ) from e
