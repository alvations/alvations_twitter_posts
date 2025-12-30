import os
import time
import sys
import re
import tweepy
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
            print(f"✅ API found {len(response.data)} items.")
            return [{"id": str(t.id), "text": t.text, "timestamp": t.created_at.timestamp(), "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/{USERNAME}/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ Tweepy API Error: {e}")
    return []

def get_tweets_from_google():
    print(f"🔍 Scraping Google Search for '{USERNAME} twitter'...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Stealth to prevent being flagged as a bot immediately
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
        # 1. Navigate to Google
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter&hl=en")
        time.sleep(5)

        # 2. THE COOKIE BUSTER: Click "Accept all" if it exists
        try:
            # Google often uses different IDs/Text for the accept button based on region
            # We look for common "Accept" labels
            btns = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Agree')]")
            if btns:
                btns[0].click()
                print("🍪 Google Cookie Consent bypassed.")
                time.sleep(3)
        except:
            pass

        # 3. Targeted extraction from the specific HTML you provided
        # The tweets in your example are in divs with role="listitem"
        elements = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
        print(f"DEBUG: Found {len(elements)} potential tweet containers.")

        for el in elements:
            try:
                # Find Link
                link_tag = el.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                href = link_tag.get_attribute("href")
                
                # Extract ID
                match = re.search(r'status/(\d+)', href)
                if not match: continue
                tweet_id = match.group(1)
                tweet_link = f"https://x.com/{USERNAME}/status/{tweet_id}"

                # Find Text (The user-provided class 'xcQxib')
                try:
                    text = el.find_element(By.CLASS_NAME, 'xcQxib').text
                except:
                    # Fallback to general text if class changed
                    text = el.text.split('\n')[0]

                # Find Timestamp (The user-provided attribute 'data-ts')
                try:
                    ts_el = el.find_element(By.CSS_SELECTOR, '[data-ts]')
                    unix_ts = int(ts_el.get_attribute("data-ts"))
                    readable_date = datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M")
                except:
                    unix_ts = int(time.time())
                    readable_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                if tweet_id and text:
                    google_data.append({
                        "id": tweet_id,
                        "text": text,
                        "timestamp": unix_ts,
                        "date": readable_date,
                        "link": tweet_link
                    })
                    print(f"✨ Found Tweet: {tweet_id}")
            except:
                continue

    except Exception as e:
        print(f"⚠️ Google Scraper Error: {e}")
    finally:
        driver.quit()
    
    return google_data

def update_markdown(combined_data):
    if not combined_data:
        print("❌ No data found from any source.")
        return False
    
    # Sort: Newest First
    combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            existing_content = f.read()

    new_entries_text = ""
    new_count = 0
    for tweet in combined_data:
        # Dedup by ID
        if tweet['id'] not in existing_content:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries_text += entry
            new_count += 1

    if new_count == 0:
        print("😴 All found tweets already exist in archive.")
        return True

    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} items to the top of {FILE_NAME}.")
    return True

if __name__ == "__main__":
    # Run API first
    api_items = get_tweets_tweepy()
    
    # Run Google Scraper second
    google_items = get_tweets_from_google()
    
    # Merge using a dictionary (Key = ID) to ensure uniqueness
    master_dict = {t['id']: t for t in (google_items + api_items)}
    final_list = list(master_dict.values())
    
    if not final_list:
        sys.exit(1) # Trigger Red status in Actions
        
    update_markdown(final_list)
