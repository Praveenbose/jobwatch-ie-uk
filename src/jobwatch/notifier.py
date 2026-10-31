"""Build and send the email digest. Credentials come from environment variables only."""
import html
import os
import smtplib
from email.message import EmailMessage
from typing import List, Tuple

from .filters import classify_level, visa_signal
from .models import Job


def build_digest(matches: List[Tuple[Job, int, List[str]]]) -> Tuple[str, str, str]:
    matches = sorted(matches, key=lambda m: -m[1])
    subject = f"{len(matches)} new job{'s' if len(matches) != 1 else ''} in Ireland/UK"
    text_lines, html_rows = [], []
    for job, score, reasons in matches:
        meta = f"{job.company} | {job.location or 'n/a'} | {classify_level(job.title)} | visa: {visa_signal(job)}"
        text_lines.append(f"- {job.title}\n  {meta}\n  {job.url}\n  why: {', '.join(reasons)}")
        html_rows.append(
            f"<li><a href='{html.escape(job.url)}'><b>{html.escape(job.title)}</b></a><br>"
            f"<small>{html.escape(meta)}<br><i>why: {html.escape(', '.join(reasons))}</i></small></li>")
    return subject, "\n\n".join(text_lines), "<ul>" + "".join(html_rows) + "</ul>"


def send_email(to_addr: str, subject: str, text: str, html_body: str) -> None:
    host, user = os.environ["SMTP_HOST"], os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ.get("MAIL_FROM", user), to_addr
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
