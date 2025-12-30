import tweepy
import os
import datetime
import sys

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
    
    try:
        # max_results: 5-100. Let's use 20 to ensure we catch everything.
        # tweet_fields: includes 'referenced_tweets' to detect reposts/replies
        response = client.get_users_tweets(
            id=USER_ID, 
            max_results=20, 
            tweet_fields=['created_at', 'referenced_tweets', 'conversation_id'],
            expansions=['referenced_tweets.id']
        )
        
        if not response.data:
            print("No tweets, reposts, or replies found in the last 7 days.")
            return []
        
        return response.data

    except tweepy.errors.Forbidden as e:
        print(f"❌ Error 403: Forbidden. Your X API tier (Free) does not allow reading tweets.")
        print("Note: The Free tier only allows POSTING. You need the Basic tier ($100/mo) to backup posts.")
        sys.exit(1) 

    except tweepy.errors.TooManyRequests:
        print("❌ Error 429: Rate limit hit.")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)

def update_markdown(tweets):
    if not tweets:
        return

    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("# My X (Twitter) Archive\n\n")

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        content = f.read()

    new_entries = []
    
    # Process tweets in reverse (oldest to newest) to maintain chronological order
    for tweet in reversed(tweets):
        if str(tweet.id) not in content:
            date = tweet.created_at.strftime("%Y-%m-%d %H:%M")
            
            # Identify the type of tweet
            prefix = "📝 **Post**" # Default
            if tweet.referenced_tweets:
                ref_type = tweet.referenced_tweets[0].type
                if ref_type == "retweeted":
                    prefix = "🔁 **Repost**"
                elif ref_type == "replied_to":
                    prefix = "💬 **Reply**"
                elif ref_type == "quoted":
                    prefix = "👁️ **Quote Tweet**"

            entry = f"### {date}\n{prefix}\n\n{tweet.text}\n\n"
            entry += f"*[Link to tweet](https://x.com/i/status/{tweet.id})*\n\n---\n\n"
            new_entries.append(entry)
            print(f"Adding {prefix} {tweet.id}")

    if new_entries:
        with open(FILE_NAME, "a", encoding="utf-8") as f:
            f.write("".join(new_entries))
    else:
        print("No new unique content to add.")

if __name__ == "__main__":
    new_tweets = get_tweets()
    update_markdown(new_tweets)
