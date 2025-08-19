# ArXiv Paper Discovery & Twitter Bot

Automated pipeline that discovers relevant arXiv papers, analyzes them with AI, and posts summaries to Twitter.

## Features

- **Paper Discovery**: Searches arXiv for ML/AI papers based on your research interests
- **AI Analysis**: Uses Gemini to judge relevance and summarize papers
- **X (Twitter) Integration**: Automatically posts paper summaries as threaded tweets
- **Customizable Interests**: Easily modify research focus areas

## Setup

1. Install dependencies:
   ```bash
   uv add tweepy arxiv google-genai
   ```

2. Create `.secrets` file with Twitter API credentials:
   ```
   BEARER_TOKEN
   API_KEY
   API_SECRET
   ACCESS_TOKEN
   ACCESS_TOKEN_SECRET
   ```

3. Set up Google AI API key in environment

## Usage

```bash
uv run main.py
```

**Dry run mode (Debug)** (default): Prints tweet threads without posting
**Live mode**: Set `dry_run=False` in `main.py`

## Configuration

- **Research interests**: Edit `interests` in `arxiv_pipeline.py`
- **Search criteria**: Modify query in `search_papers()`
- **Paper count**: Adjust `max_results` parameter

## Files

- `main.py` - Main pipeline orchestrator
- `arxiv_pipeline.py` - Paper discovery and AI analysis
- `x_tweet_module.py` - Twitter posting functionality