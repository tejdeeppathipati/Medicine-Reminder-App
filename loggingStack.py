from datetime import date, datetime, timedelta

import pytz

# loggingStack.py
#making a ssumption that all of our users are in eastern time zone. 
#we can change this later to be dynamic based on user location.
EASTERN_TZ = pytz.timezone('America/New_York')

async def log_medicine_event(userPhone, now=None):
    """
    this is creating a priorritized med stack which 
    help the logging logic of piled up meds waiting to be logged. 
    """
    stackMed = await mockDB.medicine.find({

        "userPhone": userPhone,
        "status": {"$in": ["pending", "missed"]}
    }).to_list(lenght=None) #this is going into the mongodb and checking if the data for the the specific user have the medicine is whic is 
    #status is pending meaning still hasnt been rolled our or have simply being missed. 
    if not stackMed:
        return []
    
    currentMedStack = []
    missedMedStack = []
    pendedMedStack = []

    now = now or datetime.now(EASTERN_TZ)

    for med in stackMed:
        time = med.get("time")
        hour, minute = map(int, time.split(':'))
        med_time = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute))

        medTime = EASTERN_TZ.localize(datetime(now.year, now.month, now.day, hour, minute, 0))

        if medTime < (now - timedelta(minutes=30)):
         med["status"] = "missed"
         missedMedStack.append(med)
        elif medTime <= (now + timedelta(hours=2)):
         currentMedStack.append(med)
        else:
            pendedMedStack.append(med)
    
    currentMedStack.sort(key=lambda x: x['time'])
    missedMedStack.sort(key=lambda x: x['time'])
    pendedMedStack.sort(key=lambda x: x['time'])

    prioritizedStack =  missedMedStack + currentMedStack + pendedMedStack

    for i, med in enumerate(prioritizedStack, start =1):
        med['stack_position'] = i
    
    return prioritizedStack