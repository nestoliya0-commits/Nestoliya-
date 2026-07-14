"""
CA Tracker Bot
--------------
Monitors a Twitter/X account for pump.fun / Solana contract addresses
and sends a Telegram alert when a verified token is found.

Tracks: @stoolpresidente
Alerts sent to your Telegram chat.
"""

import re
import os
import time
import threading
import requests
import snscrape.modules.twitter as sntwitter
from flask import Flask

# ============ CONFIG ============
TWITTER_USERNAME = "stoolpresidente"
BOT_TOKEN = "8646199363:AAE1K-oiNdzaS1JYoqIhCcFeH-CZZwrZx28"
CHAT_ID = "7067220710"
CHECK_INTERVAL = 30  # seconds between checks
SEEN_TWEETS_FILE = "seen_tweets.txt"

# ============ KEEP-ALIVE WEB SERVER (for Render free tier + UptimeRobot) ============
app = Flask(__name__)


@app.route("/")
def home():
    return "CA Tracker is alive."


@app.route("/ping")
def ping():
    return "pong"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# Solana address pattern (Base58, 32-44 chars)
SOLANA_ADDRESS_RE = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
PUMPFUN_LINK_RE = re.compile(r'pump\.fun/(?:coin/)?([1-9A-HJ-NP-Za-km-z]{32,44})')
SOLANA_PREFIX_RE = re.compile(r'solana:([1-9A-HJ-NP-Za-km-z]{32,44})', re.IGNORECASE)


def load_seen():
    try:
        with open(SEEN_TWEETS_FILE, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


def save_seen(tweet_id):
    with open(SEEN_TWEETS_FILE, "a") as f:
        f.write(f"{tweet_id}\n")


def get_latest_tweets(username, limit=5):
    """Fetch latest tweets using snscrape (no API key needed)."""
    tweets = []
    try:
        scraper = sntwitter.TwitterUserScraper(username)
        for i, tweet in enumerate(scraper.get_items()):
            if i >= limit:
                break
            tweets.append(tweet)
    except Exception as e:
        print(f"[ERROR] Failed to fetch tweets: {e}")
    return tweets


def extract_ca(text):
    """Extract a candidate Solana contract address from tweet text."""
    # 1. Explicit "solana:ADDRESS" notation (common among KOLs like Ansem)
    match = SOLANA_PREFIX_RE.search(text)
    if match:
        return match.group(1)

    # 2. pump.fun links
    match = PUMPFUN_LINK_RE.search(text)
    if match:
        return match.group(1)

    # 3. Fallback: raw address, prefer ones ending in 'pump' (pump.fun tokens)
    candidates = SOLANA_ADDRESS_RE.findall(text)
    for c in candidates:
        if c.lower().endswith("pump"):
            return c
    if candidates:
        return candidates[0]
    return None


def verify_token(ca):
    """Check DexScreener to confirm the token is real and has liquidity."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        pairs = data.get("pairs")
        if not pairs:
            return None  # not found / no liquidity yet
        pair = pairs[0]
        return {
            "name": pair.get("baseToken", {}).get("name", "Unknown"),
            "symbol": pair.get("baseToken", {}).get("symbol", "?"),
            "price_usd": pair.get("priceUsd", "N/A"),
            "liquidity_usd": pair.get("liquidity", {}).get("usd", "N/A"),
            "dexscreener_url": pair.get("url", f"https://dexscreener.com/solana/{ca}"),
        }
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return None


def send_telegram_alert(ca, tweet_url, info):
    text = (
        f"🚨 New CA detected from @{TWITTER_USERNAME}\n\n"
        f"Token: {info['name']} ({info['symbol']})\n"
        f"CA: `{ca}`\n"
        f"Price: ${info['price_usd']}\n"
        f"Liquidity: ${info['liquidity_usd']}\n\n"
        f"Chart: {info['dexscreener_url']}\n"
        f"Buy (Jupiter): https://jup.ag/swap/SOL-{ca}\n"
        f"Tweet: {tweet_url}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("[ALERT SENT]", ca)
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")


def send_startup_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": f"✅ CA Tracker started. Monitoring @{TWITTER_USERNAME}."}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[ERROR] Startup message failed: {e}")


def run_test_mode():
    """Sends one real test alert using a known pump.fun CA, so you can confirm
    Telegram formatting and DexScreener verification work end-to-end."""
    print("[TEST MODE] Running a one-time test alert...")
    test_ca = "9cRCn9rGT8V2imeM2BaKs13yhMEais3ruM3rPvTGpump"
    info = verify_token(test_ca)
    if info:
        send_telegram_alert(test_ca, "https://twitter.com/stoolpresidente/status/test", info)
        print("[TEST MODE] Alert sent successfully. Check your Telegram.")
    else:
        print("[TEST MODE] Could not verify test CA on DexScreener (token may be delisted/old). "
              "Sending a raw alert instead so you can still confirm Telegram delivery works.")
        fallback_info = {
            "name": "TEST TOKEN", "symbol": "TEST", "price_usd": "N/A",
            "liquidity_usd": "N/A", "dexscreener_url": f"https://dexscreener.com/solana/{test_ca}",
        }
        send_telegram_alert(test_ca, "https://twitter.com/stoolpresidente/status/test", fallback_info)


def main():
    print(f"Starting CA tracker for @{TWITTER_USERNAME}...")

    # Start the keep-alive web server in a background thread
    # (Render pings this URL via UptimeRobot so the free web service never sleeps)
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    send_startup_message()

    # Set TEST_MODE=1 as an environment variable on Render to trigger a one-time test alert
    if os.environ.get("TEST_MODE") == "1":
        run_test_mode()

    seen = load_seen()

    while True:
        tweets = get_latest_tweets(TWITTER_USERNAME)
        for tweet in reversed(tweets):  # oldest first
            tid = str(tweet.id)
            if tid in seen:
                continue

            seen.add(tid)
            save_seen(tid)

            ca = extract_ca(tweet.rawContent)
            if ca:
                print(f"[FOUND CA] {ca} in tweet {tid}")
                info = verify_token(ca)
                if info:
                    send_telegram_alert(ca, tweet.url, info)
                else:
                    print(f"[SKIPPED] {ca} — not verified on DexScreener yet")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
