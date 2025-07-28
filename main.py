import arxiv
from datetime import datetime

def main():
    client = arxiv.Client()
    
    today = datetime.utcnow().date()
    search = arxiv.Search(
        query="cat:cs.LG OR cat:cs.AI OR cat:stat.ML",
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
        max_results=100 
    )
    
    results = client.results(search)
    todays_papers = []
    
    for result in results:
        if result.published.date() == today:
            todays_papers.append(result)
            
    if not todays_papers:
        print(f"No machine learning papers found for {today}")

if __name__ == "__main__":
    main()