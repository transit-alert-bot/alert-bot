import sqlite3
import hashlib
import feedparser
from atproto import Client, models, client_utils
import ssl
from dotenv import load_dotenv
import os
import grapheme
from bs4 import BeautifulSoup

ssl._create_default_https_context = ssl._create_unverified_context

# === Load .env file ===
load_dotenv()
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_APP_PASSWORD = os.getenv("BSKY_APP_PASSWORD")

# === Check credentials ===
if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
    raise RuntimeError("Missing BSKY_HANDLE or BSKY_APP_PASSWORD in .env file.")

# === Configuration ===
FEED_URL = "https://www.octranspo.com/en/feeds/updates-en/"
DB_PATH = "rss_posts.db"

# === Initialize Bluesky Client ===
client = Client()
client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)

# === Database Setup ===
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS posts (
    guid TEXT PRIMARY KEY,
    pub_date TEXT,
    hash TEXT,
    post_uri TEXT,
    post_cid TEXT
)
""")
conn.commit()

def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ').strip()

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def fetch_feed():
    return feedparser.parse(FEED_URL)

def get_stored_post(guid: str):
    cur.execute("SELECT pub_date, hash, post_uri, post_cid FROM posts WHERE guid = ?", (guid,))
    return cur.fetchone()

def store_post(guid: str, pub_date: str, content_hash: str, post_uri: str, post_cid: str):
    cur.execute(
        "REPLACE INTO posts (guid, pub_date, hash, post_uri, post_cid) VALUES (?, ?, ?, ?, ?)",
        (guid, pub_date, content_hash, post_uri, post_cid)
    )
    conn.commit()

def truncate_post(text, max_graphemes=300):
    if grapheme.length(text) <= max_graphemes:
        return text

    # Reserve space for ellipsis
    allowed = max_graphemes - 3
    trimmed = grapheme.slice(text, 0, allowed)
    return trimmed + "..."



def process_feed():
    feed = fetch_feed()
    if feed.bozo:
        print("Error parsing feed:", feed.bozo_exception)
        return
    print(feed)
    # Sort entries by published date (oldest first)
    sorted_entries = sorted(feed.entries, key=lambda x: x.published)
    for entry in sorted_entries:
        guid = entry.guid
        title = clean_html(entry.title)
        description = clean_html(entry.description).strip()
        link = entry.link
        pub_date = entry.published

        # Combine all parts to form a unique content hash
        # Truncate content to 300 chars
        tb = client_utils.TextBuilder()
        tb.text("⚠️ " + title + "\n")
        tb.link("🔗 More details", link)
        tb.text("\n\n")
        tb.text(description)
        content = truncate_post(
            tb.build_text(),
        )
        content_hash = compute_hash(content)

        stored = get_stored_post(guid)

        if stored is None:
            post = client.send_post(
                text=content,
                facets=tb.build_facets(),
            )
            
            store_post(guid, pub_date, content_hash, post.uri, post.cid)
            print(f"✅ Posted new: {title}")
        else:
            _, stored_hash, stored_uri, stored_cid = stored
            if stored_hash != content_hash:
                post = client.send_post(
                    content,
                    reply_to=models.AppBskyFeedPost.ReplyRef(
                        root=models.ComAtprotoRepoStrongRef.Main(uri=stored_uri, cid=stored_cid),
                        parent=models.ComAtprotoRepoStrongRef.Main(uri=stored_uri, cid=stored_cid),
                    ),
                    facets=tb.build_facets(),
                )
                store_post(guid, pub_date, content_hash, post.uri, post.cid)
                print(f"♻️ Replied with update: {title}")
            else:
                print(f"➖ No change: {title}")

# === Run ===
if __name__ == "__main__":
    process_feed()
