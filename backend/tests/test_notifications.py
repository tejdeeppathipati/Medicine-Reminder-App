"""
Unit tests for the Twilio notification service.
"""
import unittest
from unittest.mock import patch, MagicMock
import os

from backend.notifications import TwilioNotificationService


class TestTwilioNotificationService(unittest.TestCase):
    """Test cases for TwilioNotificationService"""

    @patch.dict(
        os.environ,
        {
            "TWILIO_ACCOUNT_SID": "ACxxxx",
            "TWILIO_AUTH_TOKEN": "secret",
            "TWILIO_FROM_NUMBER": "whatsapp:+14155238886",
        },
        clear=True,
    )
    @patch("backend.notifications.Client")
    def test_phone_number_normalization(self, mock_client):
        """Phone numbers are normalized to WhatsApp before sending"""
        # Fake Twilio message object
        message = MagicMock()
        message.sid = "SM123"
        mock_client.return_value.messages.create.return_value = message

        service = TwilioNotificationService()
        result = service.send_sms(to="+17034532810", body="Test")

        # Twilio client should be called with whatsapp:+...
        mock_client.return_value.messages.create.assert_called_once_with(
            to="whatsapp:+17034532810",
            from_="whatsapp:+14155238886",
            body="Test",
        )
        self.assertEqual(result.get("status"), "sent")
        self.assertEqual(result.get("sid"), "SM123")

    def test_mock_mode_when_creds_missing(self):
        """Mock mode is used when Twilio credentials are missing"""
        with patch.dict(os.environ, {}, clear=True):
            service = TwilioNotificationService()
            result = service.send_sms(to="+17034532810", body="Test")
            self.assertEqual(result.get("status"), "mocked")

    def test_send_sms_validation(self):
        """Empty phone numbers and messages are rejected"""
        with patch.dict(os.environ, {}, clear=True):
            service = TwilioNotificationService()

        with self.assertRaises(ValueError):
            service.send_sms(to="", body="Test")

        with self.assertRaises(ValueError):
            service.send_sms(to="+17034532810", body="")


if __name__ == "__main__":
    unittest.main()
