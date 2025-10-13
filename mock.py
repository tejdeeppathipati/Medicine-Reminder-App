
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