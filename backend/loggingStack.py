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

def medcineLoggingLogic(userPhone, now=None):
    """
    this is creating a priorritized med stack which 
    help the logging logic of piled up meds waiting to be logged. 
    """
    user = mockDB['user'].find_one({
        "phone": userPhone 
    })
    
    if not user or 'medications' not in user:
        return []
    
    caregivers = user.get('caregivers', [])
    
    stackMed = []
    for med in user.get('medications', []):
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

    now = now or datetime.now(EASTERN_TZ)
    print(f" CURRENT TIME: {now}")
    print(f" ALL MEDICATIONS: {user.get('medications', [])}")
    

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
    
    if len(missedMedStack) >= 3 and caregivers:
        careMed = [med['medicine_name'] for med in missedMedStack]
        user_name = user.get('name', 'The user')
        
        careAlert = f"Alert: {user_name} has missed {len(missedMedStack)} medications: {', '.join(careMed)}. Please check on them."
        
        for caregiver in caregivers:
            print(f"CAREGIVER ALERT to {caregiver['name']} ({caregiver['phone']}): {careAlert}")
    
    currentMedStack.sort(key=lambda x: x['time'])
    missedMedStack.sort(key=lambda x: x['time'])
    pendedMedStack.sort(key=lambda x: x['time'])

    prioritizedStack = missedMedStack + currentMedStack + pendedMedStack
    
    stack_position = 1
    for med in prioritizedStack:
        med['stack_position'] = stack_position 
        stack_position += 1                     
    
    return prioritizedStack
