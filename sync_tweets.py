import os
import time
import sys
import re
import tweepy
import feedparser
from datetime import datetime
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

# A list of Nitter instances to try for RSS
NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net"
]

def get_uc_driver():
    """Returns an undetected-chromedriver instance to bypass Cloudflare."""
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    # Setting a Mac-like user agent
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = uc.Chrome(options=options)
    return driver

def get_tweets_tweepy():
    print("🛰️ Attempting Tweepy API fetch...")
    if not BEARER_TOKEN: return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=10, tweet_fields=['created_at', 'text'])
        if response.data:
            print(f"✅ API found {len(response.data)} items.")
            return [{"id": str(t.id), "text": t.text, "timestamp": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ API Error: {e}")
    return []

def get_tweets_from_sotwe():
    print(f"🌊 Attempting Sotwe (Cloudflare Bypass)...")
    driver = get_uc_driver()
    sotwe_data = []
    try:
        driver.get(f"https://www.sotwe.com/{USERNAME}")
        time.sleep(10) # Wait for Cloudflare Turnstile to clear

        # Sotwe usually lists tweets in containers with class 'tweet-item' or 'item'
        tweets = driver.find_elements(By.CSS_SELECTOR, '.tweet-item, .item')
        for t in tweets:
            try:
                text = t.find_element(By.CLASS_NAME, 'text').text
                link_el = t.find_element(By.XPATH, ".//a[contains(@href, '/status/')]")
                href = link_el.get_attribute("href")
                tweet_id = href.split('/')[-1]
                sotwe_data.append({
                    "id": tweet_id,
                    "text": text,
                    "timestamp": int(time.time()), # Approximate
                    "date": "Sotwe Archive",
                    "link": f"https://x.com/{USERNAME}/status/{tweet_id}"
                })
            except: continue
        print(f"✅ Sotwe found {len(sotwe_data)} items.")
    except Exception as e:
        print(f"⚠️ Sotwe Scraper Error: {e}")
    finally:
        driver.quit()
    return sotwe_data

def get_tweets_nitter_rss():
    print("📻 Attempting Nitter RSS fetch...")
    rss_data = []
    for instance in NITTER_INSTANCES:
        try:
            feed_url = f"{instance}/{USERNAME}/rss"
            feed = feedparser.parse(feed_url)
            if feed.entries:
                for entry in feed.entries:
                    match = re.search(r'status/(\d+)', entry.link)
                    if match:
                        tweet_id = match.group(1)
                        ts = time.mktime(entry.published_parsed)
                        rss_data.append({
                            "id": tweet_id,
                            "text": f"[RSS]: {entry.title}",
                            "timestamp": ts,
                            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                            "link": f"https://x.com/{USERNAME}/status/{tweet_id}"
                        })
                print(f"✅ Nitter RSS found {len(rss_data)} items from {instance}")
                return rss_data
        except Exception as e:
            print(f"⚠️ Nitter Error ({instance}): {e}")
            continue
    return []

def get_tweets_from_google():
    print(f"🔍 Scraping Google for '{USERNAME} twitter'...")
    driver = get_uc_driver()
    google_data = []
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)

        # Handle Cookie Consent
        try:
            btns = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'I agree')]")
            if btns: btns[0].click(); time.sleep(2)
        except: pass

        # Targeted Selectors from your Mac Chrome source code
        cards = driver.find_elements(By.XPATH, '//div[@role="listitem"] | //div[contains(@class, "dRzkFf")]')
        for card in cards:
            try:
                link_tag = card.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                href = link_tag.get_attribute("href")
                match = re.search(r'status/(\d+)', href)
                if not match: continue
                tweet_id = match.group(1)
                text = card.find_element(By.CLASS_NAME, 'xcQxib').text
                ts_el = card.find_element(By.CSS_SELECTOR, '[data-ts]')
                unix_ts = int(ts_el.get_attribute("data-ts"))
                
                google_data.append({
                    "id": tweet_id,
                    "text": text,
                    "timestamp": unix_ts,
                    "date": datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M"),
                    "link": f"https://x.com/{USERNAME}/status/{tweet_id}"
                })
            except: continue
        print(f"✅ Google found {len(google_data)} items.")
    except Exception as e:
        print(f"⚠️ Google Error: {e}")
    finally:
        driver.quit()
    return google_data

def update_markdown(combined_data):
    if not combined_data: return False
    
    # Sort: Newest First (Descending based on ID)
    combined_data.sort(key=lambda x: int(x['id']), reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            existing_content = f.read()

    new_entries_text = ""
    new_count = 0
    for tweet in combined_data:
        # Deduplicate by ID
        if tweet['id'] not in existing_content:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries_text += entry
            new_count += 1

    if new_count == 0:
        print("😴 No new unique items to add.")
        return True

    # Prepend new entries to the file
    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} items to the top of {FILE_NAME}.")
    return True

if __name__ == "__main__":
    # Aggregating all results
    all_results = get_tweets_tweepy() + \
                  get_tweets_from_sotwe() + \
                  get_tweets_nitter_rss() + \
                  get_tweets_from_google()
    
    # Final Deduplication using Dictionary (Key is Tweet ID)
    master_dict = {t['id']: t for t in all_results}
    final_list = list(master_dict.values())
    
    if not final_list:
        print("❌ All methods failed to find data.")
        sys.exit(1)
        
    update_markdown(final_list)
