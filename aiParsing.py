
import os
import json
import re
from openai import OpenAI

ai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=30)

async def ai_parse_medicine_message(message_text):
    """
    Parses an incoming SMS message like:
    "vitamin a 8:10 pm monday"
    and returns structured JSON data for MongoDB.
    """

    prompt = (
        "You are an intelligent assistant that extracts medicine reminder details "
        "from user SMS messages. Each message contains a medicine name, a time, "
        "and optionally a day of the week.\n\n"
        "Return ONLY a valid JSON object in the format:\n"
        "{\n"
        '  "medicine_name": "<string>",\n'
        '  "time": "<string>",\n'
        '  "day": "<string or null if not provided>"\n'
        "}\n\n"
        "Examples:\n"
        '"Vitamin D 10 pm" → {"medicine_name": "vitamin d", "time": "10 pm", "day": null}\n'
        '"Tylenol 8 am Monday" → {"medicine_name": "tylenol", "time": "8 am", "day": "monday"}\n\n'
        f"Message:\n{message_text}"
    )

    try:
        response = await ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise data extraction AI. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )

        textResponse = response.choices[0].message.content
        print("Raw AI response:", textResponse)

        parsedResponse = None
        try:
            parsedResponse = json.loads(textResponse)
        except json.JSONDecodeError:
            print("Initial JSON parse failed. Attempting recovery...")
            
            match = re.search(r'\{[\s\S]*\}', textResponse)
            if match:
                try:
                    parsedResponse = json.loads(match.group())
                    print("Recovered JSON from regex match")
                except json.JSONDecodeError:
                    print("Recovery attempt failed.")
                    return None
            else:
                print("No JSON structure found.")
                return None

        if not isinstance(parsedResponse, dict):
            print("AI response is not a JSON object.")
            return None

        required_keys = ["medicine_name", "time", "day"]
        for key in required_keys:
            if key not in parsedResponse:
                print("Missing key:", key)
                return None

        if parsedResponse["medicine_name"] and isinstance(parsedResponse["medicine_name"], str):
            parsedResponse["medicine_name"] = parsedResponse["medicine_name"].strip().lower()
        
        if parsedResponse["time"] and isinstance(parsedResponse["time"], str):
            parsedResponse["time"] = parsedResponse["time"].strip().lower()
        
        if parsedResponse["day"] is not None and isinstance(parsedResponse["day"], str):
            parsedResponse["day"] = parsedResponse["day"].strip().lower()

        print("Final parsed data:", parsedResponse)
        return parsedResponse

    except Exception as err:
        print("Error in ai_parse_medicine_message:", str(err))
        return None