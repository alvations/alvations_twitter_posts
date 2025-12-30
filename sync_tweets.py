import tweepy
import os
import datetime
import sys

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

def get_tweets():
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    
    try:
        # 1. Automatically resolve username to ID
        user = client.get_user(username=USERNAME)
        user_id = user.data.id
        print(f"✅ Verified User: {USERNAME} (ID: {user_id})")

        # 2. Fetch recent content (last 7 days)
        # Note: 'referenced_tweets' is required to see reposts and replies
        response = client.get_users_tweets(
            id=user_id, 
            max_results=20, 
            tweet_fields=['created_at', 'referenced_tweets', 'text'],
            expansions=['referenced_tweets.id']
        )
        
        if not response.data:
            print("⚠️ The API returned 0 tweets. Note: V2 API only looks back at the last 7 days.")
            return []
        
        return response.data

    except tweepy.errors.Forbidden:
        print("❌ Error 403: Forbidden. Your API tier (Free) does not allow reading tweets.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def update_markdown(tweets):
    if not tweets: return
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# My X Archive\n\n")

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        content = f.read()

    new_entries = []
    for tweet in reversed(tweets):
        if str(tweet.id) not in content:
            date = tweet.created_at.strftime("%Y-%m-%d %H:%M")
            
            # Label the type of interaction
            prefix = "📝 **Post**"
            if tweet.referenced_tweets:
                rtype = tweet.referenced_tweets[0].type
                if rtype == "retweeted": prefix = "🔁 **Repost**"
                elif rtype == "replied_to": prefix = "💬 **Reply**"
                elif rtype == "quoted": prefix = "👁️ **Quote**"

            entry = f"### {date}\n{prefix}\n\n{tweet.text}\n\n"
            entry += f"*[Link](https://x.com/i/status/{tweet.id})*\n\n---\n\n"
            new_entries.append(entry)
            print(f"Added {prefix} {tweet.id}")

    if new_entries:
        with open(FILE_NAME, "a", encoding="utf-8") as f:
            f.write("".join(new_entries))

if __name__ == "__main__":
    tweets = get_tweets()
    update_markdown(tweets)
