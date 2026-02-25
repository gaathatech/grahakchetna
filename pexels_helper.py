import os
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


def fetch_image_from_pexels(headline, dimension=800):
    """Fetch an image from Pexels for the given headline.

    Returns local path or None.
    """
    try:
        pexels_api_key = os.getenv("PEXELS_API_KEY")
        if not pexels_api_key:
            logger.warning("PEXELS_API_KEY not set")
            return None

        keywords = " ".join((headline or "").split()[:5])
        if not keywords:
            return None

        headers = {"Authorization": pexels_api_key, "User-Agent": "GrahakChetna/1.0"}
        params = {"query": keywords, "per_page": 1, "page": 1}
        resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Pexels API returned {resp.status_code}")
            return None

        data = resp.json()
        photos = data.get("photos") or []
        if not photos:
            return None

        photo = photos[0]
        # prefer 'original' if present, else large
        image_url = photo.get("src", {}).get("original") or photo.get("src", {}).get("large")
        if not image_url:
            return None

        # Download with requests and stream
        os.makedirs("uploads", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = f"pexels_{ts}_{photo.get('id')}.jpg"
        outpath = os.path.join("uploads", basename)

        with requests.get(image_url, headers={"User-Agent": "GrahakChetna/1.0"}, stream=True, timeout=15) as r:
            if r.status_code != 200:
                logger.warning(f"Failed to download Pexels image: {r.status_code}")
                return None
            with open(outpath, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)

        logger.info(f"Downloaded Pexels image to {outpath}")
        return outpath

    except Exception as e:
        logger.warning(f"Exception fetching Pexels image: {e}")
        return None
