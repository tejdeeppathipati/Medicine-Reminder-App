
# test_medication_system.py
import asyncio
from datetime import datetime, timedelta

# Mock database instead of real MongoDB
class MockDB:
    def __init__(self):
        self.medicines = []
        self.users = []
    
    def create_test_data(self):
        # Sarah's test medicines
        self.medicines = [
            {
                "_id": "1",
                "user_phone": "555-1234",
                "name": "Vitamin A",
                "scheduled_time": "08:00",
                "scheduled_days": ["monday", "thursday"],
                "status": "pending",
                "last_reminder_sent": datetime.now()
            },
            {
                "_id": "2", 
                "user_phone": "555-1234",
                "name": "Diabetes Med",
                "scheduled_time": "12:00",
                "scheduled_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "status": "pending",
                "last_reminder_sent": datetime.now()
            },
            {
                "_id": "3",
                "user_phone": "555-1234", 
                "name": "Omega 3",
                "scheduled_time": "16:00",
                "scheduled_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "status": "missed",  # Simulate a missed medicine
                "last_reminder_sent": datetime.now() - timedelta(hours=2)
            }
        ]
        
        self.users = [
            {
                "phone": "555-1234",
                "name": "Sarah",
                "caregiver_phone": "555-5678"
            }
        ]

mock_db = MockDB()
mock_db.create_test_data()

# Mock the Medicine class to use our test data
class MockMedicine:
    @staticmethod
    async def find_by_user_phone(user_phone):
        return [med for med in mock_db.medicines if med["user_phone"] == user_phone]
    
    @staticmethod
    async def update_status(medicine_id, status):
        for med in mock_db.medicines:
            if med["_id"] == medicine_id:
                med["status"] = status
                print(f"✅ Updated {med['name']} to status: {status}")
                break
    
    @staticmethod 
    async def update_all_status(user_phone, status):
        for med in mock_db.medicines:
            if med["user_phone"] == user_phone:
                med["status"] = status
        print(f"✅ Updated all medicines for {user_phone} to: {status}")
# test_stacking.py
async def is_medicine_due(medicine):
    # For testing, always return True to see stacking work
    return True

async def build_medication_stack(user_phone):
    # 1. Fetch user's medicines from MOCK DB
    all_meds = await MockMedicine.find_by_user_phone(user_phone)
    
    # 2. Filter for CURRENT pending/missed medicines
    current_stack = []
    
    for med in all_meds:
        if med["status"] in ["pending", "missed"]:
            # Use our test version that always returns True
            if await is_medicine_due(med):
                current_stack.append(med)
    
    # 3. Sort: missed medicines FIRST, then by time
    current_stack.sort(key=lambda x: (0 if x["status"] == "missed" else 1, x["scheduled_time"]))
    
    # 4. Assign numbers dynamically
    numbered_stack = []
    for index, med in enumerate(current_stack, 1):
        med["current_number"] = index
        numbered_stack.append(med)
    
    return numbered_stack

async def generate_reminder_sms(user_phone):
    stack = await build_medication_stack(user_phone)
    
    if not stack:
        return "No medicines due right now."
    
    message_lines = [f"Sarah, take your medicines:"]
    
    for med in stack:
        status_note = " (missed!)" if med["status"] == "missed" else ""
        message_lines.append(f"{med['current_number']}. {med['name']}{status_note}")
    
    message_lines.append("Reply with the number corresponding to the medicine you took.")
    
    return "\n".join(message_lines)

# test_commands.py
async def handle_user_reply(user_phone, user_reply):
    # Get CURRENT stack
    current_stack = await build_medication_stack(user_phone)
    
    print(f"📱 User {user_phone} replied: '{user_reply}'")
    print(f"📊 Current stack has {len(current_stack)} medicines")
    
    # Check for simple number replies
    try:
        selected_number = int(user_reply.strip())
        
        # Find which medicine corresponds to THIS number
        selected_med = None
        for med in current_stack:
            if med["current_number"] == selected_number:
                selected_med = med
                break
        
        if selected_med:
            await MockMedicine.update_status(selected_med["_id"], "taken")
            return f"Logged {selected_med['name']} as taken!"
        else:
            return "Invalid number. Please reply with 1, 2, etc."
            
    except ValueError:
        # Handle text commands
        return await handle_text_command(user_phone, user_reply.lower())

async def handle_text_command(user_phone, command):
    if command in ['1', 'taken', 'yes']:
        current_stack = await build_medication_stack(user_phone)
        for med in current_stack:
            await MockMedicine.update_status(med["_id"], "taken")
        return "Logged all medicines as taken!"
    
    elif command in ['2', 'missed', 'no']:
        current_stack = await build_medication_stack(user_phone)
        for med in current_stack:
            await MockMedicine.update_status(med["_id"], "missed")
        return "Marked all as missed. We'll remind you later."
    
    elif command in ['pause', 'stop', 'hold']:
        await MockMedicine.update_all_status(user_phone, "paused")
        return "Medication reminders paused. Text 'resume' to restart."
    
    elif command in ['resume', 'start', 'restart']:
        await MockMedicine.update_all_status(user_phone, "pending")
        return "Medication reminders resumed!"
    
    else:
        # Mock AI parser for testing
        return f"AI would parse: '{command}'"
    

    # run_tests.py
async def run_test_scenarios():
    print("🧪 STARTING MEDICATION SYSTEM TESTS\n")
    
    user_phone = "555-1234"
    
    # Test 1: Show initial stack
    print("1. 📋 INITIAL STACK:")
    sms_message = await generate_reminder_sms(user_phone)
    print(sms_message)
    print()
    
    # Test 2: User replies with number
    print("2. 🔢 USER REPLIES '1':")
    response = await handle_user_reply(user_phone, "1")
    print(f"Response: {response}")
    print()
    
    # Test 3: Show updated stack
    print("3. 📋 UPDATED STACK AFTER '1':")
    sms_message = await generate_reminder_sms(user_phone)
    print(sms_message)
    print()
    
    # Test 4: User replies with command
    print("4. 🎯 USER REPLIES 'pause':")
    response = await handle_user_reply(user_phone, "pause")
    print(f"Response: {response}")
    print()
    
    # Test 5: Show stack after pause
    print("5. 📋 STACK AFTER PAUSE:")
    sms_message = await generate_reminder_sms(user_phone)
    print(sms_message)
    print()
    
    # Test 6: User resumes
    print("6. 🔄 USER REPLIES 'resume':")
    response = await handle_user_reply(user_phone, "resume")
    print(f"Response: {response}")
    print()
    
    # Test 7: Simulate free-form text
    print("7. 🤖 USER SENDS FREE-FORM TEXT:")
    response = await handle_user_reply(user_phone, "Add Vitamin C 9 AM daily")
    print(f"Response: {response}")

# Run the tests
if __name__ == "__main__":
    asyncio.run(run_test_scenarios())