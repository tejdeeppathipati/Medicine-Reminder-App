from typing import Dict


def aiParseMedicine(text: str) -> Dict[str, str]:
    """
    Simple placeholder parser for free-form medicine edits/adds.
    This is a naive implementation until the real AI integration is ready.
    """
    parts = text.split()
    if len(parts) < 2:
        raise ValueError("Unable to parse medicine input.")

    medicine_name = parts[0]
    time = parts[1]
    day = parts[2] if len(parts) > 2 else ""

    return {
        "medicine_name": medicine_name,
        "time": time,
        "day": day,
    }
