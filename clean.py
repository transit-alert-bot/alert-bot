from atproto import Client
from dotenv import load_dotenv
import os

# === Load .env file ===
load_dotenv()
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_APP_PASSWORD = os.getenv("BSKY_APP_PASSWORD")

# === Check credentials ===
if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
    raise RuntimeError("Missing BSKY_HANDLE or BSKY_APP_PASSWORD in .env file.")

# === Connect and Login ===
client = Client()
client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)

# === Fetch and Delete Posts ===
def delete_all_posts():
    print("🔍 Fetching your posts...")
    cursor = None

    while True:
        response = client.app.bsky.feed.get_author_feed({
            "actor": BSKY_HANDLE,
            "limit": 100,
            "cursor": cursor
        })

        posts = response.feed  # ✅ Access like an object

        if not posts:
            break

        for item in posts:
            post = item.post
            uri = post.uri
            if uri:
                print(f"🗑️ Deleting: {uri}")
                client.delete_post(uri)

        cursor = response.cursor
        if not cursor:
            break

    print("✅ Done deleting posts.")

if __name__ == "__main__":
    delete_all_posts()
