import datetime
import os
import time
import sys
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

def get_tweets_tweepy():
    print("🛰️ Attempting Tweepy API fetch...")
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        # Fetching last 20 tweets/replies
        response = client.get_users_tweets(
            id=user.data.id, 
            max_results=20, 
            tweet_fields=['created_at', 'text']
        )
        if response.data:
            print(f"✅ API found {len(response.data)} posts.")
            return [{"id": str(t.id), "text": t.text, "date": str(t.created_at), "link": f"https://x.com/i/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ Tweepy API Error (likely Free Tier restriction): {e}")
    return []

def get_tweets_selenium():
    print(f"🌐 Attempting Selenium Scraping for @{USERNAME}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    scraped_data = []
    
    try:
        driver.get(f"https://x.com/{USERNAME}")
        # Wait for posts to load
        time.sleep(5) 
        articles = driver.find_elements(By.TAG_NAME, "article")
        
        for article in articles:
            try:
                # Get Text
                text = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                # Get ID/Link
                links = article.find_elements(By.XPATH, './/a')
                tweet_link = ""
                for l in links:
                    href = l.get_attribute("href")
                    if href and "/status/" in href and USERNAME in href:
                        tweet_link = href
                        break
                
                if text and tweet_link:
                    tweet_id = tweet_link.split('/')[-1].split('?')[0]
                    scraped_data.append({
                        "id": tweet_id,
                        "text": text,
                        "date": "Scraped via Web",
                        "link": tweet_link
                    })
            except:
                continue
        print(f"✅ Selenium found {len(scraped_data)} posts.")
    except Exception as e:
        print(f"⚠️ Selenium Scraper Error: {e}")
    finally:
        driver.quit()
    return scraped_data

def update_markdown(combined_data):
    if not combined_data:
        return False

    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# My X Archive (Hybrid API + Selenium)\n\n")

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        existing_content = f.read()

    new_entries = []
    # De-duplicate by ID
    seen_ids = set()

    for tweet in combined_data:
        if tweet['id'] not in existing_content and tweet['id'] not in seen_ids:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries.append(entry)
            seen_ids.add(tweet['id'])

    if new_entries:
        with open(FILE_NAME, "a", encoding="utf-8") as f:
            f.write("".join(reversed(new_entries))) # Oldest to newest
        print(f"🚀 Success: Added {len(new_entries)} new items.")
        return True
    
    print("😴 No new unique items found.")
    return True

if __name__ == "__main__":
    api_posts = get_tweets_tweepy()
    web_posts = get_tweets_selenium()
    
    # Merge both lists
    all_data = api_posts + web_posts
    
    if not all_data:
        print("❌ Both API and Selenium failed to find data.")
        sys.exit(1)
        
    update_markdown(all_data)
