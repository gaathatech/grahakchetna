"""
Long-form YouTube script generation service.

Generates 1000-1500 word scripts optimized for YouTube retention with:
- Professional news tone
- Structured sections for engagement
- Clear narrative flow
- No emojis or stage directions
"""

import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GROQ_API_KEY")

def generate_long_script(headline, description, language="english"):
    """
    Generate a long-form YouTube script (1000-1500 words).
    
    Args:
        headline: Main news headline
        description: Short summary of the story
        language: Script language (english, gujarati, hindi)
    
    Returns:
        dict: {
            "success": bool,
            "script": str,
            "word_count": int,
            "sections": dict with breakdown
        }
    """
    
    if language.lower() == "gujarati":
        lang_instruction = "Write the entire script in Gujarati language."
    elif language.lower() == "hindi":
        lang_instruction = "Write the entire script in Hindi language."
    else:
        lang_instruction = "Write the entire script in English language."

    prompt = f"""
You are a professional news scriptwriter for YouTube long-form documentaries. 
Create a compelling 1000-1500 word script for a YouTube video about this news story.

{lang_instruction}

HEADLINE: {headline}
DESCRIPTION: {description}

SCRIPT STRUCTURE (include all sections):

1. **HOOK (10-15 seconds)** - Grab attention immediately with a surprising fact, question, or statement
2. **BACKGROUND CONTEXT** - Explain the historical/contextual background necessary to understand the story
3. **WHAT HAPPENED** - Detailed account of the recent events and developments
4. **WHY IT MATTERS** - Analysis of the significance and impact of this news
5. **FUTURE IMPLICATIONS** - What could happen next and why viewers should care
6. **STRONG CLOSING** - Memorable conclusion that reinforces key points and calls for thought/action

REQUIREMENTS:
- Neutral, professional journalistic tone
- Conversational yet authoritative
- NO EMOJIS
- NO stage directions or brackets
- NO hashtags or social media tags
- NO words like [PAUSE], [CUT TO], [MUSIC STARTS], etc.
- Clear transitions between sections
- Use data/statistics to support claims where relevant
- Vary sentence length for engagement
- Target 1000-1500 words
- Optimized for YouTube viewing (20-25 minute read at natural pace)
- Include a natural pause point around midway (for chapter markers)

TONE:
- Professional and credible
- Engaging but not sensational
- Respectful of all parties mentioned
- Evidence-based

Output ONLY the script text. Start directly with the Hook section without any preamble.
Do not include section headers in the output - write it as a flowing narrative.
"""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3000,
            "temperature": 0.7
        }

        logger.info("Generating long-form script via Groq API...")
        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"Groq API error: {response.status_code}",
                "script": None,
                "word_count": 0
            }

        script_text = response.json()["choices"][0]["message"]["content"].strip()
        
        # Count words
        word_count = len(script_text.split())
        
        logger.info(f"✓ Long-form script generated successfully ({word_count} words)")
        
        return {
            "success": True,
            "script": script_text,
            "word_count": word_count,
            "language": language,
            "sections": {
                "hook": "10-15 seconds",
                "background": "Variable",
                "what_happened": "Variable",
                "why_it_matters": "Variable",
                "future_implications": "Variable",
                "closing": "Variable"
            }
        }

    except requests.exceptions.Timeout:
        logger.error("Script generation timeout (>60s)")
        return {
            "success": False,
            "error": "Script generation timeout",
            "script": None,
            "word_count": 0
        }
    except Exception as e:
        logger.error(f"Script generation error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "script": None,
            "word_count": 0
        }


if __name__ == "__main__":
    # Test the long script generator
    logging.basicConfig(level=logging.INFO)
    
    test_headline = "Why Hungary Blocked EU Sanctions"
    test_description = "Hungary blocks EU sanctions package against Russia before war anniversary."
    
    result = generate_long_script(test_headline, test_description)
    print(f"\nStatus: {result['success']}")
    if result['success']:
        print(f"Word Count: {result['word_count']}")
        print(f"\n--- SCRIPT PREVIEW (first 500 chars) ---\n{result['script'][:500]}...")
    else:
        print(f"Error: {result['error']}")
