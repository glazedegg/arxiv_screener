import json
import re
import os
from datetime import datetime, timedelta

import arxiv
from google.genai import types

def search_papers(client) -> list:
    arxiv_client = arxiv.Client()

    yesterday = datetime.now().date() - timedelta(days=1)
    search = arxiv.Search(
        query="cat:cs.LG OR cat:cs.AI OR cat:stat.ML OR cat:cs.CV OR cat:cs.NE",
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
        max_results=15
    )

    results = arxiv_client.results(search)
    yesterdays_papers = []

    for result in results:
        if result.published.date() == yesterday:
            yesterdays_papers.append(result)
    print(f"Found {len(yesterdays_papers)} papers published yesterday.\n")

    if not yesterdays_papers:
        print("No machine learning papers found for yesterday\n")

    reading_list = judge_papers(yesterdays_papers, client)

    downloaded_papers = []
    
    for paper in reading_list:
        url = f"{paper['id']}"
        match = re.search(r'(?:arxiv\.org/abs/)?(\d{4}\.\d{5}v\d+|arxiv\.\d{4}\.\d{5}v\d+)', url)
        if match:
            arxiv_id = match.group(1)
            if arxiv_id.startswith("arxiv."):
                arxiv_id = arxiv_id[len("arxiv."):]
        else:
            print(f"Invalid arXiv ID or URL format: {url}")
            continue

        pdf_paper = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))
        pdf_paper.download_pdf(dirpath="./papers", filename=f"{pdf_paper.title}.pdf")

        if pdf_paper:
            downloaded_papers.append(pdf_paper)
            print(f"\rDownloaded: {len(downloaded_papers)} papers", end="")
        else: 
            print(f"Failed to download: {pdf_paper.title}")

    return downloaded_papers

def judge_papers(papers, client, read_list=None) -> list | None:
    if read_list is None:
        read_list = []

    interests = """
                - Strong Interests:
                    - Self-evolving agents and adaptive AI systems (e.g., continual learning, agent evolution, memory/tool adaptation)
                    - Generative models for time-series data
                    - Multimodal learning and video understanding
                    - Computer vision applications (especially in temporal, agentic, or multimodal contexts)
                    - Few-shot and meta-learning
                    - Representation learning for multi-task systems (e.g., task saliency, cross-task transfer)
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
                    - Static LLM alignment/prompt engineering unless tied to continual learning or real-time adaptation
                    - Reinforcement learning (RL) in static settings, unless it involves continual learning or adaptive agents
                    - Offline and local models


                - General:
                    - Broadly interested in computer science, with curiosity spanning learning theory, agent design, systems, and real-world AI deployment — especially in domains involving perception, interaction, or simulation.

                - Avoids / Not currently focused on:
                    - Classic standalone image classification tasks
                    - Domain-specific biomedical ML unless it links to adaptive agents or generative/causal modeling
                """

    for paper in papers:

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=f"""
                                    You are an expert AI research assistant with deep knowledge of the machine learning landscape. Your goal is to analyze a paper's abstract based on the user's stated research interests and provide a concise, structured recommendation.

                                    The user's interests will be provided, ranked by priority. Your analysis MUST be strictly guided by these interests: {interests}. When rating papers, because there is a lot of papers published every day, you MUST be very selective.

                                    You MUST respond with a valid JSON object. Do not include any text, notes, or explanations outside of the JSON structure. You MUST respond with a valid JSON object containing the following keys and nothing else:
                                    - "title": string
                                    - "id": string
                                    - "should_read": A boolean value (true if you strongly recommend reading it based on the user's high-priority interests, otherwise false).
                                    - "relevance_score": An integer from 1 to 10, where 10 is a perfect match for the user's high-priority interests. A score below 6 indicates it is not relevant.
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

            print("-" * 50)
            if paper_analysis.get('should_read', False):
                read_list.append(paper_analysis)
                print(f"{paper_analysis['title']}, {paper_analysis['id']}")
                print(f"Score: {paper_analysis['relevance_score']}/10")
                print(f"Summary: {paper_analysis['one_sentence_summary']}")
            else:
                print(f"Skipped: {paper_analysis['title']}")
                print(f"Reasoning: {paper_analysis['reasoning']}")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"\n⚠ Error parsing response for paper: {paper.title}")
            print(f"Error: {e}")
            print(f"Raw response: {response.text[:200]}...")
            continue
    print("-" * 50)
    
    return read_list

def summarize_reading_list(read_list, client) -> list:
    system_prompt = """
            You are an expert research analyst. You will be given a full research paper as a PDF.
            Your task is to extract as much valuable information as possible and provide a comprehensive but concise summary formatted as a JSON object.

            The purpose is to absorb the paper's core contributions and insights efficiently. The user may decide to read the full paper if it appears especially interesting or foundational.

            Analyze the entire document and extract the following structured fields:

            1. **Title**: The full title of the paper.
            2. **Field & Subfield**: E.g., "Machine Learning > Computer Vision" or "Physics > Quantum Computing".
            3. **Key Contributions**: A bulleted list (in a single string) of the 2-4 most important contributions.
            4. **Methodology**: A concise paragraph explaining the core method, technique, or approach.
            5. **Strengths**: Bulleted list of the main strengths (e.g., novel algorithm, strong theoretical guarantee, state-of-the-art performance).
            6. **Limitations**: Bulleted list of potential limitations or open questions.
            7. **Datasets / Benchmarks**: Mention any datasets used or introduced, and benchmarks compared against.
            8. **Results Summary**: A short paragraph on key quantitative or qualitative results.
            9. **Why It Matters**: A short paragraph on why this work is important, novel, or useful in practice.
            10. **Should Read Fully?**: "Yes" or "No" depending on how fundamental, novel, or surprising the paper is.
            11. **Key Figures or Tables** (optional): If any figure/table seems essential, mention its purpose briefly.

            Output the entire summary as a JSON object.
            Be precise, clear, and helpful.
            """

    summary = []
    papers_dir = "./papers"
    if os.path.exists(papers_dir):
        for filename in os.listdir(papers_dir):
            if not filename.endswith(".pdf"):
                continue
            file_path = os.path.join(papers_dir, filename)
            paper_pdf = client.files.upload(file=file_path)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=f"{system_prompt}"
                ),
                contents= ["Please analyze this research paper PDF and provide a comprehensive summary following the JSON format specified in the system instructions:", paper_pdf]
            )
            summary.append(response.text)
            print(response.text)

    return summary

def remove_downloaded_papers() -> None:
    papers_dir = "./papers"
    if os.path.exists(papers_dir):
        for filename in os.listdir(papers_dir):
            file_path = os.path.join(papers_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
            except Exception as e:
                print(f"Error removing {file_path}: {e}")