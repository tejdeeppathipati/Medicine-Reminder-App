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


def _build_message(user: Dict[str, Any], med: Dict[str, Any], when: str) -> str:
    name = user.get("name", "there")
    dosage = med.get("dosage", "").strip()
    dosage_str = f" ({dosage})" if dosage else ""
    return (
        f"Hi {name}, it's time to take {med.get('name', 'your medication')}"
        f"{dosage_str} scheduled for {when}. Reply with the number in your SMS stack to log it."
    )


def _check_missed_medications_and_alert_caregivers(app) -> None:
    """Check for users with 3+ missed medications and alert their caregivers"""
    with app.app_context():
        now = datetime.now(DEFAULT_TIMEZONE)
        today_key = now.strftime("%Y-%m-%d")
        
        cursor = users.find({"paused": {"$ne": True}})
        for user in cursor:
            phone = user.get("phone")
            caregivers = user.get("caregivers", [])
            
            if not phone or not caregivers:
                continue
            
            # Check if we already alerted caregivers today
            last_caregiver_alert = user.get("last_caregiver_alert_date")
            if last_caregiver_alert == today_key:
                continue
            
            # Count missed medications
            missed_count = 0
            missed_meds = []
            tz = _get_timezone(user.get("timezone"))
            
            for med in user.get("medications", []):
                status = med.get("status", "pending")
                for time_str in med.get("times", []):
                    med_dt = _parse_med_time(now, time_str, tz)
                    if not med_dt:
                        continue
                    
                    # If more than 3 minutes past med time and still pending, it's missed
                    if now > (med_dt + timedelta(minutes=3)) and status == "pending":
                        missed_count += 1
                        missed_meds.append(f"{med.get('name')} ({time_str})")
            
            # Alert caregivers if 3+ meds missed
            if missed_count >= 3:
                user_name = user.get("name", "The user")
                alert_message = (
                    f"Alert: {user_name} has missed {missed_count} medications: "
                    f"{', '.join(missed_meds)}. Please check on them."
                )
                
                for caregiver in caregivers:
                    caregiver_phone = caregiver.get("phone")
                    if not caregiver_phone:
                        continue
                    
                    result = twilio_service.send_sms(to=caregiver_phone, body=alert_message)
                    app.logger.info(
                        "Caregiver alert for %s to %s (%s) -> %s",
                        phone,
                        caregiver.get("name", "Caregiver"),
                        caregiver_phone,
                        result.get("status"),
                    )
                
                # Mark that we alerted caregivers today
                users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_caregiver_alert_date": today_key}}
                )


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
