import arxiv
from google import genai
from google.genai import types

from datetime import datetime

def search_papers():
    client = arxiv.Client()
    
    today = datetime.utcnow().date()
    search = arxiv.Search(
        query="cat:cs.LG OR cat:cs.AI OR cat:stat.ML OR cat:cs.CV OR cat:cs.NE",
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
        max_results=5 
    )
    
    results = client.results(search)
    todays_papers = []
    
    for result in results:
        #if result.published.date() == today:
        todays_papers.append(result)
        print(f"\rFound {len(todays_papers)} papers published today.", end="")

    if not todays_papers:
        print(f"No machine learning papers found for {today}\n")
    
    return todays_papers

def papers_to_read(papers):
    client = genai.Client()
    for paper in papers:

        response = client.models.generate_content_stream(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction="""
                                    You are an expert AI research assistant. Your goal is to analyze a paper's abstract
                                    based on the user's stated interests and provide a recommendation.

                                    You MUST respond with a valid JSON object containing the following keys and nothing else:
                                    - "title": string
                                    - "id": string
                                    - "should_read": boolean
                                    - "relevance_score": integer (1-10)
                                    - "one_sentence_summary": string
                                    - "reasoning": string
                                    """
            ),
            contents = [f"""
                        {paper.title},
                        {paper.summary},
                        {paper.authors},
                        {paper.primary_category},
                        {paper.entry_id},
                        """
            ]
        )

        for chunk in response:
            print(chunk.text, end="")
            
def main():
    result = search_papers()
    papers_to_read(result)

if __name__ == "__main__":
    main()