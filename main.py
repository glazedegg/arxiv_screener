import arxiv_pipeline
import x_tweet_module
from google import genai
import os

def main():
    x_auth = x_tweet_module.authenticate()

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set") 
    
    client = genai.Client(api_key=api_key)
    
    result = arxiv_pipeline.search_papers(client)
    if not result: return

    summaries = arxiv_pipeline.summarize_reading_list(result, client)

    reading_list = arxiv_pipeline.judge_papers([r for r in result], client)
    parsed_summaries = arxiv_pipeline.parse_summary(summaries, reading_list)
    x_tweet_module.post(x_auth, parsed_summaries, dry_run=False)
    
    arxiv_pipeline.remove_downloaded_papers()

if __name__ == "__main__":
    main()
