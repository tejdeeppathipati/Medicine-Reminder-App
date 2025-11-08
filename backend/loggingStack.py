from datetime import date, datetime, timedelta
import pytz
from pymongo import MongoClient  

client = MongoClient('mongodb://localhost:27017/')
db = client['medication_reminder']
mockDB = {
    'user': db['users'],  
    'medicine': db['users']  
}

EASTERN_TZ = pytz.timezone('America/New_York')

def log_medicine_event(userPhone, now=None):
    """
    this is creating a priorritized med stack which 
    help the logging logic of piled up meds waiting to be logged. 
    """
    user = mockDB['user'].find_one({
        "phone": userPhone 
    })
    
    if not user or 'medications' not in user:
        return []
    
    stackMed = []
    for med in user.get('medications', []):
        status = med.get('status', 'pending')  
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

    now = now or datetime.now(EASTERN_TZ)

    for med in stackMed:
        time_str = med.get("time")
        try:
            hour, minute = map(int, time_str.split(':'))
            med_time = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute))
            medTime = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute, 0))

            if medTime < (now - timedelta(minutes=30)):
                med["status"] = "missed"
                missedMedStack.append(med)
            elif medTime <= (now + timedelta(hours=2)):
                currentMedStack.append(med)
            else:
                pendedMedStack.append(med)
        except (ValueError, AttributeError):
            continue
    
    currentMedStack.sort(key=lambda x: x['time'])
    missedMedStack.sort(key=lambda x: x['time'])
    pendedMedStack.sort(key=lambda x: x['time'])

    prioritizedStack = missedMedStack + currentMedStack + pendedMedStack

    for i, med in enumerate(prioritizedStack, start=1):
        med['stack_position'] = i
    
    return prioritizedStack
