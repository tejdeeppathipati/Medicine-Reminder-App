import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
#this is tackling the logic of user simply typing edit
# sarah will type edit : vitamin a 8 am thursday or i will take vitamin a on thursday at 8 00 and ai will 
# parse the data into a strucuted json output. 

load_dotenv()
#basic layout: ai response just like normal , then becomes json, check if broken format, make data look the same which will help our other logic and return the data which will go to DB 
ai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=30)

def aiParseMedicine(message_text):
    """
    Parses an incoming SMS message like:
    "vitamin a 8:10 pm monday"
    and returns structured JSON data for MongoDB.
    """
#this is giving ai the prompt to follow when structuring the data. 
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
#we will be using 40 mini because its better and cheaper and the precision given is 0.2 which will help control any inconsistency and error.  
    try:
    
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise data extraction AI. Return valid JSON only."}, # rules given to the model. 
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
            #if ai has failed to given the output in json format then the pattern matching will help us require the format in json structure. 
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
