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

NITTER_INSTANCES = ["https://xcancel.com", "https://nitter.poast.org", "https://nitter.privacydev.net"]

def get_uc_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="MacIntel", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    return driver

def get_tweets_tweepy():
    print("🛰️ API fetch...")
    if not BEARER_TOKEN: return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=15, tweet_fields=['created_at', 'text'])
        if response.data:
            return [{"id": str(t.id), "text": t.text, "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except: pass
    return []

def get_tweets_wayback():
    print("🏛️ Wayback Deep Scrape...")
    data = []
    try:
        cdx = f"http://web.archive.org/cdx/search/cdx?url=x.com/{USERNAME}/status/&matchType=prefix&output=json&limit=5&filter=statuscode:200"
        res = requests.get(cdx, timeout=15).json()
        for r in res[1:]:
            ts, orig_url = r[1], r[2]
            tid = re.search(r'status/(\d+)', orig_url).group(1)
            page = requests.get(f"https://web.archive.org/web/{ts}/{orig_url}", timeout=10)
            soup = BeautifulSoup(page.text, 'lxml')
            text_el = soup.find("div", {"data-testid": "tweetText"}) or soup.find("p", class_="tweet-text")
            time_el = soup.find("time")
            date = time_el['datetime'].replace('T', ' ').split('.')[0] if time_el else "Archived"
            if text_el: data.append({"id": tid, "text": text_el.get_text(), "date": date, "link": f"https://x.com/{USERNAME}/status/{tid}"})
    except: pass
    return data

def get_tweets_ntscraper():
    print("🕵️ NTScraper...")
    try:
        scraper = Nitter()
        results = scraper.get_tweets(USERNAME, mode='user', number=10)
        return [{"id": t['link'].split('/')[-1], "text": t['text'], "date": t['date'], "link": t['link']} for t in results['tweets']]
    except: return []

def get_tweets_from_google():
    print("🔍 Google Scrape...")
    driver = get_uc_driver()
    data = []
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)
        try: driver.find_element(By.XPATH, "//button[contains(., 'Accept')]").click(); time.sleep(2)
        except: pass
        cards = driver.find_elements(By.XPATH, '//div[@role="listitem"] | //div[contains(@class, "dRzkFf")]')
        for card in cards:
            try:
                link = card.find_element(By.XPATH, './/a[contains(@href, "status/")]').get_attribute("href")
                tid = re.search(r'status/(\d+)', link).group(1)
                text = card.find_element(By.CLASS_NAME, 'xcQxib').text
                ts = int(card.find_element(By.CSS_SELECTOR, '[data-ts]').get_attribute("data-ts"))
                data.append({"id": tid, "text": text, "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{tid}"})
            except: continue
    except: pass
    finally: driver.quit()
    return data

def get_tweets_rss():
    print("📻 RSS Feeds...")
    for inst in NITTER_INSTANCES:
        try:
            feed = feedparser.parse(f"{inst}/{USERNAME}/rss")
            if feed.entries:
                return [{"id": re.search(r'status/(\d+)', e.link).group(1), "text": e.title, "date": datetime.fromtimestamp(time.mktime(e.published_parsed)).strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{re.search(r'status/(\d+)', e.link).group(1)}"} for e in feed.entries]
        except: continue
    return []

def get_tweets_bing():
    print("🔎 Bing Scrape...")
    driver = get_uc_driver()
    data = []
    try:
        driver.get(f"https://www.bing.com/search?q=site%3ax.com%2f{USERNAME}%2fstatus")
        time.sleep(5)
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'status/')]")
        for link in links:
            href = link.get_attribute("href")
            match = re.search(r'status/(\d+)', href)
            if match:
                tid = match.group(1)
                data.append({"id": tid, "text": "[Indexed by Bing]", "date": "Search Result", "link": f"https://x.com/{USERNAME}/status/{tid}"})
    except: pass
    finally: driver.quit()
    return data

# --- FILE PROCESSING ---

def parse_existing_markdown():
    """Parses the .md file and returns a list of tweet dictionaries."""
    tweets = []
    if not os.path.exists(FILE_NAME): return tweets
    
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by the separator
    sections = content.split("---\n\n")
    for section in sections:
        try:
            # Regex to find parts of the post
            date_match = re.search(r'### (.*?)\n', section)
            link_match = re.search(r'\*\[Link\]\((.*?status/(\d+).*?)\)\*', section)
            
            if date_match and link_match:
                # Find text: everything between the date header and the link
                text_start = date_match.end()
                text_end = link_match.start()
                text = section[text_start:text_end].strip()
                
                tweets.append({
                    "id": link_match.group(2),
                    "text": text,
                    "date": date_match.group(1),
                    "link": link_match.group(1)
                })
        except: continue
    return tweets

def sync():
    # 1. Pull from all sources
    new_data = get_tweets_tweepy() + get_tweets_wayback() + get_tweets_ntscraper() + \
               get_tweets_from_google() + get_tweets_rss() + get_tweets_bing()
    
    # 2. Pull existing from file
    existing_data = parse_existing_markdown()
    
    # 3. Merge and Deduplicate (Keyed by ID)
    master_dict = {t['id']: t for t in (existing_data + new_data) if t.get('id')}
    
    # 4. Sort Globally (Snowflake ID descending = Latest First)
    all_sorted = sorted(master_dict.values(), key=lambda x: int(x['id']), reverse=True)
    
    # 5. Build File Content
    output = HEADER
    for t in all_sorted:
        output += f"### {t['date']}\n{t['text']}\n\n*[Link]({t['link']})*\n\n---\n\n"
    
    # 6. Atomic Write
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"✅ Sync Complete. Total Archive Size: {len(all_sorted)} posts.")

if __name__ == "__main__":
    sync()
