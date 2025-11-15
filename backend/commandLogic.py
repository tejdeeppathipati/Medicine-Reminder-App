from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio
from aiParsing import aiParseMedicine
from loggingStack import medcineLoggingLogic
from DBsaving import users  
from pytz import timezone
from backend.notifications import twilio_service
from flask import Response

textD = Blueprint('textD', __name__)
EASTERN_TZ = timezone('US/Eastern')

def printingStack(stack):
    """Returns a clean, vertical stack display"""
    if not stack:
        return "No medications need logging right now."
    
    printingLog = ["Your medication stack:"]
    
    for med in stack:
        statusLog = "(missed)" if med['status'] == 'missed' else "(current)"
        printingLog.append(f"{med['stack_position']}. {med['medicine_name']} at {med['time']} {statusLog}")  
    
    printingLog.append("")  
    printingLog.append("Text the number to log that medication")
    
    return "\n".join(printingLog)

def commandLogic(userPhone, messageText):
    """
    Handles SMS commands: numeric logs, pause, resume, stop, edit, add.
    """
    medLogic = messageText.strip().lower()

  
    if medLogic.isdigit():
        return medTaken(userPhone, int(medLogic))

  
    elif medLogic == "pause":
        users.update_one({"phone": userPhone}, {"$set": {"paused": True}})
        return "Reminders paused successfully. Text 'resume' to continue reminders again."

   
    elif medLogic == "resume":
        users.update_one({"phone": userPhone}, {"$set": {"paused": False}})
        return "Reminders resumed successfully. You will continue receiving notifications."


    elif medLogic == "stop":
        result = users.delete_one({"phone": userPhone})
        if result.deleted_count > 0:
            return "Your account and all your data have been deleted. You will no longer receive reminders. Fill the form again to restart."
        else:
            return "No account found with this phone number."

    
    elif medLogic.startswith("edit") or medLogic.startswith("add"):
        medParsed = medLogic[4:].strip() if medLogic.startswith("edit") else medLogic[3:].strip()

        if not medParsed:
            return "Please specify the medicine details. Example: 'edit vitamin d 8 am monday'"

        try:
          
            aidata = aiParseMedicine(medParsed)
        except Exception as e:
            return f"Error during AI parsing: {e}"

        if not aidata:
            return "Failed to parse medicine details. Please ensure the format is correct."


        if medLogic.startswith("edit"):
            result = users.update_one(
                {
                    "phone": userPhone,
                    "medications.name": {"$regex": f"^{aidata['medicine_name']}$", "$options": "i"}
                },
                {
                    "$set": {
                        "medications.$.times": [aidata['time']],
                        "medications.$.day": aidata.get('day', "")
                    }
                }
            )
            if result.modified_count > 0:
                return f"Updated {aidata['medicine_name']} to {aidata['time']} {aidata.get('day', '')}."
            else:
                return f"No medicine named '{aidata['medicine_name']}' found to edit."

      
        elif medLogic.startswith("add"):
            newMed = {
                "name": aidata['medicine_name'],
                "times": [aidata['time']],
                "day": aidata.get('day', ""),
                "status": "pending"
            }
            result = users.update_one(
                {"phone": userPhone},
                {"$push": {"medications": newMed}}
            )
            if result.modified_count > 0:
                return f"Added new medicine: {aidata['medicine_name']} at {aidata['time']} {aidata.get('day', '')}."
            else:
                return "Failed to add medicine. User not found."


    else:
        return "Command not recognized. Please reply with a number, 'pause', 'resume', 'edit', 'add', or 'stop'."


def medTaken(userPhone, position):
    """Handles when a user texts a number to log medication."""
    stack = medcineLoggingLogic(userPhone)
    medicineLog = None

    for med in stack:
        if med.get('stack_position') == position:
            medicineLog = med
            break

    if not medicineLog:
        return f"Position {position} not found.\n\n{printingStack(stack)}"

    result = users.update_one(
        {
            "phone": userPhone,
            "medications.name": medicineLog['medicine_name']
        },
        {
            "$set": {
                "medications.$.status": "taken",
                "medications.$.taken_at": datetime.now(EASTERN_TZ)
            }
        }
    )

    if result.modified_count > 0:
        newStack = medcineLoggingLogic(userPhone)
        if newStack: 
            return f"Logged {medicineLog['medicine_name']}!\n\n{printingStack(newStack)}"  
        else:
            return f"Logged {medicineLog['medicine_name']}!\n\nAll medications completed."
    else:
        return f"Failed to log {medicineLog['medicine_name']}"


# @textD.route('/api/sms/handle', methods=['POST'])
# def handle_sms():
#     """Receives SMS from Twilio webhook or curl request."""
#     data = request.get_json(silent=True) or request.form
#     user_phone = data.get('From') or data.get('phone')
#     message_text = data.get('Body') or data.get('message')

#     if not user_phone or not message_text:
#         return jsonify({'error': 'Missing phone or message'}), 400

#     response = commandLogic(user_phone, message_text)
#     #twilio_service.send_sms(to=user_phone, body=response)
#     #return jsonify({'response': response})
#     twiml = f"<Response><Message>{response}</Message></Response>"
#     return Response(twiml, mimetype="text/xml")

@textD.route('/api/sms/handle', methods=['POST'])
def handle_sms():
    """Receives SMS from Twilio webhook or curl request."""
    data = request.form.to_dict()
    if not data:
        json_data = request.get_json(silent=True)
        if json_data:
            data = json_data

    user_phone = data.get('From') or data.get('phone')
    message_text = data.get('Body') or data.get('message')

    if not user_phone or not message_text:
        return jsonify({'error': 'Missing phone or message'}), 400

    response_text = commandLogic(user_phone, message_text)
    twiml = f"<Response><Message>{response_text}</Message></Response>"
    return Response(twiml, mimetype="text/xml")

