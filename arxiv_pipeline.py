import json
import re
import difflib
from datetime import datetime, timedelta
from pathlib import Path

import arxiv
from google.genai import types


SEARCH_QUERY = "cat:cs.LG OR cat:cs.AI OR cat:stat.ML OR cat:cs.CV OR cat:cs.NE"
MAX_RESULTS = 3
PAPERS_DIR = Path("papers")
LOG_PATH = Path("log.json")

INTERESTS_PROMPT = """
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
    - Classic standalone image classification tasks
    - Domain-specific biomedical ML

- General:
    - Broadly interested in computer science, with curiosity spanning learning theory, agent design, systems, and real-world AI deployment — especially in domains involving perception, interaction, or simulation.

- Avoids / Not currently focused on:
"""

def search_papers(client) -> list:
    papers = _fetch_yesterdays_papers()
    if not papers:
        print("No machine learning papers found for yesterday\n")
        return []

    reading_list = judge_papers(papers, client)
    if not reading_list:
        return []

    PAPERS_DIR.mkdir(exist_ok=True)

    downloaded: list[arxiv.Result] = []
    for entry in reading_list:
        arxiv_id = _extract_arxiv_id(entry.get("id", ""))
        if not arxiv_id:
            print(f"Invalid arXiv ID or URL format: {entry.get('id', '')}")
            continue

        pdf = _download_pdf(arxiv_id)
        if not pdf:
            continue

        pdf.download_pdf(dirpath=str(PAPERS_DIR), filename=f"{pdf.title}.pdf")
        downloaded.append(pdf)
        print(f"\rDownloaded: {len(downloaded)} papers", end="")

    if downloaded:
        print()
    return downloaded

def judge_papers(papers, client, read_list=None) -> list | None:
    selections = [] if read_list is None else read_list

    for paper in papers:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are an expert AI research assistant with deep knowledge of the machine learning landscape. "
                    "Your goal is to analyze a paper's abstract based on the user's stated research interests and provide "
                    "a concise, structured recommendation.\n\n"
                    "The user's interests will be provided, ranked by priority. Your analysis MUST be strictly guided by "
                    f"these interests: {INTERESTS_PROMPT}. When rating papers, be extremely selective.\n\n"
                    "OUTPUT REQUIREMENTS (must follow exactly):\n"
                    "- Output EXACTLY ONE JSON object (not an array, not multiple objects).\n"
                    "- NO markdown, NO code fences, NO surrounding text.\n"
                    "- Keys (all required, none extra):\n"
                    '  - "title": string\n'
                    '  - "id": string\n'
                    '  - "should_read": boolean\n'
                    '  - "relevance_score": integer 1-10\n'
                    '  - "one_sentence_summary": string\n'
                    '  - "reasoning": string\n'
                    '  - "keywords": array of strings\n'
                )
            ),
            contents=[
                (
                    f"{paper.title},\n"
                    f"{paper.entry_id},\n"
                    f"{paper.summary},\n"
                    f"{paper.authors},\n"
                    f"{paper.primary_category},"
                )
            ],
        )

        analysis = _parse_model_response(response.text, paper.title)
        if not analysis:
            continue

        print("-" * 50)
        if analysis.get("should_read"):
            selections.append(analysis)
            print(f"{analysis['title']}, {analysis['id']}")
            print(f"Score: {analysis['relevance_score']}/10")
            print(f"Summary: {analysis['one_sentence_summary']}")
        else:
            print(f"Skipped: {analysis.get('title', paper.title)}")
            print(f"Reasoning: {analysis.get('reasoning', 'No reasoning provided.')}")

    print("-" * 50)
    if not selections:
        return None

    return sorted(selections, key=lambda item: item.get("relevance_score", 0), reverse=True)

def summarize_reading_list(read_list, client) -> list:
    system_prompt = """
You are an expert research analyst. You will be given a full research paper as a PDF. Your task is to extract as much valuable information as possible and provide a comprehensive but concise summary formatted as a JSON object. Each field must be at most 280 characters.

Required fields:
1. Title
2. Field & Subfield
3. Key Contributions (single string with bullet-style entries)
4. Methodology
5. Strengths
6. Limitations
7. Datasets / Benchmarks
8. Results Summary
9. Why It Matters
10. Should Read Fully? (Yes/No)
11. Key Figures or Tables (optional)
"""

    summaries = []
    if not PAPERS_DIR.exists():
        return summaries

    for pdf_path in sorted(PAPERS_DIR.iterdir()):
        if pdf_path.suffix.lower() != ".pdf":
            continue

        uploaded = client.files.upload(file=str(pdf_path))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=[
                "Please analyze this research paper PDF and provide a comprehensive summary following the JSON format specified in the system instructions:",
                uploaded,
            ],
        )
        summaries.append(response.text)
        print(response.text)

    return summaries

def parse_summary(summary, reading_list) -> list:
    parsed = []
    log_entries = _load_log_entries()
    reading_lookup = _build_reading_lookup(reading_list)
    updated = False

    for item in summary:
        document = _coerce_json_document(item)
        if document is None:
            continue

        matched_id = _match_reading_entry(document, reading_lookup)
        if matched_id:
            document["arxiv_id"] = matched_id

        log_entries.append(document)
        updated = True

        kv_list = []
        for key, value in document.items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            kv_list.append(f"{key}: {value_str}")
        parsed.append(kv_list)

        if updated:
            _write_log_entries(log_entries)
    return parsed

def remove_downloaded_papers() -> None:
    if not PAPERS_DIR.exists():
        return

    for path in PAPERS_DIR.iterdir():
        if path.is_file():
            try:
                path.unlink()
                print(f"Removed: {path}")
            except OSError as exc:
                print(f"Error removing {path}: {exc}")


def _fetch_yesterdays_papers() -> list[arxiv.Result]:
    client = arxiv.Client()
    search = arxiv.Search(
        query=SEARCH_QUERY,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
        max_results=MAX_RESULTS,
    )

    yesterday = datetime.now().date() - timedelta(days=1)
    results = [result for result in client.results(search) if result.published.date() == yesterday]
    print(f"Found {len(results)} papers published yesterday.\n")
    return results


def _extract_arxiv_id(url: str) -> str | None:
    match = re.search(r"(?:arxiv\.org/abs/)?(\d{4}\.\d{5}v\d+|arxiv\.\d{4}\.\d{5}v\d+)", url)
    if not match:
        return None

    arxiv_id = match.group(1)
    if arxiv_id.startswith("arxiv."):
        return arxiv_id[len("arxiv."):]
    return arxiv_id


def _download_pdf(arxiv_id: str) -> arxiv.Result | None:
    try:
        return next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))
    except StopIteration:
        print(f"Failed to download paper with id {arxiv_id}")
        return None


def _parse_model_response(raw_text: str, title: str) -> dict | None:
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        payload = json_match.group(1) if json_match else raw_text.strip()
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"\n⚠ Error parsing response for paper: {title}")
        print(f"Error: {exc}")
        print(f"Raw response: {raw_text[:200]}...")
        return None


def _load_log_entries() -> list:
    if not LOG_PATH.exists():
        return []

    try:
        content = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        if isinstance(content, list):
            return content
        return [content]
    except (json.JSONDecodeError, OSError):
        return []


def _write_log_entries(entries: list) -> None:
    LOG_PATH.write_text(json.dumps(entries, indent=4, ensure_ascii=False), encoding="utf-8")


def _build_reading_lookup(reading_list) -> dict[str, dict]:
    lookup = {}
    if not reading_list:
        return lookup

    for item in reading_list:
        title_value = item.get("title") or item.get("Title")
        normalized = _normalize_title(title_value)
        if normalized:
            lookup[normalized] = item
    return lookup


def _match_reading_entry(document: dict, lookup: dict[str, dict]) -> str | None:
    if not lookup:
        return None

    title_candidate = document.get("Title") or document.get("title")
    normalized = _normalize_title(title_candidate)
    if not normalized:
        return None

    if normalized in lookup:
        matched = lookup.pop(normalized)
        return matched.get("id")

    close_match = difflib.get_close_matches(normalized, list(lookup.keys()), n=1, cutoff=0.8)
    if close_match:
        matched = lookup.pop(close_match[0])
        return matched.get("id")

    return None


def _normalize_title(value: str | None) -> str:
    return re.sub(r"\W+", "", value).lower() if value else ""


def _coerce_json_document(raw: str) -> dict | None:
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        payload = json_match.group(1) if json_match else raw.strip()
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        print(f"Error parsing summary: {exc}")
        return None
