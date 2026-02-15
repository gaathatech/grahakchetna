import feedparser

RSS_URL = "https://news.google.com/rss/search?q=Gujarat+news&hl=en-IN&gl=IN&ceid=IN:en"

def fetch_rss_news():
    feed = feedparser.parse(RSS_URL)
    news_list = []

    for i, entry in enumerate(feed.entries[:5]):
        news_list.append((i+1, entry.title))

    return news_list
