import arxiv
from google import genai
from google.genai import types
import json
import re

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
    print(f"Found {len(todays_papers)} papers published today.\n")

    if not todays_papers:
        print(f"No machine learning papers found for {today}\n")
    
    return todays_papers

def judge_papers(papers, client, read_list=None) -> list | None:
    if read_list is None:
        read_list = []

    interests = """
                - Strong Interests:
                    - Generative models for time-series data
                    - Computer vision applications (especially when combined with temporal, multimodal, or interactive environments)
                    - Multimodal learning and video understanding
                    - AI agents interacting with graphical or real-world environments (e.g., GUI agents, task automation, visual grounding)
                    - Few-shot and meta-learning
                    - Bayesian methods and probabilistic modeling
                    - Applications of ML in finance, especially time-dependent or causal settings
                    - Text-to-speech (TTS) and generative audio systems

                - Moderate Interests:
                    - Efficient Transformer architectures
                    - Causal inference and interpretability
                    - Neuro-symbolic reasoning
                    - Physics-informed neural networks (PINNs)
                    - Sim-to-real transfer and visual navigation in robotics
                    - Neural architecture search (NAS)

                - General:
                    - Deeply interested in computer science, with broad curiosity in theory, systems, and practical ML applications across domains such as finance, simulation, and perception.

                - Avoids / Not currently focused on:
                    - Pure reinforcement learning or RLHF unless paired with real-world grounding or interpretability
                    - LLM alignment and prompt engineering without deeper algorithmic or interactive innovation
                    - Static image classification tasks with no temporal or agent-based context
                    - Narrow biomedical ML unless tied to causal reasoning or generative modeling
                """

    for paper in papers:

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=f"""
                                    You are an expert AI research assistant with deep knowledge of the machine learning landscape. Your goal is to analyze a paper's abstract based on the user's stated research interests and provide a concise, structured recommendation.

                                    The user's interests will be provided, ranked by priority. Your analysis MUST be strictly guided by these interests: {interests}.

                                    You MUST respond with a valid JSON object. Do not include any text, notes, or explanations outside of the JSON structure. You MUST respond with a valid JSON object containing the following keys and nothing else:
                                    - "title": string
                                    - "id": string
                                    - "should_read": A boolean value (true if you strongly recommend reading it based on the user's high-priority interests, otherwise false).
                                    - "relevance_score": An integer from 1 to 10, where 10 is a perfect match for the user's high-priority interests. A score below 5 indicates it is not relevant.
                                    - "one_sentence_summary": A single, non-technical sentence summarizing the paper's core contribution.
                                    - "reasoning": A brief, objective explanation for your recommendation and score, directly referencing keywords from the user's interests and the paper's abstract.
                                    - "keywords": An array of 3-5 strings, listing the most important technical terms from the abstract (e.g., "Variational Inference", "Mixture of Experts", "Direct Preference Optimization").
                                    """
            ),
            contents = [f"""
                        {paper.title},
                        {paper.entry_id},
                        {paper.summary},
                        {paper.authors},
                        {paper.primary_category},
                        """
            ]
        )

        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.text, re.DOTALL)
            if json_match:
                stripped_json = json_match.group(1)
            else:
                stripped_json = response.text.strip()

            paper_analysis = json.loads(stripped_json)

            print(f"-" * 50)
            if paper_analysis.get('should_read', False):
                read_list.append(paper_analysis)
                print(f"{paper_analysis['title']}")
                print(f"Score: {paper_analysis['relevance_score']}/10")
                print(f"Summary: {paper_analysis['one_sentence_summary']}")
            else:
                print(f"Skipped: {paper_analysis['title']}")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"\n⚠ Error parsing response for paper: {paper.title}")
            print(f"Error: {e}")
            print(f"Raw response: {response.text[:200]}...")
            continue
    print(f"-" * 50)
    return read_list

def main():
    result = search_papers()

    client = genai.Client()

    read_list = judge_papers(result, client)

if __name__ == "__main__":
    main()