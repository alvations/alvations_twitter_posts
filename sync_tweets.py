import datetime
import os
import re
import sys
import time
import tweepy
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
            return [{"id": str(t.id), "text": t.text, "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/i/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ API Error: {e}")
    return []

def get_tweets_from_google():
    print(f"🌐 Scraping Google Search for site:x.com/{USERNAME}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    google_data = []
    
    try:
        # Search query to find specific posts
        query = "alvations+twitter" # f"site:x.com/{USERNAME}/status"
        driver.get(f"https://www.google.com/search?q={query}")
        time.sleep(5) # Wait for results

        # Find all search result blocks
        search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")
        
        for res in search_results:
            try:
                # Extract URL to get Tweet ID
                link_element = res.find_element(By.TAG_NAME, "a")
                url = link_element.get_attribute("href")
                
                # Extract Snippet Text
                # Google usually stores snippets in a div with class 'VwiC3b' or similar
                snippet = res.text.split('\n')[-1] # Simple fallback
                
                # Use regex to find status ID
                match = re.search(r'status/(\d+)', url)
                if match:
                    tweet_id = match.group(1)
                    google_data.append({
                        "id": tweet_id,
                        "text": f"[Google Snippet]: {snippet}",
                        "date": f"{time.strftime('%Y-%m-%d')} (Indexed)",
                        "link": f"https://x.com/{USERNAME}/status/{tweet_id}"
                    })
            except:
                continue
        
        print(f"✅ Google found {len(google_data)} indexed links.")
    except Exception as e:
        print(f"⚠️ Google Scraping Error: {e}")
    finally:
        driver.quit()
    return google_data

def update_markdown(combined_data):
    if not combined_data:
        return False
    
    # Sort Newest ID first
    combined_data.sort(key=lambda x: int(x['id']), reverse=True)
    
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
        print("😴 No new items found to add.")
        return True

    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} items to top of file.")
    return True

if __name__ == "__main__":
    api_results = get_tweets_tweepy()
    google_results = get_tweets_from_google()
    
    # Merge and Deduplicate
    merged = {t['id']: t for t in (google_results + api_results)}
    final_list = list(merged.values())
    
    if not final_list:
        print("❌ All backup methods failed. No data found.")
        sys.exit(1)
        
    update_markdown(final_list)
