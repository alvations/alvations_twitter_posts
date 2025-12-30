import os
import time
import sys
import re
import tweepy
import feedparser
from datetime import datetime
from ntscraper import Nitter
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

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

# Pool of Nitter instances for RSS fallback
NITTER_INSTANCES = [
    "https://nitter.net", 
    "https://xcancel.com", 
    "https://nitter.poast.org",
    "https://nitter.privacydev.net", 
    "https://nitter.cz"
]

def get_uc_driver():
    """Bypasses bot detection using undetected-chromedriver."""
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return uc.Chrome(options=options)

def get_tweets_tweepy():
    print("🛰️ Method 1: Tweepy API...")
    if not BEARER_TOKEN: 
        print("⚠️ No BEARER_TOKEN found.")
        return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=10, tweet_fields=['created_at', 'text'])
        if response.data:
            return [{"id": str(t.id), "text": t.text, "ts": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e: 
        print(f"⚠️ API skip: {e}")
    return []

def get_tweets_ntscraper():
    print("🕵️ Method 2: NTScraper...")
    try:
        scraper = Nitter()
        results = scraper.get_tweets(USERNAME, mode='user', number=10)
        data = []
        for t in results['tweets']:
            link = t['link']
            tid = link.split('/')[-1]
            # Convert string date like 'Dec 30, 2025 · 1:00 AM UTC' to timestamp
            try:
                ts = datetime.strptime(t['date'], "%b %d, %Y · %I:%M %p %Z").timestamp()
            except:
                ts = time.time()
            data.append({
                "id": tid, "text": t['text'], "ts": ts,
                "date": t['date'], "link": link
            })
        print(f"✅ NTScraper found {len(data)} items.")
        return data
    except Exception as e: 
        print(f"⚠️ NTScraper skip: {e}")
        return []

def get_tweets_from_google():
    print(f"🔍 Method 3: Google Search Scraping...")
    driver = get_uc_driver()
    google_data = []
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)
        
        # Cookie Buster for Google
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Agree')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                print("🍪 Bypassed Google Cookie Consent.")
                time.sleep(2)
        except: pass

        # Scrape based on provided Mac Chrome HTML sample
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
    except Exception as e: 
        print(f"⚠️ Google skip: {e}")
    finally: 
        driver.quit()
    return google_data

def get_tweets_rss():
    print("📻 Method 4: RSS Feeds...")
    data = []
    for inst in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{inst}/{USERNAME}/rss")
            if feed.entries:
                for entry in feed.entries:
                    tid_match = re.search(r'status/(\d+)', entry.link)
                    if tid_match:
                        tid = tid_match.group(1)
                        ts = time.mktime(entry.published_parsed)
                        data.append({
                            "id": tid, "text": entry.title, "ts": ts, 
                            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"), 
                            "link": f"https://x.com/{USERNAME}/status/{tid}"
                        })
                print(f"✅ RSS found {len(data)} items from {inst}")
                break # Stop if we found a working instance
        except: continue
    return data

def update_markdown(all_tweets):
    if not all_tweets: return
    
    # Sort numerically by ID (Largest/Newest ID first)
    all_tweets.sort(key=lambda x: int(x['id']), reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f: 
            existing_content = f.read()

    new_entries_block = ""
    new_count = 0
    for t in all_tweets:
        # Check for duplication
        if t['id'] not in existing_content:
            new_entries_block += f"### {t['date']}\n{t['text']}\n\n*[Link]({t['link']})*\n\n---\n\n"
            new_count += 1
    
    if new_count > 0:
        # Clean header to avoid stacking multiple titles
        clean_old = existing_content.replace(HEADER, "")
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(HEADER + new_entries_block + clean_old)
        print(f"🚀 Success! Added {new_count} items to the top of the file.")
    else:
        print("😴 No new unique tweets found.")

if __name__ == "__main__":
    # Aggregating all results
    combined_results = get_tweets_tweepy() + \
                       get_tweets_ntscraper() + \
                       get_tweets_from_google() + \
                       get_tweets_rss()
    
    # Deduplicate using dictionary (Key = ID)
    unique_tweets = {t['id']: t for t in combined_results}
    
    if not unique_tweets:
        print("❌ All methods returned 0 items. Site structure likely changed or IP is blocked.")
        sys.exit(1)
        
    update_markdown(list(unique_tweets.values()))
