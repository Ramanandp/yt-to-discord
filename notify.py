# Python 3.10+
# requirements: feedparser, requests
import os, json, time
import requests
import feedparser

CHANNEL_ID = os.getenv("YT_CHANNEL_ID")  # e.g., UCxxxxxxxxxxxxxxxx
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
STATE_FILE = "last_video.json"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

# Optional filters
PING_EVERYONE = False              # set True to @everyone
SKIP_SHORTS_BY_TITLE = True        # skip videos with "#shorts" in the title
# You can also ping a role: set ROLE_ID and PING_ROLE = True
PING_ROLE = False
ROLE_ID = "000000000000000000"     # replace with your role ID if using role ping

def load_last_id():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("last_id")
    except Exception:
        return None

def save_last_id(video_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_id": video_id}, f)

def should_skip(title: str) -> bool:
    # convert title to lowercase once
    lower = title.lower()

    # keywords/hashtags to skip
    skip_keywords = ["#shorts", "#memes", "#gamedev", "#gamedevelopment"]

    return any(k in lower for k in skip_keywords)

def post_to_discord(title, url, thumbnail):
    # Build content & allowed mentions safely
    mentions = []
    content_bits = []

    if PING_EVERYONE:
        content_bits.append("@everyone")
        mentions = ["everyone"]
    if PING_ROLE and ROLE_ID.isdigit():
        content_bits.append(f"<@&{ROLE_ID}>")

    content_bits.append(f"**New video:** {title}\n{url}")
    content = " ".join(content_bits)

    payload = {
        "content": content,
        "embeds": [{
            "title": title,
            "url": url,
            "image": {"url": thumbnail}
        }],
        "allowed_mentions": {
            "parse": mentions,
            "roles": [ROLE_ID] if (PING_ROLE and ROLE_ID.isdigit()) else []
        }
    }
    r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    r.raise_for_status()

def main():
    if not CHANNEL_ID or not WEBHOOK_URL:
        raise SystemExit("Missing YT_CHANNEL_ID or DISCORD_WEBHOOK_URL env vars.")

    feed = feedparser.parse(FEED_URL)
    entries = feed.entries or []
    if not entries:
        return

    last_id = load_last_id()

    # Collect new items since last_id, oldest→newest order
    new_items = []
    for e in entries:
        vid = getattr(e, "yt_videoid", None)
        if not vid:
            continue
        if vid == last_id:
            break
        new_items.append(e)

    if last_id is None and new_items:
        # First run: only announce the latest to avoid spamming old videos
        new_items = [entries[0]]

    for e in reversed(new_items):
        vid = e.yt_videoid
        title = e.title
        if should_skip(title):
            continue
        url = e.link  # standard watch URL
        thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        post_to_discord(title, url, thumb)
        # gentle pause (avoid rate limits)
        time.sleep(1)

    # Save last seen (latest entry id)
    latest = entries[0].yt_videoid
    save_last_id(latest)

if __name__ == "__main__":
    main()
