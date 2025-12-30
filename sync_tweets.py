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
HEADER = "# My Daily X Archive (Latest First)\n\n"

def get_tweets_tweepy():
    print("🛰️ Attempting Tweepy API fetch...")
    if not BEARER_TOKEN:
        print("⚠️ No Bearer Token found in Secrets.")
        return []
    
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(
            id=user.data.id, 
            max_results=20, 
            tweet_fields=['created_at', 'text']
        )
        if response.data:
            print(f"✅ API found {len(response.data)} posts.")
            return [{"id": str(t.id), "text": t.text, "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/i/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ Tweepy API Error: {e}")
    return []

def get_tweets_selenium():
    print(f"🌐 Attempting Selenium Scraping for @{USERNAME}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    scraped_data = []
    
    try:
        driver.get(f"https://x.com/{USERNAME}")
        time.sleep(8) # Wait for dynamic content
        articles = driver.find_elements(By.TAG_NAME, "article")
        
        for article in articles:
            try:
                text = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                links = article.find_elements(By.XPATH, './/a')
                tweet_link = ""
                for l in links:
                    href = l.get_attribute("href")
                    if href and "/status/" in href and USERNAME in href:
                        tweet_link = href.split('?')[0]
                        break
                
                if text and tweet_link:
                    tweet_id = tweet_link.split('/')[-1]
                    scraped_data.append({
                        "id": tweet_id,
                        "text": text,
                        "date": f"{time.strftime('%Y-%m-%d %H:%M')} (Scraped)",
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
        print("😴 No data to process.")
        return False

    # 1. Sort combined data by ID (Snowflake IDs sort chronologically) 
    # Reverse=True puts the newest IDs at the start of our list
    combined_data.sort(key=lambda x: int(x['id']), reverse=True)

    # 2. Read existing content
    existing_content = ""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            existing_content = f.read()

    # 3. Filter for truly new tweets only
    new_entries_html = ""
    new_count = 0
    for tweet in combined_data:
        if tweet['id'] not in existing_content:
            entry = f"### {tweet['date']}\n{tweet['text']}\n\n"
            entry += f"*[Link]({tweet['link']})*\n\n---\n\n"
            new_entries_html += entry
            new_count += 1

    if new_count == 0:
        print("😴 No new unique items to add.")
        return True

    # 4. Reconstruct file: Header + New Tweets + Old Content (minus its old header)
    clean_old_content = existing_content.replace(HEADER, "")
    
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER)
        f.write(new_entries_html)
        f.write(clean_old_content)
    
    print(f"🚀 Success: Added {new_count} new items to the top of the file.")
    return True

if __name__ == "__main__":
    # Get data from both sources
    api_posts = get_tweets_tweepy()
    web_posts = get_tweets_selenium()
    
    # Merge lists (using dictionary to ensure ID uniqueness)
    merged_map = {t['id']: t for t in (web_posts + api_posts)}
    final_data = list(merged_map.values())
    
    if not final_data:
        print("❌ Both API and Selenium failed to find data.")
        sys.exit(1)
        
    update_markdown(final_data)
