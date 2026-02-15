from script_service import generate_script

def generate_seo(headline, script):
    prompt = f"""
    Create YouTube Shorts SEO content in Gujarati.

    Headline: {headline}
    Script: {script}

    Provide:
    - Viral Title
    - SEO Description
    - 10 Hashtags
    - Pinned Comment
    """

    return generate_script(headline, prompt)
