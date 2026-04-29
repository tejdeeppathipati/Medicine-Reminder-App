import atexit
import logging
import os
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler 

from backend.db import users
from backend.notifications import twilio_service

DEFAULT_TZ = os.getenv("DEFAULT_TIMEZONE", "US/Eastern")
REMINDER_POLL_MINUTES = int(os.getenv("REMINDER_POLL_MINUTES", "1"))
REMINDER_WINDOW_MINUTES = int(os.getenv("REMINDER_WINDOW_MINUTES", "5"))
DAILY_SUMMARY_HOUR = int(os.getenv("CAREGIVER_DAILY_SUMMARY_HOUR", "20"))
WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}

try:
    DEFAULT_TIMEZONE = pytz.timezone(DEFAULT_TZ)
except Exception: 
    DEFAULT_TIMEZONE = pytz.timezone("US/Eastern")

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler(app) -> Optional[BackgroundScheduler]:
    global _scheduler

    if _scheduler and _scheduler.running:
        app.logger.info("Medication scheduler already running.")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=DEFAULT_TIMEZONE)
    _scheduler.add_job(
        func=_dispatch_due_reminders,
        trigger="interval",
        minutes=REMINDER_POLL_MINUTES,
        id="medication_reminders",
        max_instances=1,
        replace_existing=True,
        args=[app],
    )
    _scheduler.start()
    app.logger.info(
        "Medication reminder scheduler started (poll=%s min, window=%s min).",
        REMINDER_POLL_MINUTES,
        REMINDER_WINDOW_MINUTES,
    )

    atexit.register(lambda: _shutdown_scheduler(app))
    return _scheduler


def _shutdown_scheduler(app) -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        app.logger.info("Stopping medication reminder scheduler.")
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _get_timezone(user_tz: Optional[str]) -> pytz.timezone:
    if not user_tz:
        return DEFAULT_TIMEZONE
    try:
        return pytz.timezone(user_tz)
    except Exception:
        logging.warning("Unknown timezone '%s'. Falling back to default.", user_tz)
        return DEFAULT_TIMEZONE


def _parse_med_time(now: datetime, time_str: str, tz: pytz.timezone) -> Optional[datetime]:
    try:
        # Handle both 24-hour format (16:11) and 12-hour format (4:11pm)
        time_str = time_str.strip().lower()
        
        # Check if it's 12-hour format with am/pm
        is_pm = time_str.endswith('pm')
        is_am = time_str.endswith('am')
        
        if is_pm or is_am:
            # Remove am/pm suffix
            time_str = time_str[:-2].strip()
        
        # Parse hour and minute
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        
        # Convert to 24-hour format if needed
        if is_pm and hour != 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
        
        scheduled = tz.localize(
            datetime(now.year, now.month, now.day, hour, minute, 0)
        )
        return scheduled
    except Exception as e:
        logging.warning("Unable to parse medication time '%s'. Error: %s", time_str, str(e))
        return None


def _normalise_frequency(med: Dict[str, Any]) -> str:
    frequency = (med.get("frequency") or "Daily").strip().lower()
    if frequency in {"twice daily", "twice_daily", "twice-daily"}:
        return "twice daily"
    if frequency == "weekly":
        return "weekly"
    if frequency in {"as needed", "as_needed", "as-needed", "prn"}:
        return "as needed"
    return "daily"


def _med_is_scheduled_today(med: Dict[str, Any], now: datetime) -> bool:
    frequency = _normalise_frequency(med)
    if frequency == "as needed":
        return False
    if frequency != "weekly":
        return True

    days = med.get("days") or []
    if isinstance(days, str):
        days = [days]
    if not days:
        return True

    today = now.weekday()
    return any(WEEKDAY_ALIASES.get(str(day).strip().lower()) == today for day in days)


def _caregiver_wants(caregiver: Dict[str, Any], kind: str) -> bool:
    notify_when = (caregiver.get("notify_when") or "On missed dose").strip().lower()
    if notify_when == "both":
        return True
    if kind == "missed_dose":
        return notify_when == "on missed dose"
    if kind == "daily_summary":
        return notify_when == "daily summary"
    return False


def _build_message(user: Dict[str, Any], med: Dict[str, Any], when: str) -> str:
    name = user.get("name", "there")
    dosage = med.get("dosage", "").strip()
    dosage_str = f" ({dosage})" if dosage else ""
    return (
        f"Hi {name}, it's time to take {med.get('name', 'your medication')}"
        f"{dosage_str} scheduled for {when}. Reply with the number in your SMS stack to log it."
    )


def _check_missed_medications_and_alert_caregivers(app) -> None:
    """Check for missed medications and alert caregivers based on their preference."""
    with app.app_context():
        now = datetime.now(DEFAULT_TIMEZONE)
        today_key = now.strftime("%Y-%m-%d")
        
        cursor = users.find({"paused": {"$ne": True}})
        for user in cursor:
            phone = user.get("phone")
            caregivers = user.get("caregivers", [])
            
            if not phone or not caregivers:
                continue
            
            caregiver_alert_log = user.get("caregiver_alert_log", {})
            
            # Count missed medications
            missed_count = 0
            missed_meds = []
            tz = _get_timezone(user.get("timezone"))
            
            for med in user.get("medications", []):
                if not _med_is_scheduled_today(med, now):
                    continue

                status = med.get("status", "pending")
                for time_str in med.get("times", []):
                    med_dt = _parse_med_time(now, time_str, tz)
                    if not med_dt:
                        continue
                    
                    # If more than 3 minutes past med time and still pending, it's missed
                    if now > (med_dt + timedelta(minutes=3)) and status == "pending":
                        missed_count += 1
                        missed_meds.append(f"{med.get('name')} ({time_str})")
            
            if missed_count == 0:
                continue

            user_name = user.get("name", "The user")
            updates: Dict[str, Any] = {}

            alert_message = (
                f"Alert: {user_name} missed {missed_count} medication"
                f"{'s' if missed_count != 1 else ''}: {', '.join(missed_meds)}. "
                "Please check on them."
            )
            if caregiver_alert_log.get("missed_dose") != today_key:
                sent_any = False
                for caregiver in caregivers:
                    if not _caregiver_wants(caregiver, "missed_dose"):
                        continue
                    caregiver_phone = caregiver.get("phone")
                    if not caregiver_phone:
                        continue

                    result = twilio_service.send_sms(to=caregiver_phone, body=alert_message)
                    sent_any = True
                    app.logger.info(
                        "Missed-dose caregiver alert for %s to %s (%s) -> %s",
                        phone,
                        caregiver.get("name", "Caregiver"),
                        caregiver_phone,
                        result.get("status"),
                    )

                if sent_any:
                    updates["caregiver_alert_log.missed_dose"] = today_key

            summary_due = now.hour >= DAILY_SUMMARY_HOUR
            summary_message = (
                f"Daily summary: {user_name} missed {missed_count} medication"
                f"{'s' if missed_count != 1 else ''} today: {', '.join(missed_meds)}."
            )
            if summary_due and caregiver_alert_log.get("daily_summary") != today_key:
                sent_any = False
                for caregiver in caregivers:
                    if not _caregiver_wants(caregiver, "daily_summary"):
                        continue
                    caregiver_phone = caregiver.get("phone")
                    if not caregiver_phone:
                        continue

                    result = twilio_service.send_sms(to=caregiver_phone, body=summary_message)
                    sent_any = True
                    app.logger.info(
                        "Daily caregiver summary for %s to %s (%s) -> %s",
                        phone,
                        caregiver.get("name", "Caregiver"),
                        caregiver_phone,
                        result.get("status"),
                    )

                if sent_any:
                    updates["caregiver_alert_log.daily_summary"] = today_key

            if updates:
                users.update_one({"_id": user["_id"]}, {"$set": updates})


def _dispatch_due_reminders(app) -> None:
    with app.app_context():
        now = datetime.now(DEFAULT_TIMEZONE)
        window_start = now - timedelta(minutes=REMINDER_WINDOW_MINUTES)
        window_end = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)
        today_key = now.strftime("%Y-%m-%d")

        cursor = users.find({"paused": {"$ne": True}})
        for user in cursor:
            phone = user.get("phone")
            if not phone:
                continue

            meds: List[Dict[str, Any]] = deepcopy(user.get("medications", []))
            updated = False
            tz = _get_timezone(user.get("timezone"))

            for med in meds:
                if not _med_is_scheduled_today(med, now):
                    continue

                reminder_log: Dict[str, Any] = med.get("reminder_log", {})
                for time_str in med.get("times", []):
                    med_dt = _parse_med_time(now, time_str, tz)
                    if not med_dt:
                        continue
                    if reminder_log.get(time_str) == today_key:
                        continue
                    if not (window_start <= med_dt <= window_end):
                        continue

                    message = _build_message(user, med, time_str)
                    result = twilio_service.send_sms(to=phone, body=message)
                    app.logger.info(
                        "Reminder for %s (%s) at %s -> %s",
                        phone,
                        med.get("name"),
                        time_str,
                        result.get("status"),
                    )

                    reminder_log[time_str] = today_key
                    med["reminder_log"] = reminder_log
                    med["status"] = "pending"
                    med["last_reminder_at"] = datetime.utcnow()
                    updated = True

            if updated:
                users.update_one({"_id": user["_id"]}, {"$set": {"medications": meds}})
        
        # After sending reminders, check for missed meds and alert caregivers
        _check_missed_medications_and_alert_caregivers(app)
