import tweepy
import os
import datetime

# Configuration
"""
You can find your ID hidden in the code of your own profile page.
1. Open your profile on X (e.g., x.com/yourusername) in Chrome or Firefox.
2. Right-click anywhere on the page and select View Page Source.[10]
3. Press Ctrl + F (or Cmd + F on Mac) to search. Search for: rest_id
   You will see something like "rest_id":"123456789". That number is your User ID.
"""

BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
USER_ID = "1511382325715742725"  # https://x.com/alvations
FILE_NAME = "my_tweets.md"

def get_tweets():
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    
    # Fetching the last 10 tweets (API Basic tier allows this)
    # We use user_auth=False for Bearer Token access
    response = client.get_users_tweets(
        id=USER_ID, 
        max_results=10, 
        tweet_fields=['created_at', 'public_metrics']
    )
    
    if not response.data:
        print("No new tweets found.")
        return []
    
    return response.data

def update_markdown(tweets):
    if not tweets:
        return

    # Create file if it doesn't exist
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# My X (Twitter) Archive\n\n")

    # Read existing IDs to avoid duplicates
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        content = f.read()

    with open(FILE_NAME, "a", encoding="utf-8") as f:
        for tweet in reversed(tweets):
            if str(tweet.id) not in content:
                date = tweet.created_at.strftime("%Y-%m-%d %H:%M")
                f.write(f"### {date}\n")
                f.write(f"{tweet.text}\n\n")
                f.write(f"*[Link to tweet](https://x.com/user/status/{tweet.id})*\n")
                f.write("---\n\n")
                print(f"Added tweet {tweet.id}")

if __name__ == "__main__":
    new_tweets = get_tweets()
    update_markdown(new_tweets)
