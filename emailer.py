import logging
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_digest(jobs: list[dict]) -> None:
    sender = os.environ["SMTP_ADDRESS"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", sender)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Finance Jobs Digest — {date.today().isoformat()} ({len(jobs)} new)"
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(_build_plain(jobs), "plain"))
    msg.attach(MIMEText(_build_html(jobs), "html"))

    with smtplib.SMTP("smtp-mail.outlook.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender, password)
        smtp.sendmail(sender, recipient, msg.as_string())
    logger.info(f"Sent digest with {len(jobs)} jobs to {recipient}")


def _build_plain(jobs: list[dict]) -> str:
    lines = [f"New finance jobs in Canada — {date.today().isoformat()}\n"]
    for j in jobs:
        lines.append(f"{j['company']} | {j['title']} | {j['location']}")
        lines.append(f"  {j['link']}\n")
    return "\n".join(lines)


def _build_html(jobs: list[dict]) -> str:
    by_company: dict[str, list[dict]] = {}
    for j in jobs:
        by_company.setdefault(j["company"], []).append(j)

    rows = []
    for company, company_jobs in sorted(by_company.items()):
        for j in company_jobs:
            rows.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;color:#c8102e">{company}</td>
          <td style="padding:8px;border-bottom:1px solid #eee">
            <a href="{j['link']}" style="color:#1a0dab;text-decoration:none">{j['title']}</a>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555">{j['location']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#888;font-size:12px">{j.get('posted', '')}</td>
        </tr>""")

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#333;max-width:800px;margin:auto">
  <h2 style="border-bottom:2px solid #c8102e;padding-bottom:8px">
    New Finance Jobs in Canada
    <span style="font-size:14px;color:#666;font-weight:normal">— {date.today().isoformat()}</span>
  </h2>
  <p>{len(jobs)} new posting(s) found today.</p>
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr style="background:#f5f5f5">
        <th style="padding:8px;text-align:left">Company</th>
        <th style="padding:8px;text-align:left">Role</th>
        <th style="padding:8px;text-align:left">Location</th>
        <th style="padding:8px;text-align:left">Posted</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p style="color:#888;font-size:12px;margin-top:24px">
    Automated digest from FinancialBot. Jobs filtered for Canada + entry-level keywords.
  </p>
</body>
</html>"""
