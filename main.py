import sqlite3
import hashlib
import feedparser
from atproto import Client, models
import ssl
from dotenv import load_dotenv
import os

import grapheme

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
    for entry in feed.entries:
        guid = entry.guid
        title = entry.title
        description = entry.description.strip()
        link = entry.link
        pub_date = entry.published

        # Combine all parts to form a unique content hash
        # Truncate content to 300 chars
        content = truncate_post(
            title + "\n" + link + "\n" + description.replace("<p>", "").replace("</p>", "")
        )
        content_hash = compute_hash(content)

        stored = get_stored_post(guid)

                # Find where the link is in the text
        start = content.find(link)
        if start == -1:
            # Link not found in content, skip adding facet
            facet = None
        else:
            end = start + len(link)
            # Create facet for hyperlink
            facet = models.AppBskyRichtextFacet.Main(
                features=[
                    models.AppBskyRichtextFacet.Link(uri=content[start:end])
                ],
                index=models.AppBskyRichtextFacet.ByteSlice(byte_start=start, byte_end=end)
            )

        if stored is None:
            post = client.send_post(
                text=content,
                facets=[facet] if facet else None
            )
            
            store_post(guid, pub_date, content_hash, post.uri, post.cid)
            print(f"✅ Posted new: {title}")
        else:
            _, stored_hash, stored_uri, stored_cid = stored
            if stored_hash != content_hash:
                post = client.send_post(
                    content,
                    facets=[facet],
                    reply_to=models.AppBskyFeedPost.ReplyRef(
                        root=models.ComAtprotoRepoStrongRef.Main(uri=stored_uri, cid=stored_cid),
                        parent=models.ComAtprotoRepoStrongRef.Main(uri=stored_uri, cid=stored_cid),
                    ),
                )
                store_post(guid, pub_date, content_hash, post.uri)
                print(f"♻️ Replied with update: {title}")
            else:
                print(f"➖ No change: {title}")

# === Run ===
if __name__ == "__main__":
    process_feed()
