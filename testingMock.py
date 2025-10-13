import asyncio
from datetime import datetime
from loggingStack import log_medicine_event, EASTERN_TZ

async def run_test(userPhone, fake_now):
    stack = await log_medicine_event(userPhone, now=fake_now)
    print(f"\n=== Stack for {userPhone} at {fake_now.strftime('%H:%M')} ===")
    for med in stack:
        print(f"Stack {med['stack_position']}: {med['name']} ({med['status']}) at {med['time']}")

async def main():
    # Scenario 1: Morning overdue, now 10:15
    await run_test("user1", EASTERN_TZ.localize(datetime(2025, 10, 13, 10, 15)))

    # Scenario 2: Afternoon pile-up, now 12:45
    await run_test("user2", EASTERN_TZ.localize(datetime(2025, 10, 13, 12, 45)))

    # Scenario 3: All future, now 11:00
    await run_test("user3", EASTERN_TZ.localize(datetime(2025, 10, 13, 11, 0)))

    # Scenario 4: All missed, now 11:00
    await run_test("user4", EASTERN_TZ.localize(datetime(2025, 10, 13, 11, 0)))

    # Scenario 5: Mixed, now 12:30
    await run_test("user5", EASTERN_TZ.localize(datetime(2025, 10, 13, 12, 30)))

asyncio.run(main())

