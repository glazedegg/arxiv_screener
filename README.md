# ArXiv Twitter Pipeline

Pipeline that finds yesterday’s arXiv ML papers, ranks them with Gemini, saves the summaries, and posts a thread to X.

## Quick Start
*Personal use*
```bash
uv sync
export GEMINI_API_KEY=your_key
uv run main.py
```

Provide X credentials via environment variables or a `.secrets` file with:

```
BEARER_TOKEN
API_KEY
API_SECRET
ACCESS_TOKEN
ACCESS_TOKEN_SECRET
```

## Customize

- Interests & ranking prompt: `arxiv_pipeline.py` (`INTERESTS_PROMPT`)
- Search scope / paper count: `_fetch_yesterdays_papers`
- Tweet formatting: `x_tweet_module.py`

## Tests

```bash
uv run pytest tests
```

## Automation

GitHub Actions (`.github/workflows/main.yml`) runs the pipeline nightly, commits the updated `log.json`, and tweets (unless you leave `dry_run=True`). Make sure repository actions have read/write permissions and the secrets listed above are set.