import sqlite3
import hashlib
import feedparser
from atproto import Client, models, client_utils
import ssl
import grapheme
from bs4 import BeautifulSoup
import yaml

ssl._create_default_https_context = ssl._create_unverified_context

# === Load config file ===
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

if not config.get('endpoints'):
    raise RuntimeError("Missing 'endpoints' configuration in config.yaml")

DB_PATH = "rss_posts.db"

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


def fetch_feed(url: str):
    return feedparser.parse(url)


def get_stored_post(guid: str):
    cur.execute(
        "SELECT pub_date, hash, post_uri, post_cid FROM posts WHERE guid = ?", (guid,))
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


def extract_first_image(html_content: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html_content, 'html.parser')
    img = soup.find('img')
    if not img:
        return None, None
    # Default to 'Alert image' if no alt
    return img.get('src'), img.get('alt', 'Alert image')


def process_feeds():
    for endpoint in config['endpoints']:
        print(f"\nProcessing feed: {endpoint['feed']}")

        # Create new client for each endpoint
        client = Client()
        try:
            client.login(endpoint['handle'], endpoint['password'])
        except Exception as e:
            print(f"Failed to login as {endpoint['handle']}: {e}")
            continue

        feed = fetch_feed(endpoint['feed'])
        if feed.bozo:
            print("Error parsing feed:", feed.bozo_exception)
            continue

        # Sort entries by published date (oldest first)
        sorted_entries = sorted(feed.entries, key=lambda x: x.published)
        for entry in sorted_entries:
            guid = entry.guid
            title = clean_html(entry.title)
            description = clean_html(entry.description).strip()
            link = entry.link
            pub_date = entry.published

            # Extract image if any
            image_url, image_alt = extract_first_image(entry.description)
            images = []
            if image_url:
                try:
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    content_type = img_response.headers.get(
                        "Content-Type", "image/jpeg")  # Default fallback

                    response = client.upload_blob(
                        file_data=img_response.content,
                        content_type=content_type,
                    )
                    images = [models.AppBskyEmbedImages.Image(
                        alt=image_alt, image=response.blob)]
                except Exception as e:
                    print(f"Failed to upload image: {e}")

            # Combine all parts to form a unique content hash
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
                    embed=models.AppBskyEmbedImages.Main(
                        images=images) if images else None
                )

                store_post(guid, pub_date, content_hash, post.uri, post.cid)
                print(f"✅ Posted new: {title}")
            else:
                _, stored_hash, stored_uri, stored_cid = stored
                if stored_hash != content_hash:
                    post = client.send_post(
                        text=content,
                        reply_to=models.AppBskyFeedPost.ReplyRef(
                            root=models.ComAtprotoRepoStrongRef.Main(
                                uri=stored_uri, cid=stored_cid),
                            parent=models.ComAtprotoRepoStrongRef.Main(
                                uri=stored_uri, cid=stored_cid),
                        ),
                        facets=tb.build_facets(),
                        embed=models.AppBskyEmbedImages.Main(
                            images=images) if images else None
                    )
                    store_post(guid, pub_date, content_hash,
                               post.uri, post.cid)
                    print(f"♻️ Replied with update: {title}")
                else:
                    print(f"➖ No change: {title}")


# === Run ===
if __name__ == "__main__":
    process_feeds()
