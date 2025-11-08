from flask import Blueprint, request, jsonify
from datetime import datetime
import pytz
import os
import asyncio
from pymongo import MongoClient
from flask_cors import CORS


from loggingStack import log_medicine_event
from aiParsing import ai_parse_medicine_message


client = MongoClient('mongodb://localhost:27017/')
db = client['medication_reminder']
mockDB = {
    'user': db['users'],
    'medicine': db['users']  
}

EASTERN_TZ = pytz.timezone('America/New_York')


textD = Blueprint('sms', __name__)
CORS(textD)


async def commandLogic(userPhone, messageText):
    """ code will tackle the logic of users logging the medicines as taken, or using the 
    commands such as pause, edit, stop to manage their reminder application   """

    medLogic = messageText.strip().lower()
    
  
    if medLogic.isdigit():
        return await medTaken(userPhone, int(medLogic)) 

    
    elif medLogic == "pause":
        await mockDB['user'].update_one({"phone": userPhone}, {"$set": {"paused": True}})
        return "Reminders paused successfully. Text 'resume' to continue reminders again."


    elif medLogic == "resume":
        await mockDB['user'].update_one({"phone": userPhone}, {"$set": {"paused": False}})
        return "Reminders resumed successfully. You will continue receiving notifications."

  
    elif medLogic == "stop":
        recieve = await mockDB['user'].delete_one({"phone": userPhone})
        if recieve.deleted_count > 0:
            return "Your account and all your data have been deleted. You will no longer receive reminders. Fill the form to start again."
        else: 
            return "No account found with this phone number."

    elif medLogic.startswith("edit") or medLogic.startswith("add"):
        medParsed = medLogic[4:].strip() if medLogic.startswith("edit") else medLogic[3:].strip()
        
        if not medParsed: 
            return "Please specify the medicine details. Example: 'edit vitamin d 8 am monday'"
            
        aidata = await ai_parse_medicine_message(medParsed) 
        if not aidata:
            return "Failed to parse medicine details. Please ensure the format is correct."
            
        if medLogic.startswith("edit"):
            recieve = await mockDB['user'].update_one(
                {
                    "phone": userPhone,
                    "medications.name": {"$regex": f"^{aidata['medicine_name']}$", "$options": "i"}
                },
                {
                    "$set": {
                        "medications.$.times": [aidata['time']],  
                        "medications.$.day": aidata['day'] or "" 
                    }
                }
            )
            if recieve.modified_count > 0:
                return f"Updated {aidata['medicine_name']} to {aidata['time']} {aidata['day'] or ''}."
            else:
                return f"No medicine named '{aidata['medicine_name']}' found to edit."
                
        elif medLogic.startswith("add"):
            newMed = {
                "name": aidata['medicine_name'],
                "times": [aidata['time']],
                "day": aidata['day'] or "",
                "status": "pending"
            }
            recieve = await mockDB['user'].update_one(
                {"phone": userPhone},
                {"$push": {"medications": newMed}}
            )
            if recieve.modified_count > 0:
                return f"Added new medicine: {aidata['medicine_name']} at {aidata['time']} {aidata['day'] or ''}."
            else:
                return "Failed to add medicine. User not found."


    else:
        return "Command not recognized. Please reply with a number, 'pause', 'resume', 'edit', 'add', or 'stop'."


async def medTaken(userPhone, position):
    """Handle when user texts a number to log medication"""
    stack = await log_medicine_event(userPhone)
    

    medicine_to_log = None
    for med in stack:
        if med.get('stack_position') == position:
            medicine_to_log = med
            break
    
    if not medicine_to_log:
        return f"No medicine found at position {position}"
    

    recieve = await mockDB['user'].update_one(
        {
            "phone": userPhone,
            "medications.name": medicine_to_log['medicine_name']
        },
        {
            "$set": {
                "medications.$.status": "taken",
                "medications.$.taken_at": datetime.now(EASTERN_TZ)
            }
        }
    )
    
    if recieve.modified_count > 0:
        return f"Logged {medicine_to_log['medicine_name']} as taken!"
    else:
        return f"Failed to log {medicine_to_log['medicine_name']}"


def async_handler(async_func):
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper


@textD.route('/api/sms/handle', methods=['POST'])
@async_handler
async def handle_sms():
    data = request.get_json()
    user_phone = data.get('From') or data.get('phone')
    message_text = data.get('Body') or data.get('message')
    
    if not user_phone or not message_text:
        return jsonify({'error': 'Missing phone or message'}), 400
    
    response = await commandLogic(user_phone, message_text)
    return jsonify({'response': response})