import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from twilio.rest import Client  
except ImportError: 
    Client = None 


def _str_to_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class TwilioConfig:
    account_sid: Optional[str]
    auth_token: Optional[str]
    from_number: Optional[str]
    enabled: bool


class TwilioNotificationService:
    """
    Simple wrapper around Twilio's REST client that also supports a mock mode
    so we can develop/test without live credentials.
    """

    def __init__(self) -> None:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")
        force_mock = _str_to_bool(os.getenv("TWILIO_FORCE_MOCK"))

        self.config = TwilioConfig(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            enabled=not force_mock
            and all([account_sid, auth_token, from_number, Client is not None]),
        )

        self._client: Optional[Client] = None
        if self.config.enabled and Client is not None:
            self._client = Client(account_sid, auth_token)
        else:
            logging.warning(
                "Twilio running in mock mode. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER "
                "and install twilio to enable real SMS delivery."
            )

    def send_sms(self, *, to: str, body: str) -> Dict[str, Any]:
        if not to:
            raise ValueError("Destination phone number is required.")
        if not body:
            raise ValueError("SMS body cannot be empty.")

        if self.config.enabled and self._client is not None:
            try:
                message = self._client.messages.create(
                    to=to,
                    from_=self.config.from_number,
                    body=body,
                )
                logging.info("Sent SMS via Twilio (sid=%s) to %s", message.sid, to)
                return {"status": "sent", "sid": message.sid}
            except Exception as exc:  # pragma: no cover - network side failures
                logging.exception("Failed to send SMS via Twilio: %s", exc)
                return {"status": "error", "error": str(exc)}

        logging.info("Mock SMS -> %s: %s", to, body)
        return {"status": "mocked"}


twilio_service = TwilioNotificationService()

