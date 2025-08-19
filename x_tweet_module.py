import tweepy
import re

def authenticate() -> tweepy.Client:
    try:
        with open(".secrets", "r") as f:
            secrets = f.read().strip().split("\n")
            if len(secrets) < 5:
                raise ValueError("Secrets file must contain 5 lines: Bearer, API Key, API Secret, Access Key, Access Secret.")
            bearer_token = secrets[0].strip()
            consumer_key = secrets[1].strip()
            consumer_secret = secrets[2].strip()
            access_token = secrets[3].strip()
            access_token_secret = secrets[4].strip()

    except FileNotFoundError:
        print("Secrets file not found. Add to a .secrets file with API credentials.")
        raise
    except Exception as e:
        print(f"Error reading secrets: {e}")
        raise

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        return_type=tweepy.Response
    )

    try:
        client.get_me(user_auth=True)
        print("Successfully authenticated with Twitter API.")
    except tweepy.TweepyException as e:
        print(f"Authentication failed: {e}")
        raise

    return client

def post(client: tweepy.Client, data, dry_run: bool = True) -> list:
    def kv_list_to_dict(kv_list):
        d = {}
        for item in kv_list:
            if not isinstance(item, str):
                continue
            parts = item.split(":", 1)
            if len(parts) == 2:
                k = parts[0].strip().lower().replace(" ", "_")
                v = parts[1].strip()
                d[k] = v
        return d

    def build_thread(item_dict):
        title = item_dict.get("title") or item_dict.get("Title") or "Untitled"
        field = item_dict.get("field_&_subfield") or item_dict.get("field") or ""
        
        results = (item_dict.get("results_summary") or 
                  item_dict.get("methodology") or 
                  item_dict.get("one_sentence_summary") or 
                  item_dict.get("summary") or "")
        
        why = (item_dict.get("why_it_matters") or 
               item_dict.get("why_it_matters?") or 
               item_dict.get("reasoning") or "")
        
        contributions = (item_dict.get("key_contributions") or 
                        item_dict.get("key_contributions:") or 
                        item_dict.get("key_contributions_list") or "")
        
        link_id = (item_dict.get("arxiv_id") or 
                  item_dict.get("id") or 
                  item_dict.get("entry_id") or "")
        
        link = ""
        if link_id:
            print(f"Debug: Found link_id: {link_id}")
            if link_id.startswith("http"):
                link = link_id
            else:
                clean_id = link_id.replace("http://arxiv.org/abs/", "")
                clean_id = re.sub(r'v\d+$', '', clean_id)
                link = f"https://arxiv.org/abs/{clean_id}"
            print(f"Debug: Generated link: {link}")
        
        tweets = []
        
        first = title
        if field:
            first = f"{title} — {field}"
        tweets.append(first[:280])

        if results:
            tweets.append(results[:280])
        
        if why:
            tweets.append(why[:280])
        
        if contributions:
            # Clean up contributions formatting - handle JSON array format
            contrib_text = contributions
            
            # Remove JSON array formatting if present
            if contrib_text.startswith('["') and contrib_text.endswith('"]'):
                try:
                    import json
                    contrib_list = json.loads(contrib_text)
                    contrib_text = "\n".join([f"{item}" for item in contrib_list])
                except json.JSONDecodeError:
                    contrib_text = contrib_text.strip('[""]').replace('", "', '"\n"').replace('"', '')
                    contrib_text = "\n".join([f"{line.strip()}" for line in contrib_text.split('\n') if line.strip()])
            elif contrib_text.startswith('[') and contrib_text.endswith(']'):
                contrib_text = contrib_text.strip('[]').replace('", "', '\n').replace('"', '')
                contrib_text = "\n".join([f"{line.strip()}" for line in contrib_text.split('\n') if line.strip()])
            
            parts = []
            if "" in contrib_text:
                bullet_lines = [line.strip() for line in contrib_text.split('\n') if line.strip()]
                
                current_tweet = ""
                for bullet in bullet_lines:
                    if len(current_tweet + "\n" + bullet) > 270:
                        if current_tweet:
                            parts.append(current_tweet.strip())
                        current_tweet = bullet
                    else:
                        if current_tweet:
                            current_tweet += "\n" + bullet
                        else:
                            current_tweet = bullet
                
                if current_tweet:
                    parts.append(current_tweet.strip())

            elif "- " in contrib_text:
                bullet_parts = contrib_text.split("- ")
                clean_bullets = []
                for part in bullet_parts[1:]:
                    clean_part = part.strip().rstrip(".,")
                    if clean_part:
                        clean_bullets.append(f"{clean_part}")
                
                current_tweet = ""
                for bullet in clean_bullets:
                    if len(current_tweet + "\n" + bullet) > 270:
                        if current_tweet:
                            parts.append(current_tweet.strip())
                        current_tweet = bullet
                    else:
                        if current_tweet:
                            current_tweet += "\n" + bullet
                        else:
                            current_tweet = bullet
                
                if current_tweet:
                    parts.append(current_tweet.strip())
                    
            else:
                if len(contrib_text) > 280:
                    sentences = contrib_text.split(". ")
                    current_part = ""
                    for sentence in sentences:
                        if len(current_part + sentence) > 260:
                            if current_part:
                                parts.append(current_part.strip())
                                current_part = sentence
                            else:
                                parts.append(sentence[:280])
                        else:
                            current_part += sentence + ". " if not sentence.endswith(".") else sentence + " "
                    if current_part.strip():
                        parts.append(current_part.strip())
                else:
                    parts.append(contrib_text)
            
            for p in parts:
                if p and len(p.strip()) > 0:
                    tweets.append(p[:280])
        
        if link and "arxiv.org/abs/" in link:
            clean_link = link.replace("arxiv.org/abs/arxiv.", "arxiv.org/abs/")
            print(f"Debug: Adding link to thread: {clean_link}")
            tweets.append(clean_link)
        else:
            print(f"Debug: No valid link found (link: {link})")
        
        return tweets

    entries = []
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            entries = data
        else:
            for d in data:
                if isinstance(d, (list, tuple)):
                    entries.append(kv_list_to_dict(d))
                elif isinstance(d, str):
                    entries.append({"summary": d})
                else:
                    entries.append({})
    else:
        print("No data to post.")
        return []

    responses = []
    for item in entries:
        thread = build_thread(item)
        for i, t in enumerate(thread):
            prefix = "Tweet" if i == 0 else f"Reply {i}"
            print(f"{prefix}: {t}")

        if not dry_run:
            try:
                # Post chain: create first tweet, then reply to it for the rest
                resp = client.create_tweet(text=thread[0], user_auth=True)
                responses.append(resp)
                print(f"Posted tweet: {resp.data['id']}")
                last_id = resp.data["id"]
                for j, t in enumerate(thread[1:], 1):
                    resp = client.create_tweet(text=t, in_reply_to_tweet_id=last_id, user_auth=True)
                    responses.append(resp)
                    print(f"Posted reply {j}: {resp.data['id']}")
                    last_id = resp.data["id"]
            except tweepy.TweepyException as e:
                if "duplicate" in str(e).lower():
                    print(f"Skipped duplicate content: {thread[0][:50]}...")
                else:
                    print(f"Failed to post thread: {e}")
                continue

    return responses