from datetime import date, datetime, timedelta
import pytz
import re
from backend.db import users as users_collection
from backend.notifications import twilio_service

EASTERN_TZ = pytz.timezone('America/New_York')
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

def normalize_phone(phone):
    """Remove 'whatsapp:' prefix if present"""
    if phone and phone.lower().startswith("whatsapp:"):
        return phone[9:] 
    return phone

def normalize_caregiver_phone(phone):
    """
    Normalize caregiver phone number for WhatsApp sending.
    Removes whatsapp: prefix and ensures + is present.
    send_sms will add whatsapp: prefix back.
    """
    if not phone:
        return phone
    # Remove whatsapp: prefix if present
    digits = phone.strip()
    if digits.lower().startswith("whatsapp:"):
        digits = digits[9:].strip()
    # Remove any non-digit characters except +
    digits_only = re.sub(r'[^\d+]', '', digits)
    # Ensure it starts with + (send_sms expects this format)
    if not digits_only.startswith("+"):
        # Add +1 for US numbers (10 digits) or + for numbers starting with 1
        if len(digits_only) == 10:
            digits_only = f"+1{digits_only}"
        elif digits_only.startswith("1") and len(digits_only) == 11:
            digits_only = f"+{digits_only}"
        else:
            digits_only = f"+{digits_only}" if digits_only else digits_only
    # Return without whatsapp: prefix - send_sms will add it
    return digits_only

def med_is_scheduled_today(med, now):
    frequency = (med.get("frequency") or "Daily").strip().lower()
    if frequency in {"as needed", "as_needed", "as-needed", "prn"}:
        return False
    if frequency != "weekly":
        return True

    days = med.get("days") or []
    if isinstance(days, str):
        days = [days]
    if not days:
        return True

    return any(WEEKDAY_ALIASES.get(str(day).strip().lower()) == now.weekday() for day in days)

def caregiver_wants_missed_alert(caregiver):
    notify_when = (caregiver.get("notify_when") or "On missed dose").strip().lower()
    return notify_when in {"on missed dose", "both"}

def medcineLoggingLogic(userPhone, now=None):
    """
    this is creating a priorritized med stack which 
    help the logging logic of piled up meds waiting to be logged. 
    """
    # Normalize phone number (remove whatsapp: prefix if present)
    userPhone = normalize_phone(userPhone)
    user = users_collection.find_one({
        "phone": userPhone 
    })
    
    if not user or 'medications' not in user:
        return []
    
    caregivers = user.get('caregivers', [])
    
    now = now or datetime.now(EASTERN_TZ)
    stackMed = []
    for med in user.get('medications', []):
        if not med_is_scheduled_today(med, now):
            continue

        status = med.get('status', 'pending') 
        print(f" {med['name']} at {med['times']} - status: {status}")
 
        if status in ['pending', 'missed']:
            times = med.get('times', [])
            for time_str in times:
                stackMed.append({
                    'medicine_name': med['name'],  
                    'time': time_str,
                    'dosage': med.get('dosage', ''),
                    'status': status,
                    'userPhone': userPhone,
                    'original_med': med
                })
    
    if not stackMed:
        return []
    
    currentMedStack = []
    missedMedStack = []
    pendedMedStack = []

    print(f" CURRENT TIME: {now}")
    print(f" ALL MEDICATIONS: {user.get('medications', [])}")
    

    for med in stackMed:
        time_str = med.get("time")
        try:
            hour, minute = map(int, time_str.split(':'))
            med_time = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute))
            medTime = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute, 0))

            if medTime < (now - timedelta(minutes=3)):
                med["status"] = "missed"
                missedMedStack.append(med)
            elif medTime <= (now + timedelta(hours=2)):
                currentMedStack.append(med)
            else:
                pendedMedStack.append(med)
        except (ValueError, AttributeError):
            continue
    
    if len(missedMedStack) >= 3 and caregivers:
        careMed = [med['medicine_name'] for med in missedMedStack]
        user_name = user.get('name', 'The user')
        
        careAlert = f"Alert: {user_name} has missed {len(missedMedStack)} medications: {', '.join(careMed)}. Please check on them."
        
        for caregiver in caregivers:
            if not caregiver_wants_missed_alert(caregiver):
                continue

            caregiver_phone = caregiver.get('phone')
            if not caregiver_phone:
                print(f"WARNING: Caregiver {caregiver.get('name', 'Unknown')} has no phone number")
                continue
            
            # Debug: Print original phone format
            print(f"DEBUG: Original caregiver phone: '{caregiver_phone}' (type: {type(caregiver_phone)})")
            
            # Normalize caregiver phone number for WhatsApp
            normalized_phone = normalize_caregiver_phone(caregiver_phone)
            print(f"DEBUG: Normalized caregiver phone: '{normalized_phone}'")
            
            # Send message and capture result
            result = twilio_service.send_sms(to=normalized_phone, body=careAlert)
            caregiver_name = caregiver.get('name', 'Caregiver')
            
            print(f"DEBUG: Twilio result: {result}")
            
            if result.get('status') == 'sent':
                print(f"✓ CAREGIVER ALERT SENT to {caregiver_name} ({normalized_phone}): {careAlert}")
            elif result.get('status') == 'error':
                print(f"✗ CAREGIVER ALERT FAILED to {caregiver_name} ({normalized_phone}): {result.get('error', 'Unknown error')}")
            else:
                print(f"CAREGIVER ALERT (mocked) to {caregiver_name} ({normalized_phone}): {careAlert}")
    
    currentMedStack.sort(key=lambda x: x['time'])
    missedMedStack.sort(key=lambda x: x['time'])
    pendedMedStack.sort(key=lambda x: x['time'])

    prioritizedStack = missedMedStack + currentMedStack + pendedMedStack
    
    stack_position = 1
    for med in prioritizedStack:
        med['stack_position'] = stack_position 
        stack_position += 1                     
    
    return prioritizedStack
