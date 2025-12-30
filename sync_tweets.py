import os
import time
import sys
import re
import tweepy
import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from ntscraper import Nitter
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

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

# Pool of Nitter instances
NITTER_INSTANCES = ["https://nitter.net", "https://xcancel.com", "https://nitter.poast.org", "https://nitter.privacydev.net"]

def get_uc_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="MacIntel", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    return driver

def get_tweets_tweepy():
    print("🛰️ Method 1: Tweepy API...")
    if not BEARER_TOKEN: return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=15, tweet_fields=['created_at', 'text'])
        if response.data:
            return [{"id": str(t.id), "text": t.text, "ts": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e: print(f"⚠️ API skip: {e}")
    return []

def get_tweets_wayback():
    print("🏛️ Method 2: Wayback Machine Deep Scrape...")
    wayback_data = []
    try:
        # 1. Get the list of snapshots for statuses
        cdx_url = f"http://web.archive.org/cdx/search/cdx?url=x.com/{USERNAME}/status/&matchType=prefix&output=json&limit=5&filter=statuscode:200"
        response = requests.get(cdx_url, timeout=15)
        if response.status_code != 200: return []
        
        results = response.json()
        # Each 'r' is [timestamp, original_url, etc]
        for r in results[1:]: 
            ts_archive = r[1] # e.g. 20251229123000
            orig_url = r[2]
            match = re.search(r'status/(\d+)', orig_url)
            if not match: continue
            tid = match.group(1)
            
            # 2. Fetch the actual archived page to get content
            memento_url = f"https://web.archive.org/web/{ts_archive}/{orig_url}"
            try:
                page = requests.get(memento_url, timeout=10)
                soup = BeautifulSoup(page.text, 'lxml')
                
                # Try finding text in different Twitter UI versions
                text = ""
                # Newer X layout
                text_el = soup.find("div", {"data-testid": "tweetText"})
                if text_el: 
                    text = text_el.get_text()
                else:
                    # Older Twitter layout
                    text_el = soup.find("p", class_="tweet-text") or soup.find("div", class_="tweet-text")
                    if text_el: text = text_el.get_text()

                # Try finding the original date
                date_str = "Archived Date"
                time_el = soup.find("time")
                if time_el and time_el.has_attr('datetime'):
                    date_str = time_el['datetime'].replace('T', ' ').split('.')[0]
                
                if text:
                    wayback_data.append({
                        "id": tid, "text": f"[Wayback]: {text}", "ts": time.time(),
                        "date": date_str, "link": f"https://x.com/{USERNAME}/status/{tid}"
                    })
            except: continue
        
        print(f"✅ Wayback recovered {len(wayback_data)} full posts.")
    except Exception as e: print(f"⚠️ Wayback Error: {e}")
    return wayback_data

def get_tweets_bing():
    print("🔍 Method 3: Bing Search Scraping...")
    driver = get_uc_driver()
    bing_data = []
    try:
        driver.get(f"https://www.bing.com/search?q=site%3ax.com%2f{USERNAME}%2fstatus")
        time.sleep(5)
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'status/')]")
        for link in links:
            href = link.get_attribute("href")
            match = re.search(r'status/(\d+)', href)
            if match:
                tid = match.group(1)
                bing_data.append({
                    "id": tid, "text": "[Link found via Bing Index]", "ts": time.time(),
                    "date": f"{datetime.now().strftime('%Y-%m-%d')} (Bing)", "link": f"https://x.com/{USERNAME}/status/{tid}"
                })
    except: pass
    finally: driver.quit()
    return bing_data

def get_tweets_ntscraper():
    print("🕵️ Method 4: NTScraper...")
    try:
        scraper = Nitter()
        results = scraper.get_tweets(USERNAME, mode='user', number=10)
        data = []
        for t in results['tweets']:
            tid = t['link'].split('/')[-1]
            data.append({"id": tid, "text": t['text'], "ts": time.time(), "date": t['date'], "link": t['link']})
        print(f"✅ NTScraper found {len(data)} items.")
        return data
    except: return []

def get_tweets_from_google():
    print(f"🔍 Method 5: Google Search Scraping...")
    driver = get_uc_driver()
    google_data = []
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)
        try:
            btns = driver.find_elements(By.XPATH, "//button[contains(., 'Accept') or contains(., 'Agree')]")
            if btns: btns[0].click(); time.sleep(2)
        except: pass
        
        cards = driver.find_elements(By.XPATH, '//div[@role="listitem"] | //div[contains(@class, "dRzkFf")]')
        for card in cards:
            try:
                link_tag = card.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                tid = re.search(r'status/(\d+)', link_tag.get_attribute("href")).group(1)
                text = card.find_element(By.CLASS_NAME, 'xcQxib').text
                unix_ts = int(card.find_element(By.CSS_SELECTOR, '[data-ts]').get_attribute("data-ts"))
                google_data.append({
                    "id": tid, "text": text, "ts": unix_ts,
                    "date": datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M"),
                    "link": f"https://x.com/{USERNAME}/status/{tid}"
                })
            except: continue
        print(f"✅ Google found {len(google_data)} items.")
    except: pass
    finally: driver.quit()
    return google_data

def get_tweets_rss():
    print("📻 Method 6: Nitter RSS...")
    for inst in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{inst}/{USERNAME}/rss")
            if feed.entries:
                data = []
                for entry in feed.entries:
                    tid = re.search(r'status/(\d+)', entry.link).group(1)
                    data.append({"id": tid, "text": entry.title, "ts": time.mktime(entry.published_parsed), "date": datetime.fromtimestamp(time.mktime(entry.published_parsed)).strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{tid}"})
                print(f"✅ RSS found {len(data)} items.")
                return data
        except: continue
    return []

def update_markdown(all_tweets):
    if not all_tweets: return
    # Sort by Snowflake ID (Numerical)
    all_tweets.sort(key=lambda x: int(x['id']), reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f: existing_content = f.read()
    
    new_entries = ""
    new_count = 0
    for t in all_tweets:
        if t['id'] not in existing_content:
            new_entries += f"### {t['date']}\n{t['text']}\n\n*[Link]({t['link']})*\n\n---\n\n"
            new_count += 1
    
    if new_count > 0:
        clean_old = existing_content.replace(HEADER, "")
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(HEADER + new_entries + clean_old)
        print(f"🚀 SUCCESS: Added {new_count} new items to the top.")
    else:
        print("😴 No new unique items found.")

if __name__ == "__main__":
    combined = get_tweets_tweepy() + get_tweets_wayback() + get_tweets_bing() + \
               get_tweets_ntscraper() + get_tweets_from_google() + get_tweets_rss()
    
    # Deduplicate by ID
    unique = {t['id']: t for t in combined if t['id']}
    
    if not unique:
        print("❌ All methods failed to retrieve data.")
        sys.exit(1)
        
    update_markdown(list(unique.values()))
