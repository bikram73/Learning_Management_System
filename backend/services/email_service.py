import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from flask import current_app, render_template

from database import db
from models import WelcomeEmailJob


SUBJECTS_BY_ROLE = {
    "admin": "Welcome to LMS Admin",
    "student": "Welcome to LMS",
}

TEMPLATES_BY_ROLE = {
    "admin": "welcome_admin_mail.html",
    "student": "welcome_student_mail.html",
}


def _mail_config() -> dict:
    return {
        "host": current_app.config.get("MAIL_HOST") or os.getenv("MAIL_HOST"),
        "port": int(current_app.config.get("MAIL_PORT") or os.getenv("MAIL_PORT", "587")),
        "username": current_app.config.get("MAIL_USERNAME") or os.getenv("MAIL_USERNAME"),
        "password": current_app.config.get("MAIL_PASSWORD") or os.getenv("MAIL_PASSWORD"),
        "from_email": current_app.config.get("MAIL_FROM") or os.getenv("MAIL_FROM"),
        "use_tls": str(current_app.config.get("MAIL_USE_TLS") or os.getenv("MAIL_USE_TLS", "true")).lower() == "true",
        "app_base_url": (current_app.config.get("APP_BASE_URL") or os.getenv("APP_BASE_URL") or "http://127.0.0.1:5000").rstrip("/"),
        "support_email": current_app.config.get("SUPPORT_EMAIL") or os.getenv("SUPPORT_EMAIL") or "support@example.com",
    }


def _validate_mail_config(config: dict):
    required = ["host", "port", "from_email"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError(f"Missing mail configuration: {', '.join(missing)}")


def queue_welcome_email(user):
    template_name = TEMPLATES_BY_ROLE.get(user.role, TEMPLATES_BY_ROLE["student"])
    subject = SUBJECTS_BY_ROLE.get(user.role, SUBJECTS_BY_ROLE["student"])
    job = WelcomeEmailJob(user_id=user.id, template_name=template_name, subject=subject)
    db.session.add(job)
    return job


def _render_welcome_html(job: WelcomeEmailJob, config: dict) -> str:
    user = job.user
    return render_template(
        job.template_name,
        user_name=user.name,
        user_email=user.email,
        user_role=user.role,
        app_name="Learning Management System",
        dashboard_url=f"{config['app_base_url']}/dashboard.html",
        profile_url=f"{config['app_base_url']}/profile.html",
        login_url=f"{config['app_base_url']}/login.html",
        support_email=config["support_email"],
        current_year=datetime.utcnow().year,
    )


def send_html_email(to_email: str, subject: str, html_body: str):
    config = _mail_config()
    _validate_mail_config(config)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"]
    message["To"] = to_email
    message.set_content("Welcome to Learning Management System. Please view this email in HTML format.")
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(config["host"], config["port"], timeout=30) as smtp:
        if config["use_tls"]:
            smtp.starttls()
        if config["username"] and config["password"]:
            smtp.login(config["username"], config["password"])
        smtp.send_message(message)


def send_html_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes,
    filename: str,
):
    config = _mail_config()
    _validate_mail_config(config)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"]
    message["To"] = to_email
    message.set_content("Please view this email in HTML format.")
    message.add_alternative(html_body, subtype="html")
    message.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    with smtplib.SMTP(config["host"], config["port"], timeout=30) as smtp:
        if config["use_tls"]:
            smtp.starttls()
        if config["username"] and config["password"]:
            smtp.login(config["username"], config["password"])
        smtp.send_message(message)


def send_course_payment_email(user, course, token: str):
    config = _mail_config()
    payment_url = f"{config['app_base_url']}/course_payment.html?token={token}"
    html_body = render_template(
        "cource_payment_mail.html",
        user_name=user.name,
        user_email=user.email,
        course_title=course.title,
        course_price=f"{float(course.price or 0):.2f}",
        payment_url=payment_url,
        support_email=config["support_email"],
        app_name="Learning Management System",
        current_year=datetime.utcnow().year,
    )
    send_html_email(user.email, f"Payment link for {course.title}", html_body)


def send_course_paid_email(user, course, receipt_number: str, receipt_pdf: bytes):
    config = _mail_config()
    html_body = render_template(
        "cource_paid_mail.html",
        user_name=user.name,
        user_email=user.email,
        course_title=course.title,
        amount=f"{float(course.price or 0):.2f}",
        receipt_number=receipt_number,
        dashboard_url=f"{config['app_base_url']}/dashboard.html",
        support_email=config["support_email"],
        app_name="Learning Management System",
        current_year=datetime.utcnow().year,
    )
    send_html_email_with_attachment(
        user.email,
        f"Payment confirmed - {course.title}",
        html_body,
        receipt_pdf,
        f"receipt-{receipt_number}.pdf",
    )


def send_welcome_course_email(user, course):
    config = _mail_config()
    html_body = render_template(
        "welcome_course.html",
        user_name=user.name,
        course_title=course.title,
        instructor=course.instructor,
        pricing_type=(course.pricing_type or "free").capitalize(),
        amount=f"{float(course.price or 0):.2f}",
        course_url=f"{config['app_base_url']}/course.html?id={course.id}",
        dashboard_url=f"{config['app_base_url']}/dashboard.html",
        support_email=config["support_email"],
        app_name="Learning Management System",
        current_year=datetime.utcnow().year,
    )
    send_html_email(user.email, f"Welcome to {course.title}", html_body)


def send_new_lesson_email(user, course, lesson):
    config = _mail_config()
    html_body = render_template(
        "new_lesson_mail.html",
        user_name=user.name,
        course_title=course.title,
        lesson_title=lesson.title,
        lesson_order=lesson.lesson_order,
        course_url=f"{config['app_base_url']}/course.html?id={course.id}",
        support_email=config["support_email"],
        app_name="Learning Management System",
        current_year=datetime.utcnow().year,
    )
    send_html_email(user.email, f"New lesson added: {course.title}", html_body)


def send_pending_welcome_emails(limit: int = 20) -> dict:
    config = _mail_config()
    _validate_mail_config(config)

    jobs = (
        WelcomeEmailJob.query.filter(WelcomeEmailJob.status.in_(["pending", "failed"]))
        .order_by(WelcomeEmailJob.created_at.asc())
        .limit(limit)
        .all()
    )

    sent = 0
    failed = 0

    for job in jobs:
        try:
            html_body = _render_welcome_html(job, config)
            send_html_email(job.user.email, job.subject, html_body)
            job.status = "sent"
            job.sent_at = datetime.utcnow()
            job.last_error = None
            sent += 1
        except Exception as exc:
            job.status = "failed"
            job.last_error = str(exc)
            failed += 1
        finally:
            job.attempts += 1

    db.session.commit()

    return {
        "processed": len(jobs),
        "sent": sent,
        "failed": failed,
    }


def send_reset_password_email(user, reset_token: str):
    config = _mail_config()
    reset_link = f"{config['app_base_url']}/reset_password.html?token={reset_token}"
    html_body = render_template(
        "reset_password_mail.html",
        user_name=user.name,
        user_email=user.email,
        reset_link=reset_link,
        support_email=config["support_email"],
        app_name="Learning Management System",
        current_year=datetime.utcnow().year,
    )
    send_html_email(user.email, "Reset Your Password - Learning Management System", html_body)
