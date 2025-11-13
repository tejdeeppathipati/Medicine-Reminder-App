# Medicine Reminder App

Flask + React prototype that stores medication schedules in MongoDB, sends reminders over Twilio (SMS or WhatsApp), and lets users reply with simple commands to log doses.

## Prerequisites
- Python 3.10+
- Node 18+ (for the React form)
- MongoDB running locally (`mongodb://localhost:27017/`)
- Twilio account (trial is fine)

## Backend Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # edit values
export $(grep -v '^#' .env | xargs)  # or use direnv
python backend/app.py
```

The scheduler boots with the Flask app and checks for due medications every minute. API endpoints:
- `POST /api/user/setup` – create a user with meds/caregivers
- `GET /api/user/<user_id>` – fetch profile
- `PUT /api/user/<user_id>/medications`
- `PUT /api/user/<user_id>/caregivers`
- `POST /api/sms/handle` – Twilio/WhatsApp webhook for replies

## WhatsApp Sandbox (no A2P registration required)
1. Console → Messaging → Try it out → WhatsApp → send the displayed `join ...` code to `+1 415 523 8886`.
2. Set env vars:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxx
   TWILIO_FROM_NUMBER=whatsapp:+14155238886
   ```
3. Store user/caregiver phones as `whatsapp:+1XXXXXXXXXX` (the setup API now accepts that format).
4. Expose your backend (ngrok etc.) and paste the public URL into “When a message comes in” on the sandbox page so replies hit `/api/sms/handle`.
5. Run the app; when a med time hits, you’ll receive a WhatsApp reminder from the sandbox. Replies (`1`, `pause`, etc.) go through the webhook.

Switch back to SMS later by updating `TWILIO_FROM_NUMBER` and storing plain E.164 numbers (e.g., `+15551234567`).

## Frontend
```bash
cd frontend
npm install
npm run dev
```
The form submits to the backend running on `http://127.0.0.1:5000`.
