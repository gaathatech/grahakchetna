import asyncio
import edge_tts
import re
import time

VOICE_MAP = {
    "english": "en-US-AriaNeural",            # Professional female news anchor voice (confirmed female)
    "hindi": "hi-IN-SwaraNeural",            # Female voice (professional news tone)
    "gujarati": "gu-IN-DhwaniNeural",        # Female voice (professional news tone)
}

OUTPUT_PATH = "output/voice.mp3"


def clean_text(text):
    # Remove unwanted special characters but keep spaces and basic punctuation
    text = re.sub(r"[^\w\s.,!?-]", "", text)
    return text.strip()[:3000]


async def _generate(text, voice):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+5%",         # Faster speech for professional news reading tone
        pitch="+0Hz"
    )
    await communicate.save(OUTPUT_PATH)


def generate_voice(text, language="english"):

    voice = VOICE_MAP.get(language, "en-US-AriaNeural")

    cleaned = clean_text(text)
    
    # Use text directly without extra wrapper narration
    script_for_tts = cleaned

    for attempt in range(3):  # retry system
        try:
            asyncio.run(_generate(script_for_tts, voice))
            return OUTPUT_PATH
        except Exception as e:
            print(f"Attempt {attempt + 1} failed:", e)
            time.sleep(1)

    return None
