# Medicine Reminder App

Lets users set up their medication schedule through a web form and get SMS/WhatsApp reminders. The Flask backend stores users in MongoDB, sends reminders with Twilio (or the WhatsApp sandbox for demos), and processes text commands like “1”, “pause”, or “add” to keep the schedule up to date. The React frontend is just a form that posts to the API.
