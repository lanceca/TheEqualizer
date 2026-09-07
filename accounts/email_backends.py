import json
import logging
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


class BrevoAPIEmailBackend(BaseEmailBackend):
    """
    Send Django email through Brevo's transactional HTTPS API.

    Existing send_mail(), EmailMessage, EmailMultiAlternatives, and Django's
    built-in password-reset views can continue using Django's email API.
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "BREVO_API_KEY", "").strip()

        if not api_key:
            if self.fail_silently:
                return 0
            raise RuntimeError("BREVO_API_KEY is not configured.")

        sent_count = 0

        for message in email_messages:
            try:
                self._send_message(message)
            except Exception:
                if self.fail_silently:
                    logger.exception("Brevo API email delivery failed.")
                    continue
                raise
            else:
                sent_count += 1

        return sent_count

    def _send_message(self, message):
        payload = self._build_payload(message)

        request = Request(
            getattr(
                settings,
                "BREVO_API_URL",
                "https://api.brevo.com/v3/smtp/email",
            ),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            method="POST",
        )

        timeout = getattr(settings, "BREVO_API_TIMEOUT", 10)

        try:
            with urlopen(request, timeout=timeout) as response:
                status = response.getcode()
                if not 200 <= status < 300:
                    raise RuntimeError(
                        f"Brevo API returned HTTP {status}."
                    )
        except HTTPError as exc:
            detail = self._read_http_error(exc)
            raise RuntimeError(
                f"Brevo API rejected the email (HTTP {exc.code}): {detail}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Could not connect to Brevo API: {exc.reason}"
            ) from exc

    def _build_payload(self, message):
        sender_name, sender_email = parseaddr(
            message.from_email or settings.DEFAULT_FROM_EMAIL
        )

        if not sender_email:
            raise ValueError("The sender email address is missing.")

        recipients = self._addresses(message.to)
        if not recipients:
            raise ValueError("The email has no valid recipients.")

        payload = {
            "sender": {"email": sender_email},
            "to": recipients,
            "subject": message.subject or "",
            "textContent": message.body or "",
        }

        if sender_name:
            payload["sender"]["name"] = sender_name

        cc = self._addresses(message.cc)
        if cc:
            payload["cc"] = cc

        bcc = self._addresses(message.bcc)
        if bcc:
            payload["bcc"] = bcc

        reply_to = self._addresses(message.reply_to)
        if reply_to:
            payload["replyTo"] = reply_to[0]

        html_content = self._extract_html(message)
        if html_content:
            payload["htmlContent"] = html_content

        return payload

    @staticmethod
    def _addresses(addresses):
        result = []

        for raw_address in addresses or []:
            name, email = parseaddr(raw_address)
            if not email:
                continue

            item = {"email": email}
            if name:
                item["name"] = name
            result.append(item)

        return result

    @staticmethod
    def _extract_html(message):
        alternatives = getattr(message, "alternatives", [])

        for alternative in alternatives:
            content = getattr(alternative, "content", None)
            mimetype = getattr(alternative, "mimetype", None)

            if content is None:
                try:
                    content = alternative[0]
                    mimetype = alternative[1]
                except (TypeError, IndexError):
                    continue

            if mimetype == "text/html":
                return content

        return None

    @staticmethod
    def _read_http_error(exc):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            return str(exc.reason)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return body or str(exc.reason)

        return data.get("message") or body or str(exc.reason)
