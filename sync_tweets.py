import tweepy
import os
import datetime
import sys
from googlesearch import search

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

def get_tweets_from_api():
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    try:
        user = client.get_user(username=USERNAME)
        response = client.get_users_tweets(
            id=user.data.id, 
            max_results=20, 
            tweet_fields=['created_at', 'text']
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"⚠️ Tweepy API Error (likely tier limit): {e}")
        return []

def get_tweets_from_google():
    print(f"🔍 Searching Google for recent {USERNAME} activity...")
    query = f"site:x.com/{USERNAME}"
    found_links = []
    
    try:
        # We search for the 10 most recent indexed results
        for url in search(query, num_results=10):
            if f"status/" in url:
                found_links.append(url)
    except Exception as e:
        print(f"⚠️ Google Search Error: {e} (Google may be blocking this IP)")
        
    return found_links

def update_markdown(api_tweets, google_links):
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# My X Archive (Hybrid Sync)\n\n")

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        content = f.read()

    new_count = 0
    with open(FILE_NAME, "a", encoding="utf-8") as f:
        # 1. Process API Tweets
        for tweet in api_tweets:
            if str(tweet.id) not in content:
                f.write(f"### {tweet.created_at}\n{tweet.text}\n\n")
                f.write(f"*[Link](https://x.com/i/status/{tweet.id})*\n\n---\n\n")
                content += str(tweet.id) # Prevent double adding in same run
                new_count += 1

        # 2. Process Google Links (Fallback)
        for url in google_links:
            tweet_id = url.split('/')[-1]
            if tweet_id not in content:
                f.write(f"### [Archived via Google Search]\n")
                f.write(f"New activity found via Google indexing.\n\n")
                f.write(f"*[Link to Post]({url})*\n\n---\n\n")
                new_count += 1

    print(f"✅ Added {new_count} new items to {FILE_NAME}")

if __name__ == "__main__":
    # Check if API is working
    api_data = get_tweets_from_api()
    
    # Supplement with Google Search
    google_data = get_tweets_from_google()
    
    if not api_data and not google_data:
        print("❌ Failed to find any data via API or Google Search.")
        # If both fail, we exit with error to turn the GitHub Action RED
        sys.exit(1)
        
    update_markdown(api_data, google_data)
