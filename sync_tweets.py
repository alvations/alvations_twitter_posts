import os
import time
import sys
import re
import tweepy
import feedparser
from datetime import datetime
from ntscraper import Nitter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import undetected_chromedriver as uc


"""
You can find your ID hidden in the code of your own profile page.
1. Open your profile on X (e.g., x.com/yourusername) in Chrome or Firefox.
2. Right-click anywhere on the page and select View Page Source.[10]
3. Press Ctrl + F (or Cmd + F on Mac) to search. Search for: rest_id
   You will see something like "rest_id":"123456789". That number is your User ID.
"""
# Configuration
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
USER_ID = "1511382325715742725"  # https://x.com/alvations
USERNAME = "alvations" # No need for numeric ID anymore
FILE_NAME = "my_tweets.md"
HEADER = "# My Daily X Archive (Latest First)\n\n"

# Pool of Nitter instances for RSS
NITTER_INSTANCES = [
    "https://nitter.net", "https://xcancel.com", "https://nitter.poast.org",
    "https://nitter.privacydev.net", "https://nitter.cz"
]

def get_uc_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return uc.Chrome(options=options)

def get_tweets_tweepy():
    print("🛰️ Method 1: Tweepy API...")
    if not BEARER_TOKEN: return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=10, tweet_fields=['created_at', 'text'])
        if response.data:
            return [{"id": str(t.id), "text": t.text, "ts": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e: print(f"⚠️ API skip: {e}")
    return []

def get_tweets_ntscraper():
    print("🕵️ Method 2: NTScraper...")
    try:
        scraper = Nitter()
        # terms=USERNAME, mode='user'
        results = scraper.get_tweets(USERNAME, mode='user', number=10)
        data = []
        for t in results['tweets']:
            link = t['link']
            tid = link.split('/')[-1]
            # Convert string date to timestamp
            ts = datetime.strptime(t['date'], "%b %d, %Y · %I:%M %p %Z").timestamp()
            data.append({
                "id": tid, "text": t['text'], "ts": ts,
                "date": t['date'], "link": link
            })
        print(f"✅ NTScraper found {len(data)} items.")
        return data
    except Exception as e: print(f"⚠️ NTScraper skip: {e}"); return []

def get_tweets_from_google():
    print(f"🔍 Method 3: Google Search Scraping...")
    driver = get_uc_driver()
    google_data = []
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)
        
        # COOKIE BUSTER: Specifically for Google on Cloud IPs
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'I agree')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                time.sleep(2)
        except: pass

        # Parse the Mac Chrome layout you provided
        cards = driver.find_elements(By.XPATH, '//div[@role="listitem"] | //div[contains(@class, "dRzkFf")]')
        for card in cards:
            try:
                link_tag = card.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                href = link_tag.get_attribute("href")
                tid = re.search(r'status/(\d+)', href).group(1)
                text = card.find_element(By.CLASS_NAME, 'xcQxib').text
                unix_ts = int(card.find_element(By.CSS_SELECTOR, '[data-ts]').get_attribute("data-ts"))
                google_data.append({
                    "id": tid, "text": text, "ts": unix_ts,
                    "date": datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M"),
                    "link": f"https://x.com/{USERNAME}/status/{tid}"
                })
            except: continue
        print(f"✅ Google found {len(google_data)} items.")
    except Exception as e: print(f"⚠️ Google Error: {e}")
    finally: driver.quit()
    return google_data

def get_tweets_from_sotwe():
    print(f"🌊 Method 4: Sotwe Scraping...")
    driver = get_uc_driver()
    data = []
    try:
        driver.get(f"https://www.sotwe.com/{USERNAME}")
        time.sleep(10)
        # Sotwe updated selector
        items = driver.find_elements(By.CSS_SELECTOR, 'div.tweet-item, div.item')
        for item in items:
            try:
                text = item.find_element(By.CSS_SELECTOR, '.text, .tweet-text').text
                href = item.find_element(By.XPATH, ".//a[contains(@href, '/status/')]").get_attribute("href")
                tid = href.split('/')[-1]
                data.append({"id": tid, "text": text, "ts": time.time(), "date": "Sotwe Archive", "link": href})
            except: continue
        print(f"✅ Sotwe found {len(data)} items.")
    except Exception as e: print(f"⚠️ Sotwe skip: {e}")
    finally: driver.quit()
    return data

def get_tweets_rss():
    print("📻 Method 5: RSS Feeds...")
    data = []
    for inst in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{inst}/{USERNAME}/rss")
            if feed.entries:
                for entry in feed.entries:
                    tid = re.search(r'status/(\d+)', entry.link).group(1)
                    ts = time.mktime(entry.published_parsed)
                    data.append({"id": tid, "text": entry.title, "ts": ts, "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{tid}"})
                print(f"✅ RSS found {len(data)} items from {inst}")
                break
        except: continue
    return data

def update_markdown(all_tweets):
    if not all_tweets: return
    # Sort numerically by ID (Newest First)
    all_tweets.sort(key=lambda x: int(x['id']), reverse=True)
    
    existing = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f: existing = f.read()

    new_content = ""
    new_count = 0
    for t in all_tweets:
        if t['id'] not in existing:
            new_content += f"### {t['date']}\n{t['text']}\n\n*[Link]({t['link']})*\n\n---\n\n"
            new_count += 1
    
    if new_count > 0:
        clean_old = existing.replace(HEADER, "")
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(HEADER + new_content + clean_old)
        print(f"🚀 Success! Added {new_count} items to the top.")
    else:
        print("😴 No new unique items found.")

if __name__ == "__main__":
    combined = get_tweets_tweepy() + get_tweets_ntscraper() + get_tweets_from_google() + get_tweets_from_sotwe() + get_tweets_rss()
    unique = {t['id']: t for t in combined}
    if not unique:
        print("❌ All methods failed.")
        sys.exit(1)
    update_markdown(list(unique.values()))
