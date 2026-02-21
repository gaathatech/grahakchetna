import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

def generate_script(headline, description, language):

    if language == "gujarati":
        lang_instruction = "Write the script fully in Gujarati language."
    elif language == "hindi":
        lang_instruction = "Write the script fully in Hindi language."
    else:
        lang_instruction = "Write the script fully in English language."

    prompt = f"""
    Create ONLY the spoken narration for a news video using ONLY the provided information.

    {lang_instruction}

    Headline: {headline}
    Description: {description}

    Your output must be EXACTLY: The headline, followed by the description. Nothing more. No extra sentences, no commentary, no interpretation.
    
    Do NOT include:
    - Stage directions
    - Timing brackets
    - Visual cues
    - Hashtags
    - Music cues
    - Extra commentary or sentences
    - Interpretation or analysis
    
    Output format:
    [Headline]. [Description].
    """

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print("Groq Error:", response.text)
        return None

    return response.json()["choices"][0]["message"]["content"]
