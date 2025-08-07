import tweepy

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
    except tweepy.TweepyException as e:
        print(f"Authentication failed: {e}")
        raise

    print("Authentication successful.")

    return client

def post(client: tweepy.Client, text: str):
    try:
        resp = client.create_tweet(text=text, user_auth=True)
        print("Tweeted with id:", resp.data["id"])
        return resp
    except tweepy.TweepyException as e:
        print(f"Failed to post: {e}")
        raise