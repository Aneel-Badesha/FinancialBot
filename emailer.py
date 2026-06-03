import base64
import logging
import os
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
_BASE = Path(__file__).parent


def _get_service():
    token_path = _BASE / "token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds.valid:
            if creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    creds = _run_consent(token_path)
            else:
                creds = _run_consent(token_path)
    else:
        creds = _run_consent(token_path)
    return build("gmail", "v1", credentials=creds)


def _run_consent(token_path: Path) -> Credentials:
    flow = InstalledAppFlow.from_client_secrets_file(str(_BASE / "credentials.json"), SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\nAuthorize the app:\n{auth_url}\n")
    code = input("Enter the authorization code: ")
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def send_digest(jobs: list[dict]) -> None:
    recipient = os.environ.get("RECIPIENT_EMAIL", "")
    if not recipient:
        raise ValueError("RECIPIENT_EMAIL not set in environment")

    msg = EmailMessage()
    msg["Subject"] = f"Finance Jobs Digest — {date.today().isoformat()} ({len(jobs)} new)"
    msg["To"] = recipient
    msg.set_content(_build_plain(jobs))
    msg.add_alternative(_build_html(jobs), subtype="html")

    service = _get_service()
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Sent digest with {len(jobs)} jobs to {recipient} (id={result.get('id')})")


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
    Automated digest from FinancialBot. Jobs filtered for Canada + entry-level keywords.<br>
    <a href="https://aneel-badesha.github.io/FinancialBot" style="color:#1a0dab">View full job board →</a>
  </p>
</body>
</html>"""
