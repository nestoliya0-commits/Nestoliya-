"""
CA Tracker Bot (GitHub Actions version, multi-account)
--------------------------------------------------------
Runs ONCE per execution (GitHub Actions schedules it every 30 min).
Checks the latest tweets from every account listed in accounts.txt for
pump.fun / Solana contract addresses, verifies them on DexScreener, and
sends a Telegram alert.
"""

import re
import os
import requests
import snscrape.modules.twitter as sntwitter

# ============ CONFIG ============
ACCOUNTS_FILE = "accounts.txt"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SEEN_TWEETS_FILE = "seen_tweets.txt"

# Solana address patterns
SOLANA_ADDRESS_RE = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
PUMPFUN_LINK_RE = re.compile(r'pump\.fun/(?:coin/)?([1-9A-HJ-NP-Za-km-z]{32,44})')
SOLANA_PREFIX_RE = re.compile(r'solana:([1-9A-HJ-NP-Za-km-z]{32,44})', re.IGNORECASE)


def load_accounts():
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            return [line.strip().lstrip("@") for line in f if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError:
        print(f"[ERROR] {ACCOUNTS_FILE} not found!")
        return []


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
    match = SOLANA_PREFIX_RE.search(text)
    if match:
        return match.group(1)

    match = PUMPFUN_LINK_RE.search(text)
    if match:
        return match.group(1)

    candidates = SOLANA_ADDRESS_RE.findall(text)
    for c in candidates:
        if c.lower().endswith("pump"):
            return c
    if candidates:
        return candidates[0]
    return None


def verify_token(ca):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        pairs = data.get("pairs")
        if not pairs:
            return None
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


def send_telegram_alert(username, ca, tweet_url, info):
    text = (
        f"🚨 New CA detected from @{username}\n\n"
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


def main():
    accounts = load_accounts()
    if not accounts:
        print("No accounts to check. Add usernames to accounts.txt")
        return

    print(f"Checking {len(accounts)} accounts...")
    seen = load_seen()

    for username in accounts:
        print(f"--- Checking @{username} ---")
        tweets = get_latest_tweets(username)

        if not tweets:
            print(f"No tweets fetched for @{username} (may be rate-limited or blocked).")
            continue

        for tweet in reversed(tweets):
            tid = str(tweet.id)
            if tid in seen:
                continue

            seen.add(tid)
            save_seen(tid)

            ca = extract_ca(tweet.rawContent)
            if ca:
                print(f"[FOUND CA] {ca} from @{username} in tweet {tid}")
                info = verify_token(ca)
                if info:
                    send_telegram_alert(username, ca, tweet.url, info)
                else:
                    print(f"[SKIPPED] {ca} — not verified on DexScreener yet")

    print("Check complete.")


if __name__ == "__main__":
    main()
    
