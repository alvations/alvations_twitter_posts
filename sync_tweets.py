import os
import re
import sys
import time
import tweepy
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
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

def get_tweets_tweepy():
    print("🛰️ Attempting Tweepy API fetch...")
    if not BEARER_TOKEN: return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(id=user.data.id, max_results=10, tweet_fields=['created_at', 'text'])
        if response.data:
            return [{"id": str(t.id), "text": t.text, "timestamp": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ Tweepy API Error: {e}")
    return []

def get_tweets_from_google():
    print(f"🔍 Scraping Google Search for '{USERNAME} twitter' with Stealth...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Apply Stealth to look like a real Mac browser
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    google_data = []
    
    try:
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5) 

        # 1. Targeted Parsing (Based on your HTML)
        # We look for the carousel items (role="listitem")
        items = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
        print(f"DEBUG: Found {len(items)} list items on page.")

        for item in items:
            try:
                # Get the link (href contains status/)
                link_tag = item.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                href = link_tag.get_attribute("href")
                
                # Extract ID via Regex
                match = re.search(r'status/(\d+)', href)
                if not match: continue
                tweet_id = match.group(1)
                tweet_link = f"https://x.com/{USERNAME}/status/{tweet_id}"

                # Get Text (Targeting class 'xcQxib' from your HTML)
                text = item.find_element(By.CLASS_NAME, 'xcQxib').text

                # Get Timestamp (Targeting 'data-ts' from your HTML)
                ts_element = item.find_element(By.CSS_SELECTOR, 'span[data-ts]')
                unix_ts = int(ts_element.get_attribute("data-ts"))
                readable_date = datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M")

                google_data.append({
                    "id": tweet_id,
                    "text": text,
                    "timestamp": unix_ts,
                    "date": readable_date,
                    "link": tweet_link
                })
                print(f"✅ Found via Google: {tweet_id}")
            except:
                continue

        if not google_data:
            print("⚠️ Carousel not found. Google might be blocking the rich results for this IP.")

    except Exception as e:
        print(f"⚠️ Google Scraping Error: {e}")
    finally:
        driver.quit()
    return google_data

def update_markdown(combined_data):
    if not combined_data: return False
    
    # Sort: Newest First
    combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            existing_content = f.read()

    new_entries_text = ""
    new_count = 0
    for tweet in combined_data:
        if tweet['id'] not in existing_content:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries_text += entry
            new_count += 1

    if new_count == 0:
        print("😴 No new items found.")
        return True

    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} items to the top of the file.")
    return True

if __name__ == "__main__":
    api = get_tweets_tweepy()
    google = get_tweets_from_google()
    
    # Merge and Deduplicate by ID
    merged = {t['id']: t for t in (google + api)}
    final_list = list(merged.values())
    
    if not final_list:
        print("❌ Both fetch methods failed.")
        sys.exit(1)
        
    update_markdown(final_list)
