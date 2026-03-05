import os
import time
import logging
from typing import List, Dict, Any
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Default RSS feeds (can be overridden with RSS_FEEDS env var as comma-separated URLs)
DEFAULT_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://www.hindustantimes.com/rss/topnews/rssfeed.xml",
    "https://www.ndtv.com/rss/ndtvnews-top-stories",
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.bbci.co.uk/news/rss.xml"
]


def _get_feeds() -> List[str]:
    env = os.getenv("RSS_FEEDS")
    if env:
        return [u.strip() for u in env.split(',') if u.strip()]
    return DEFAULT_FEEDS


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ").strip()


def _entry_published_dt(entry) -> datetime:
    # feedparser provides published_parsed or updated_parsed as time.struct_time
    struct = None
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        struct = entry.published_parsed
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        struct = entry.updated_parsed

    if struct:
        try:
            return datetime.fromtimestamp(time.mktime(struct))
        except Exception:
            pass

    # Fallback: try published/updated strings
    for key in ('published', 'updated'):
        if key in entry:
            try:
                return datetime.fromisoformat(entry[key])
            except Exception:
                continue

    return datetime.utcnow()


def fetch_latest_articles(max_articles: int = 10) -> List[Dict[str, Any]]:
    """Fetch articles from configured RSS feeds, clean descriptions and return
    a list of articles sorted by published date (newest first).

    Each article dict contains: title, link, description, published (datetime).
    """
    feeds = _get_feeds()
    articles: List[Dict[str, Any]] = []

    for url in feeds:
        try:
            d = feedparser.parse(url)
            source_title = ''
            try:
                source_title = d.feed.get('title') if hasattr(d, 'feed') and d.feed else ''
            except Exception:
                source_title = ''
            for entry in d.entries:
                title = entry.get('title') or entry.get('headline') or 'No title'
                link = entry.get('link') or ''
                raw_desc = entry.get('description') or entry.get('summary') or ''
                description = _clean_html(raw_desc)
                published = _entry_published_dt(entry)

                articles.append({
                    'title': title,
                    'link': link,
                    'source': source_title or url,
                    'description': description,
                    'published': published
                })
        except Exception as e:
            logger.warning(f"Failed to parse feed {url}: {e}")

    # Sort by published descending and limit
    articles.sort(key=lambda x: x['published'], reverse=True)
    return articles[:max_articles]


# Category mapping persistence
_CATEGORY_MAP_FILE = os.path.join(os.getcwd(), 'rss_category_map.json')


def _load_category_map() -> Dict[str, str]:
    try:
        if os.path.exists(_CATEGORY_MAP_FILE):
            import json
            with open(_CATEGORY_MAP_FILE, 'r', encoding='utf-8') as fh:
                return json.load(fh)
    except Exception:
        pass
    return {}


def _save_category_map(mapping: Dict[str, str]) -> bool:
    try:
        import json
        with open(_CATEGORY_MAP_FILE, 'w', encoding='utf-8') as fh:
            json.dump(mapping, fh, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save category mapping: {e}")
        return False



