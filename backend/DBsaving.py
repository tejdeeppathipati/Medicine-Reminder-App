from flask import Blueprint, request, jsonify
from datetime import datetime
import re
from pymongo import MongoClient

# DBsaving.py
# works on creating and updating users based on form submissions. this includes medicine and caregivers.
# form submissions from the frontend are processed here and checked before being saved to mongodb.
# we can also change this if additional user data is needed or to include dynamic validation rules.


user_setup_bp = Blueprint('user_setup', __name__)

from flask_cors import CORS
CORS(user_setup_bp)

# connection to mongodb
client = MongoClient('mongodb://localhost:27017/')
db = client['medication_reminder']
users = db['users']

# api routes begin below

@user_setup_bp.route('/api/user/setup', methods=['POST'])
def setup_user():
    """Create a new user with medications and optional caregivers"""
    data = request.get_json()
    print("Received data:", data) # test output

    # will normalize medication input provided
    if "medications" in data:
        for med in data["medications"]:
            if "time" in med:
                med["times"] = [med["time"]]
                del med["time"]

    # this checks the time given (accepting formats)
    for med in data.get("medications", []):
        new_times = []
        for t in med.get("times", []):
            try:
                # parsing as 12 hour time with AM or PM (not only 24 hour time)
                dt = datetime.strptime(t.strip(), "%I:%M %p")
                new_times.append(dt.strftime("%H:%M"))
            except ValueError:
                # if parsing fails, keep original time given
                new_times.append(t.strip())
        med["times"] = new_times
    
    # checks all requirements (determines if form is accepted or not)
    if not data.get('name'):
        return jsonify({'error': 'Name is required'})
    if not data.get('phone'):
        return jsonify({'error': 'Phone number is required'})
    if not data.get('medications'):
        return jsonify({'error': 'At least one medication is required'})
    
    # checks phone format specifically, does not allow incorrect formats
    if not re.match(r'^\+?1?\d{9,15}$', data['phone']):
        return jsonify({'error': 'Invalid phone number'})
    
    # checks correct medications
    for med in data['medications']:
        if not med.get('name') or not med.get('dosage') or not med.get('times'):
            return jsonify({'error': 'Medication must have name, dosage, and times'})
        
        for time in med['times']:
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time):
                return jsonify({'error': f'Invalid time format: {time}'})
    
    # checks caregivers if any are provided
    for caregiver in data.get('caregivers', []):
        if not caregiver.get('name') or not caregiver.get('phone'):
            return jsonify({'error': 'Caregiver must have name and phone'})
    
    # new user added to users collection - formatting
    user_id = f"user_{data['phone'].replace('+', '').replace(' ', '')}"
    user_data = {
        'user_id': user_id,
        'name': data['name'],
        'phone': data['phone'],
        'medications': data['medications'],
        'caregivers': data.get('caregivers', []),
        'created_at': datetime.utcnow()
    }
    # new user sent to db
    result = users.insert_one(user_data)
    print("inserted id:", result.inserted_id) # test
    
    return jsonify({'success': True, 'user_id': user_id, 'mongo_id': str(result.inserted_id)})

# getting user
@user_setup_bp.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information by custom user_id"""
    user = users.find_one({'user_id': user_id})
    if not user:
        return jsonify({'error': 'User not found'})
    
    # json serialization
    user['_id'] = str(user['_id'])
    # return correct user from data
    return jsonify(user)

# updating medicine
@user_setup_bp.route('/api/user/<user_id>/medications', methods=['PUT'])
def update_medications(user_id):
    """Update user medications"""
    data = request.get_json()
    if not data.get('medications'):
        return jsonify({'error': 'Medications list is required'})
    
    result = users.update_one(
        {'user_id': user_id},
        {'$set': {'medications': data['medications']}}
    )
    
    # check if user was actually found
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'})
    
    return jsonify({'success': True})

# updating caregivers
@user_setup_bp.route('/api/user/<user_id>/caregivers', methods=['PUT'])
def update_caregivers(user_id):
    """Update user caregivers"""
    data = request.get_json()
    
    result = users.update_one(
        {'user_id': user_id},
        {'$set': {'caregivers': data.get('caregivers', [])}} #
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'})
    
    return jsonify({'success': True})