import json
import os
import re

# Configuration - Must match sync_tweets.py
INPUT_FILE = 'tweets.js'
OUTPUT_FILE = 'my_tweets.md'
USERNAME = "alvations"
HEADER = "# My Daily X Archive (Latest First)\n\n"

def parse_existing_markdown():
    """Reads the existing .md file so we can merge historical data into it."""
    tweets = []
    if not os.path.exists(OUTPUT_FILE):
        return tweets
    
    print(f"Reading existing {OUTPUT_FILE} for merging...")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    sections = content.split("---\n\n")
    for section in sections:
        try:
            date_match = re.search(r'### (.*?)\n', section)
            # Match the link format used in sync_tweets.py
            link_match = re.search(r'\*\[Link\]\((.*?status/(\d+).*?)\)\*', section)
            
            if date_match and link_match:
                text_start = date_match.end()
                text_end = link_match.start()
                text = section[text_start:text_end].strip()
                
                tweets.append({
                    "id": link_match.group(2),
                    "text": text,
                    "date": date_match.group(1),
                    "link": link_match.group(1)
                })
        except:
            continue
    return tweets

def parse_twitter_js_archive():
    """Parses the tweets.js file from the X/Twitter export."""
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return []

    print("Processing tweets.js archive...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        # Handle the JS variable prefix
        json_str = content[content.find('=') + 1:].strip()
        if json_str.endswith(';'):
            json_str = json_str[:-1]
        
        data = json.loads(json_str)

    archive_tweets = []
    for item in data:
        tweet = item.get('tweet', item) # Handle different archive versions
        tid = tweet.get('id_str')
        archive_tweets.append({
            "id": tid,
            "text": tweet.get('full_text', ''),
            "date": tweet.get('created_at', ''),
            "link": f"https://x.com/{USERNAME}/status/{tid}"
        })
    return archive_tweets

def main():
    # 1. Get historical data from JS file
    archive_data = parse_twitter_js_archive()
    
    # 2. Get existing data from current Markdown file (if any)
    existing_data = parse_existing_markdown()
    
    # 3. Merge and Deduplicate by ID
    # This ensures that if a tweet is in both the archive and the .md file, we only keep one.
    master_dict = {t['id']: t for t in (existing_data + archive_data) if t.get('id')}
    
    # 4. Global Chronological Sort (Latest First)
    # Snowflake IDs are chronological; sorting numerically descending puts newest at top.
    all_sorted = sorted(master_dict.values(), key=lambda x: int(x['id']), reverse=True)
    
    # 5. Write out the formatted file
    print(f"Writing {len(all_sorted)} tweets to {OUTPUT_FILE} in latest-first order...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as md:
        md.write(HEADER)
        for t in all_sorted:
            md.write(f"### {t['date']}\n")
            md.write(f"{t['text']}\n\n")
            md.write(f"*[Link]({t['link']})*\n")
            md.write("---\n\n")

    print("Success! Archive and live posts are now merged and sorted.")

if __name__ == "__main__":
    main()
