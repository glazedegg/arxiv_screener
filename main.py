import arxiv_pipeline
from google import genai

def main():
    client = genai.Client()
    result = arxiv_pipeline.search_papers(client)

    summaries = arxiv_pipeline.summarize_reading_list(result, client)

    arxiv_pipeline.remove_downloaded_papers()

if __name__ == "__main__":
    main()