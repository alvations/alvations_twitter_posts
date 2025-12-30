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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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
    if not BEARER_TOKEN:
        return []
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(
            id=user.data.id, 
            max_results=10, 
            tweet_fields=['created_at', 'text']
        )
        if response.data:
            print(f"✅ API found {len(response.data)} items.")
            return [{
                "id": str(t.id), 
                "text": t.text, 
                "timestamp": t.created_at.timestamp(),
                "date": t.created_at.strftime("%Y-%m-%d %H:%M"), 
                "link": f"https://x.com/{USERNAME}/status/{t.id}"
            } for t in response.data]
    except Exception as e:
        print(f"⚠️ API Error: {e}")
    return []

def get_tweets_from_google():
    print(f"🔍 Scraping Google Search for '{USERNAME} twitter'...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    google_data = []
    
    try:
        # Using the exact query you requested
        driver.get(f"https://www.google.com/search?q={USERNAME}+twitter")
        time.sleep(5) 

        # Based on your HTML, cards are in 'div' with role='listitem'
        # and contain links to x.com/alvations/status/...
        cards = driver.find_elements(By.XPATH, '//div[@role="listitem"]')
        
        for card in cards:
            try:
                # 1. Extract the Link and ID
                link_element = card.find_element(By.XPATH, './/a[contains(@href, "status/")]')
                full_link = link_element.get_attribute("href")
                # Clean the link (remove google tracking params)
                tweet_link = full_link.split('?')[0]
                tweet_id = tweet_link.split('/')[-1]

                # 2. Extract the Text (Class 'xcQxib' from your snippet)
                text_element = card.find_element(By.CLASS_NAME, 'xcQxib')
                text = text_element.text

                # 3. Extract the Timestamp (Attribute 'data-ts' from your snippet)
                # This is the most accurate way to sort!
                ts_element = card.find_element(By.XPATH, './/span[@data-ts]')
                unix_ts = int(ts_element.get_attribute("data-ts"))
                readable_date = datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M")

                if tweet_id and text:
                    google_data.append({
                        "id": tweet_id,
                        "text": text,
                        "timestamp": unix_ts,
                        "date": readable_date,
                        "link": tweet_link
                    })
            except Exception:
                continue
        
        print(f"✅ Google Scraper found {len(google_data)} items.")
    except Exception as e:
        print(f"⚠️ Google Scraping Error: {e}")
    finally:
        driver.quit()
    return google_data

def update_markdown(combined_data):
    if not combined_data:
        return False
    
    # Sort by Timestamp (Newest first)
    combined_data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            existing_content = f.read()

    new_entries_text = ""
    new_count = 0
    for tweet in combined_data:
        # Check if the specific Tweet ID is already in the file
        if tweet['id'] not in existing_content:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries_text += entry
            new_count += 1

    if new_count == 0:
        print("😴 No new items found to add.")
        return True

    # Overwrite the file: Header + New Content + Old Content (minus its original header)
    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} new items to top of {FILE_NAME}.")
    return True

if __name__ == "__main__":
    api_results = get_tweets_tweepy()
    google_results = get_tweets_from_google()
    
    # Merge and Deduplicate by Tweet ID
    merged = {t['id']: t for t in (google_results + api_results)}
    final_list = list(merged.values())
    
    if not final_list:
        print("❌ All fetch methods failed.")
        sys.exit(1)
        
    update_markdown(final_list)
