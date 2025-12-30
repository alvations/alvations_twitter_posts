import json
import os

# Configuration
INPUT_FILE = 'tweets.js'
OUTPUT_FILE = 'my_tweets.md'

def parse_archive():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Place this script in the 'data' folder of your archive.")
        return

    print("Reading archive... this may take a moment.")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        # Remove the JavaScript variable assignment at the start of the file
        content = f.read()
        json_str = content.replace('window.YTD.tweet.part0 = ', '')
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Some newer archives might have different variable names
            print("Standard parsing failed, attempting alternate cleaning...")
            json_str = content[content.find('=') + 1:].strip()
            data = json.loads(json_str)

    # Sort tweets by date (oldest to newest or newest to oldest)
    # The archive usually comes in reverse chronological order
    tweets = [t['tweet'] for t in data]
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as md:
        md.write("# My X (Twitter) Archive\n\n")
        
        for tweet in tweets:
            text = tweet.get('full_text', '')
            date = tweet.get('created_at', '')
            tweet_id = tweet.get('id_str', '')
            
            # Format the output to match your daily_sync.py format
            md.write(f"### {date}\n")
            md.write(f"{text}\n\n")
            md.write(f"*[Link to tweet](https://x.com/i/status/{tweet_id})*\n")
            md.write("---\n\n")

    print(f"Success! {len(tweets)} tweets saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    parse_archive()
