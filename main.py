import arxiv_pipeline
import x_tweet_module
from google import genai

def main():
    x_auth = x_tweet_module.authenticate()

    client = genai.Client()
    result = arxiv_pipeline.search_papers(client)

    summaries = arxiv_pipeline.summarize_reading_list(result, client)
    parsed_summaries = arxiv_pipeline.parse_summary(summaries)
    
    # parsed_summaries = [["Test", "This is a test summary."], ["Test 2", "This is another test summary."]]
    # x_tweet_module.post(x_auth, parsed_summaries)

    arxiv_pipeline.remove_downloaded_papers()

if __name__ == "__main__":
    main()