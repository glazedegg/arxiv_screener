import json
import os
import re
from pathlib import Path
from typing import Iterable, List

import tweepy


TWEET_LIMIT = 280
REQUIRED_KEYS = [
    "BEARER_TOKEN",
    "API_KEY",
    "API_SECRET",
    "ACCESS_TOKEN",
    "ACCESS_TOKEN_SECRET",
]


def authenticate() -> tweepy.Client:
    credentials = _collect_credentials()

    client = tweepy.Client(
        bearer_token=credentials["BEARER_TOKEN"],
        consumer_key=credentials["API_KEY"],
        consumer_secret=credentials["API_SECRET"],
        access_token=credentials["ACCESS_TOKEN"],
        access_token_secret=credentials["ACCESS_TOKEN_SECRET"],
        return_type=tweepy.Response,
    )

    try:
        client.get_me(user_auth=True)
        print("Successfully authenticated with Twitter API.")
    except tweepy.TweepyException as exc:
        print(f"Authentication failed: {exc}")
        raise

    return client


def post(client: tweepy.Client, data, dry_run: bool = True) -> list:
    entries = _normalize_entries(data)
    if not entries:
        print("No data to post.")
        return []

    responses = []
    for entry in entries:
        thread = _build_thread(entry)
        for index, tweet in enumerate(thread):
            prefix = "Tweet" if index == 0 else f"Reply {index}"
            print(f"{prefix}: {tweet}")

        if dry_run:
            continue

        try:
            first = client.create_tweet(text=thread[0], user_auth=True)
            responses.append(first)
            last_id = first.data["id"]

            for tweet in thread[1:]:
                reply = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_id, user_auth=True)
                responses.append(reply)
                last_id = reply.data["id"]
        except tweepy.TweepyException as exc:
            if "duplicate" in str(exc).lower():
                print(f"Skipped duplicate content: {thread[0][:50]}...")
            else:
                print(f"Failed to post thread: {exc}")

    return responses


def _collect_credentials() -> dict:
    values = {key: os.getenv(key) for key in REQUIRED_KEYS}
    missing = [key for key, value in values.items() if not value]

    if not missing:
        return values

    secrets_path = Path(".secrets")
    if secrets_path.exists():
        try:
            lines = [line.strip() for line in secrets_path.read_text().splitlines() if line.strip()]
            if len(lines) < len(REQUIRED_KEYS):
                raise ValueError(
                    "Secrets file must contain 5 lines: Bearer, API Key, API Secret, Access Key, Access Secret."
                )
            return dict(zip(REQUIRED_KEYS, lines))
        except Exception as exc:
            print(f"Error reading secrets: {exc}")
            raise

    message = (
        f"Missing required environment variables: {', '.join(missing)}. "
        "Please set them as environment variables or create a .secrets file."
    )
    print(message)
    raise ValueError(message)


def _normalize_entries(data) -> list[dict]:
    if not isinstance(data, list) or not data:
        return []

    if isinstance(data[0], dict):
        return data

    normalized = []
    for item in data:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, (list, tuple)):
            normalized.append(_kv_pairs_to_dict(item))
        elif isinstance(item, str):
            normalized.append({"summary": item})
        else:
            normalized.append({})
    return normalized


def _kv_pairs_to_dict(pairs: Iterable[str]) -> dict:
    result = {}
    for entry in pairs:
        if not isinstance(entry, str) or ":" not in entry:
            continue
        key, value = entry.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        result[normalized_key] = value.strip()
    return result


def _build_thread(item: dict) -> List[str]:
    tweets: List[str] = []

    title = item.get("title") or item.get("Title") or "Untitled"
    field = item.get("field_&_subfield") or item.get("field")
    first_line = f"{title} — {field}" if field else title
    tweets.append(first_line[:TWEET_LIMIT])

    for key in ("results_summary", "methodology", "one_sentence_summary", "summary"):
        _extend_tweets(tweets, item.get(key))

    for key in ("why_it_matters", "why_it_matters?", "reasoning"):
        if key in item:
            _extend_tweets(tweets, item[key])
            break

    contributions = _extract_contributions(item)
    if contributions:
        _extend_tweets(tweets, "\n".join(contributions))

    link = _build_link(item)
    if link:
        tweets.append(link)

    return tweets


def _extend_tweets(tweets: List[str], text: str | None) -> None:
    if not text:
        return

    for chunk in _split_text(text):
        tweets.append(chunk)


def _split_text(text: str) -> List[str]:
    parts: List[str] = []
    for segment in text.replace("\r", "").split("\n"):
        content = segment.strip()
        if not content:
            continue
        while len(content) > TWEET_LIMIT:
            parts.append(content[:TWEET_LIMIT])
            content = content[TWEET_LIMIT:]
        parts.append(content)
    return parts


def _extract_contributions(item: dict) -> List[str]:
    for key in ("key_contributions", "key_contributions:", "key_contributions_list"):
        raw = item.get(key)
        if raw:
            return _parse_contributions(raw)
    return []


def _parse_contributions(raw: str) -> List[str]:
    text = raw.strip()
    if not text:
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            pass

    lines = [line.strip("-• \t") for line in text.replace("\r", "").split("\n")]
    lines = [line for line in lines if line]

    if lines:
        return lines

    bullets = [segment.strip() for segment in text.split("- ") if segment.strip()]
    return bullets


def _build_link(item: dict) -> str | None:
    link_id = item.get("arxiv_id") or item.get("id") or item.get("entry_id")
    if not link_id:
        return None

    if link_id.startswith("http"):
        url = link_id
    else:
        clean_id = link_id.replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
        clean_id = re.sub(r"v\d+$", "", clean_id)
        url = f"https://arxiv.org/abs/{clean_id}"

    return url.replace("arxiv.org/abs/arxiv.", "arxiv.org/abs/")