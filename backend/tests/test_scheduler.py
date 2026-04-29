"""
Unit tests for the medication reminder scheduler.
"""
import unittest
from datetime import datetime
import pytz

from backend.scheduler import (
    _parse_med_time,
    _build_message,
    _get_timezone,
    _med_is_scheduled_today,
    _caregiver_wants,
    DEFAULT_TIMEZONE,
)

class TestScheduler(unittest.TestCase):
    """Test cases for scheduler helper functions"""

    def setUp(self):
        self.tz = pytz.timezone("US/Eastern")
        self.now = self.tz.localize(datetime(2025, 11, 16, 9, 0, 0))

    def test_parse_med_time_24hour(self):
        result = _parse_med_time(self.now, "09:15", self.tz)
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 15)

    def test_parse_med_time_12hour_am(self):
        result = _parse_med_time(self.now, "9:15am", self.tz)
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 15)

    def test_parse_med_time_12hour_pm(self):
        result = _parse_med_time(self.now, "2:30pm", self.tz)
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_parse_med_time_invalid_string_returns_none(self):
        # Completely invalid time should be skipped by scheduler
        self.assertIsNone(_parse_med_time(self.now, "not-a-time", self.tz))
        self.assertIsNone(_parse_med_time(self.now, "", self.tz))

    def test_build_message_contains_all_fields(self):
        user = {"name": "John"}
        med = {"name": "Vitamin D", "dosage": "50mg"}
        when = "09:15"

        message = _build_message(user, med, when)
        self.assertIn("John", message)
        self.assertIn("Vitamin D", message)
        self.assertIn("50mg", message)
        self.assertIn("09:15", message)

    def test_get_timezone_default(self):
        result = _get_timezone(None)
        self.assertEqual(result, DEFAULT_TIMEZONE)

    def test_get_timezone_valid_custom(self):
        london = _get_timezone("Europe/London")
        self.assertEqual(london, pytz.timezone("Europe/London"))

    def test_get_timezone_invalid_falls_back_to_default(self):
        result = _get_timezone("Not/ARealZone")
        self.assertEqual(result, DEFAULT_TIMEZONE)

    def test_daily_med_is_scheduled_every_day(self):
        self.assertTrue(_med_is_scheduled_today({"frequency": "Daily"}, self.now))

    def test_twice_daily_med_is_scheduled_every_day(self):
        self.assertTrue(_med_is_scheduled_today({"frequency": "Twice daily"}, self.now))

    def test_as_needed_med_is_not_scheduled(self):
        self.assertFalse(_med_is_scheduled_today({"frequency": "As needed"}, self.now))

    def test_weekly_med_only_schedules_on_selected_day(self):
        sunday = self.tz.localize(datetime(2025, 11, 16, 9, 0, 0))
        self.assertTrue(
            _med_is_scheduled_today({"frequency": "Weekly", "days": ["Sun"]}, sunday)
        )
        self.assertFalse(
            _med_is_scheduled_today({"frequency": "Weekly", "days": ["Mon"]}, sunday)
        )

    def test_caregiver_notification_preferences(self):
        self.assertTrue(_caregiver_wants({"notify_when": "On missed dose"}, "missed_dose"))
        self.assertFalse(_caregiver_wants({"notify_when": "On missed dose"}, "daily_summary"))
        self.assertTrue(_caregiver_wants({"notify_when": "Daily summary"}, "daily_summary"))
        self.assertTrue(_caregiver_wants({"notify_when": "Both"}, "missed_dose"))
        self.assertTrue(_caregiver_wants({"notify_when": "Both"}, "daily_summary"))


if __name__ == "__main__":
    unittest.main()
