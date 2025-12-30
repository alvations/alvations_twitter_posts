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
            return [{"id": str(t.id), "text": t.text, "date": t.created_at.strftime("%Y-%m-%d %H:%M"), "link": f"https://x.com/i/status/{t.id}"} for t in response.data]
    except Exception as e:
        print(f"⚠️ API Error: {e}")
    return []

def get_tweets_selenium():
    print(f"🌐 Attempting Stealth Selenium Scraping...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Newer headless mode is harder to detect
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Hide the fact that we are a bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Use the Search URL instead of Profile URL (sometimes bypasses login wall)
    search_url = f"https://x.com/search?q=(from%3A{USERNAME})&f=live"
    scraped_data = []
    
    try:
        driver.get(search_url)
        time.sleep(10) # Give it plenty of time to load
        
        articles = driver.find_elements(By.TAG_NAME, "article")
        
        if not articles:
            print("❌ No articles found. X is likely showing a Login Wall.")
            # DEBUG: Print the page title to see what the bot sees
            print(f"DEBUG: Page Title is '{driver.title}'")
            if "Log in" in driver.title or "X / ?" in driver.title:
                print("🚨 CONFIRMED: X is blocking this guest session with a Login Wall.")
        
        for article in articles:
            try:
                text = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
                links = article.find_elements(By.XPATH, './/a')
                tweet_link = ""
                for l in links:
                    href = l.get_attribute("href")
                    if href and "/status/" in href:
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
    except Exception as e:
        print(f"⚠️ Selenium Error: {e}")
    finally:
        driver.quit()
    return scraped_data

def update_markdown(combined_data):
    if not combined_data:
        return False
    
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
        print("😴 No new items found.")
        return True

    clean_old = existing_content.replace(HEADER, "")
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(HEADER + new_entries_text + clean_old)
    
    print(f"🚀 Success: Added {new_count} items to top.")
    return True

if __name__ == "__main__":
    api = get_tweets_tweepy()
    web = get_tweets_selenium()
    
    merged = {t['id']: t for t in (web + api)}
    final = list(merged.values())
    
    if not final:
        print("❌ All methods failed. X is blocking automation.")
        sys.exit(1)
        
    update_markdown(final)
