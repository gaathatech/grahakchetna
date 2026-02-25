import os
import time
import logging
from typing import List, Dict, Any
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup

from wordpress_uploader import create_post

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


def fetch_and_post_to_wordpress(max_articles: int = 5, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Fetch latest articles and post them to WordPress using `create_post`.

    Returns a list of results for each attempted post.
    """
    results: List[Dict[str, Any]] = []

    wp_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USERNAME')
    wp_app_pass = os.getenv('WORDPRESS_APP_PASSWORD')
    verify_ssl = os.getenv('WORDPRESS_VERIFY_SSL', 'true').lower() not in ['false', '0', 'no']
    # Special handling for grahakchetna.in due to SSL issues
    if wp_url and 'grahakchetna.in' in wp_url:
        verify_ssl = False
    post_status = os.getenv('WP_POST_STATUS', 'publish')
    hashtags_env = os.getenv('WP_HASHTAGS')
    if hashtags_env:
        hashtags = [h.strip() for h in hashtags_env.split(',') if h.strip()]
    else:
        hashtags = ['#Breaking', '#Viral', '#Trending']

    if not (wp_url and wp_user and wp_app_pass):
        raise RuntimeError('WordPress credentials are not configured in environment')

    articles = fetch_latest_articles(max_articles=max_articles)

    for art in articles:
        title = art['title']
        content = f"<p>{art['description']}</p>" if art['description'] else ''
        # Optionally append source link
        if art.get('link'):
            content += f"<p>Source: <a href=\"{art['link']}\">{art['link']}</a></p>"
        # Append viral hashtags
        if hashtags:
            content += "<p>" + " ".join(hashtags) + "</p>"

        # Derive tags from hashtags (strip leading #) and source name
        tags = [h.lstrip('#') for h in hashtags]
        if art.get('source'):
            # Use a short source tag name (e.g., 'BBC', 'CNN' or full feed title)
            src_tag = art.get('source')
            if isinstance(src_tag, str) and src_tag.strip():
                tags.append(src_tag.strip())

        try:
            if dry_run:
                # Do not perform network calls, just simulate
                results.append({'article': art, 'status': 'dry-run', 'would_post': True, 'title': title, 'categories': [], 'tags': tags})
                logger.info(f"Dry-run: would post article: {title}")
            else:
                post_resp = create_post(
                    title=title,
                    content=content,
                    wp_url=wp_url,
                    username=wp_user,
                    app_password=wp_app_pass,
                    description=art.get('description'),
                    verify_ssl=verify_ssl,
                    status=post_status,
                    categories=None,
                    tags=tags
                )
                results.append({'article': art, 'status': 'posted', 'response': post_resp})
                logger.info(f"Posted article to WordPress: {title}")
        except Exception as e:
            logger.error(f"Failed to post article '{title}': {e}")
            results.append({'article': art, 'status': 'failed', 'error': str(e)})

    return results


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


def post_selected_articles(links: List[str], dry_run: bool = False, max_search: int = 100) -> List[Dict[str, Any]]:
    """Post only articles whose link is in `links`.

    This fetches up to `max_search` latest articles and matches by link.
    Returns post results similar to `fetch_and_post_to_wordpress`.
    """
    # Normalize links to compare
    want = set([str(l).strip() for l in (links or []) if l])
    if not want:
        return []

    # Fetch a larger pool and filter
    pool = fetch_latest_articles(max_articles=max_search)
    selected = [a for a in pool if (a.get('link') or '').strip() in want]

    results = []
    if not selected:
        return results

    # Reuse environment settings
    wp_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USERNAME')
    wp_app_pass = os.getenv('WORDPRESS_APP_PASSWORD')
    verify_ssl = os.getenv('WORDPRESS_VERIFY_SSL', 'true').lower() not in ['false', '0', 'no']
    # Special handling for grahakchetna.in due to SSL issues
    if wp_url and 'grahakchetna.in' in wp_url:
        verify_ssl = False
    post_status = os.getenv('WP_POST_STATUS', 'publish')
    hashtags_env = os.getenv('WP_HASHTAGS')
    if hashtags_env:
        hashtags = [h.strip() for h in hashtags_env.split(',') if h.strip()]
    else:
        hashtags = ['#Breaking', '#Viral', '#Trending']

    if not (wp_url and wp_user and wp_app_pass) and not dry_run:
        raise RuntimeError('WordPress credentials are not configured in environment')

    for art in selected:
        title = art['title']
        content = f"<p>{art['description']}</p>" if art['description'] else ''
        if art.get('link'):
            content += f"<p>Source: <a href=\"{art['link']}\">{art['link']}</a></p>"
        if hashtags:
            content += "<p>" + " ".join(hashtags) + "</p>"

        tags = [h.lstrip('#') for h in hashtags]
        if art.get('source'):
            tags.append(art.get('source').strip())

        try:
            if dry_run:
                results.append({'article': art, 'status': 'dry-run', 'would_post': True, 'title': title, 'categories': [], 'tags': tags})
            else:
                post_resp = create_post(
                    title=title,
                    content=content,
                    wp_url=wp_url,
                    username=wp_user,
                    app_password=wp_app_pass,
                    description=art.get('description'),
                    verify_ssl=verify_ssl,
                    status=post_status,
                    categories=None,
                    tags=tags
                )
                results.append({'article': art, 'status': 'posted', 'response': post_resp})
        except Exception as e:
            results.append({'article': art, 'status': 'failed', 'error': str(e)})

    return results
