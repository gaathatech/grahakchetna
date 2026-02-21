"""
Trend Fetcher Module

This module provides functionality to fetch trending topics from:
1. Google Trends (India - geo="IN")
2. NewsAPI (Indian headlines)

Combines and deduplicates results to provide clean trending topics.

Author: Production System
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from pytrends.request import TrendReq


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
NEWSAPI_BASE_URL = "https://newsapi.org/v2/top-headlines"
DEFAULT_TIMEOUT = 10
PYTRENDS_TIMEOUT = 15
MIN_TOPIC_LENGTH = 3
MAX_TOPIC_LENGTH = 100
MAX_TOPICS = 8
MIN_TOPICS = 5


class TrendFetcherError(Exception):
    """Custom exception for trend fetching errors."""
    pass


class TrendValidator:
    """Validator class for trend fetcher parameters and data."""

    @staticmethod
    def validate_api_key(api_key: str) -> None:
        """
        Validate NewsAPI key format.

        Args:
            api_key: NewsAPI API key

        Raises:
            TrendFetcherError: If API key is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise TrendFetcherError("api_key must be a non-empty string")

        if len(api_key) < 10:
            raise TrendFetcherError("api_key format appears invalid (too short)")

        logger.info("API key validation successful")

    @staticmethod
    def clean_topic(topic: str) -> Optional[str]:
        """
        Clean and normalize a topic string.

        Args:
            topic: Raw topic string

        Returns:
            Cleaned topic or None if invalid
        """
        if not topic or not isinstance(topic, str):
            return None

        # Remove extra whitespace
        cleaned = " ".join(topic.split())

        # Remove special characters but keep spaces and alphanumeric
        cleaned = re.sub(r"[^\w\s]", "", cleaned).strip()

        # Check length
        if len(cleaned) < MIN_TOPIC_LENGTH or len(cleaned) > MAX_TOPIC_LENGTH:
            return None

        # Remove common non-trending words if they appear alone
        if cleaned.lower() in ["news", "today", "india", "breaking", "latest"]:
            return None

        return cleaned

    @staticmethod
    def validate_trend_list(trends: List[str]) -> List[str]:
        """
        Validate and clean a list of trends.

        Args:
            trends: List of trend strings

        Returns:
            Cleaned list of valid trends
        """
        if not isinstance(trends, list):
            return []

        cleaned_trends = []
        for trend in trends:
            cleaned = TrendValidator.clean_topic(trend)
            if cleaned:
                cleaned_trends.append(cleaned)

        return cleaned_trends


class GoogleTrendsFetcher:
    """Handler for Google Trends fetching."""

    def __init__(self, timeout: int = PYTRENDS_TIMEOUT):
        """
        Initialize Google Trends fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.geo = "IN"  # India

    def fetch(self) -> List[str]:
        """
        Fetch top 5 trending search topics in India.

        Returns:
            List of top 5 trending topics

        Raises:
            TrendFetcherError: If fetch fails
        """
        logger.info("Fetching Google Trends (India)...")

        try:
            # Initialize pytrends with timeout
            pytrends = TrendReq(
                hl="en-US",
                tz=330,  # IST (UTC+5:30)
                timeout=(self.timeout, self.timeout),
                retries=2,
                backoff_factor=0.1
            )

            # Fetch trending searches for India
            trending_df = pytrends.trending_searches(pn="india")

            # Extract top 5 trends (first column contains the trend names)
            trends = trending_df[0].tolist()[:5]

            # Clean and validate
            cleaned_trends = TrendValidator.validate_trend_list(trends)

            logger.info(f"✓ Google Trends fetched successfully: {len(cleaned_trends)} topics")
            logger.debug(f"Google Trends topics: {cleaned_trends}")

            return cleaned_trends

        except requests.exceptions.Timeout:
            raise TrendFetcherError("Google Trends request timeout")
        except requests.exceptions.RequestException as e:
            error_msg = f"Google Trends fetch failed: {str(e)}"
            logger.error(error_msg)
            raise TrendFetcherError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching Google Trends: {str(e)}"
            logger.error(error_msg)
            raise TrendFetcherError(error_msg)


class NewsAPIFetcher:
    """Handler for NewsAPI headline fetching."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize NewsAPI fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.base_url = NEWSAPI_BASE_URL

    def fetch(self, api_key: str) -> List[str]:
        """
        Fetch top 5 Indian headlines from NewsAPI.

        Args:
            api_key: NewsAPI API key

        Returns:
            List of top 5 headline keywords/topics

        Raises:
            TrendFetcherError: If fetch fails
        """
        logger.info("Fetching NewsAPI headlines (India)...")

        # Validate API key
        TrendValidator.validate_api_key(api_key)

        try:
            params = {
                "country": "in",
                "pageSize": 10,
                "apiKey": api_key
            }

            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get("status") != "ok":
                error_msg = f"NewsAPI error: {data.get('message', 'Unknown error')}"
                logger.error(error_msg)
                raise TrendFetcherError(error_msg)

            # Extract headlines
            articles = data.get("articles", [])
            if not articles:
                logger.warning("No articles found from NewsAPI")
                return []

            # Extract keywords from headlines (top 5 articles)
            headline_topics = []
            for article in articles[:5]:
                title = article.get("title", "")
                if title:
                    # Extract main keyword from title (usually first 3-5 words)
                    words = title.split()[:4]  # First 4 words
                    topic = " ".join(words).rstrip(".")
                    headline_topics.append(topic)

            # Clean and validate
            cleaned_topics = TrendValidator.validate_trend_list(headline_topics)

            logger.info(f"✓ NewsAPI headlines fetched successfully: {len(cleaned_topics)} topics")
            logger.debug(f"NewsAPI headline topics: {cleaned_topics}")

            return cleaned_topics

        except requests.exceptions.Timeout:
            raise TrendFetcherError("NewsAPI request timeout")
        except requests.exceptions.RequestException as e:
            error_msg = f"NewsAPI fetch failed: {str(e)}"
            logger.error(error_msg)
            raise TrendFetcherError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching NewsAPI: {str(e)}"
            logger.error(error_msg)
            raise TrendFetcherError(error_msg)


class TrendCombiner:
    """Handler for combining and deduplicating trends."""

    @staticmethod
    def combine_and_deduplicate(
        google_trends: List[str],
        news_trends: List[str]
    ) -> List[str]:
        """
        Combine trend lists and remove duplicates.

        Args:
            google_trends: List of Google Trends topics
            news_trends: List of NewsAPI headline topics

        Returns:
            Combined list of 5-8 unique, clean topics
        """
        logger.info("Combining and deduplicating trends...")

        # Create a set to track seen trends (case-insensitive)
        seen = set()
        combined_trends = []

        # Add Google Trends first (usually more relevant)
        for trend in google_trends:
            trend_lower = trend.lower()
            if trend_lower not in seen:
                seen.add(trend_lower)
                combined_trends.append(trend)

        # Add NewsAPI headlines if not already included
        for trend in news_trends:
            trend_lower = trend.lower()
            if trend_lower not in seen:
                seen.add(trend_lower)
                combined_trends.append(trend)

        # Return 5-8 topics
        final_trends = combined_trends[:MAX_TOPICS]

        # Ensure minimum topics
        if len(final_trends) < MIN_TOPICS:
            logger.warning(f"Only {len(final_trends)} unique trends found (minimum {MIN_TOPICS})")

        logger.info(
            f"✓ Combined trends: {len(final_trends)} unique topics "
            f"(Google: {len(google_trends)}, News: {len(news_trends)})"
        )
        logger.debug(f"Final combined trends: {final_trends}")

        return final_trends


def fetch_google_trends() -> List[str]:
    """
    Fetch top 5 trending search topics in India from Google Trends.

    Uses pytrends library to fetch real-time trending searches in India.

    Returns:
        List[str]: Top 5 trending topics in India

    Raises:
        TrendFetcherError: If fetch fails

    Example:
        >>> trends = fetch_google_trends()
        >>> print(trends)
        ['Topic 1', 'Topic 2', 'Topic 3', 'Topic 4', 'Topic 5']
    """
    fetcher = GoogleTrendsFetcher()
    return fetcher.fetch()


def fetch_newsapi_headlines(api_key: str) -> List[str]:
    """
    Fetch top 5 Indian headlines from NewsAPI.

    Uses NewsAPI endpoint to fetch latest news headlines for India and
    extracts top keywords/topics from them.

    Args:
        api_key (str): NewsAPI API key from https://newsapi.org

    Returns:
        List[str]: Top 5 headline topics/keywords

    Raises:
        TrendFetcherError: If fetch fails or API key is invalid

    Example:
        >>> headlines = fetch_newsapi_headlines("your_api_key")
        >>> print(headlines)
        ['Headline Topic 1', 'Headline Topic 2', ...]
    """
    fetcher = NewsAPIFetcher()
    return fetcher.fetch(api_key)


def get_combined_trends(news_api_key: str) -> Dict[str, List[str]]:
    """
    Fetch and combine trending topics from Google Trends and NewsAPI.

    This function fetches trending search topics from Google Trends (India)
    and headline keywords from NewsAPI (India), combines them, removes
    duplicates, and returns a clean list of 5-8 unique trending topics.

    Args:
        news_api_key (str): NewsAPI API key from https://newsapi.org

    Returns:
        Dict[str, List[str]]: Dictionary with key "trending_topics" containing
            a list of 5-8 clean, deduplicated trending topics. Example:
            {
                "trending_topics": [
                    "ISRO Mission",
                    "Stock Market Update",
                    "Cricket News",
                    "Weather Alert",
                    "Election Results",
                    "Tech Launch",
                    "Sports Update"
                ]
            }

    Raises:
        TrendFetcherError: If either Google Trends or NewsAPI fetch fails

    Example:
        >>> result = get_combined_trends("your_newsapi_key")
        >>> print(result["trending_topics"])
        ['Topic 1', 'Topic 2', 'Topic 3', ...]
    """
    try:
        logger.info("Starting combined trends fetch...")

        # Fetch Google Trends
        google_trends = fetch_google_trends()

        # Fetch NewsAPI headlines
        news_trends = fetch_newsapi_headlines(news_api_key)

        # Combine and deduplicate
        combined = TrendCombiner.combine_and_deduplicate(google_trends, news_trends)

        logger.info(f"✓ Combined trends retrieved successfully: {len(combined)} topics")

        return {
            "trending_topics": combined,
            "source_count": {
                "google_trends": len(google_trends),
                "newsapi_headlines": len(news_trends),
                "total_unique": len(combined)
            }
        }

    except TrendFetcherError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in get_combined_trends: {str(e)}"
        logger.error(error_msg)
        raise TrendFetcherError(error_msg) from e


if __name__ == "__main__":
    import sys
    import json
    from dotenv import load_dotenv
    import os

    # Load environment variables
    load_dotenv()

    try:
        # Get NewsAPI key from environment or command line
        news_api_key = os.getenv("NEWSAPI_KEY")

        if not news_api_key:
            print("Error: NEWSAPI_KEY environment variable not set")
            print("Set it in .env file or pass as argument:")
            print("  export NEWSAPI_KEY='your_key'")
            print("  python trend_fetcher.py")
            sys.exit(1)

        logger.info("=" * 80)
        logger.info("TREND FETCHER - TESTING")
        logger.info("=" * 80)

        # Fetch combined trends
        result = get_combined_trends(news_api_key)

        # Pretty print results
        print("\n" + "=" * 80)
        print("TRENDING TOPICS IN INDIA")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("=" * 80 + "\n")

        # Show formatted list
        print("📊 TRENDING TOPICS:")
        for i, topic in enumerate(result["trending_topics"], 1):
            print(f"  {i}. {topic}")

        print("\n" + "=" * 80)

    except TrendFetcherError as e:
        logger.error(f"Trend fetch failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
