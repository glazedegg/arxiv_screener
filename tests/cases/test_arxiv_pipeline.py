import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import arxiv_pipeline


class DummyPaper:
    def __init__(self, title: str, entry_id: str):
        self.title = title
        self.entry_id = entry_id
        self.summary = "Abstract"
        self.authors = ["Author"]
        self.primary_category = "cs.AI"


class StubModels:
    def __init__(self, responses):
        self._responses = iter(responses)

    def generate_content(self, *args, **kwargs):
        try:
            text = next(self._responses)
        except StopIteration as exc:  # pragma: no cover - defensive guard
            raise AssertionError("Unexpected generate_content call") from exc
        return SimpleNamespace(text=text)


class StubFiles:
    def __init__(self, captures):
        self._captures = captures

    def upload(self, file):
        self._captures.append(Path(file))
        return f"uploaded::{Path(file).name}"


class StubClient:
    def __init__(self, *, responses=None, upload_captures=None):
        if responses is None:
            responses = []
        if upload_captures is None:
            upload_captures = []
        self.models = StubModels(responses)
        self.files = StubFiles(upload_captures)


def _kv_list_to_dict(kv_list):
    result = {}
    for item in kv_list:
        if not isinstance(item, str) or ":" not in item:
            continue
        key, value = item.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def test_judge_papers_prioritises_high_scores(capsys):
    responses = [
        json.dumps(
            {
                "title": "Paper Low",
                "id": "http://arxiv.org/abs/0001.00001v1",
                "should_read": False,
                "relevance_score": 5,
                "one_sentence_summary": "",
                "reasoning": "Not aligned",
                "keywords": ["a", "b", "c"],
            }
        ),
        """```json
{"title": "Paper High", "id": "http://arxiv.org/abs/0002.00002v1", "should_read": true, "relevance_score": 9, "one_sentence_summary": "Great", "reasoning": "Matches interests", "keywords": ["x", "y", "z"]}
```""",
    ]

    client = StubClient(responses=responses)
    papers = [DummyPaper("Paper Low", "id-low"), DummyPaper("Paper High", "id-high")]

    reading_list = arxiv_pipeline.judge_papers(papers, client)

    captured = capsys.readouterr()
    assert "Skipped: Paper Low" in captured.out
    assert reading_list == [
        {
            "title": "Paper High",
            "id": "http://arxiv.org/abs/0002.00002v1",
            "should_read": True,
            "relevance_score": 9,
            "one_sentence_summary": "Great",
            "reasoning": "Matches interests",
            "keywords": ["x", "y", "z"],
        }
    ]


def test_judge_papers_handles_invalid_response(capsys):
    client = StubClient(responses=["not-json"])
    papers = [DummyPaper("Paper", "id")]

    result = arxiv_pipeline.judge_papers(papers, client)

    captured = capsys.readouterr()
    assert result is None
    assert "Error parsing response" in captured.out


def test_summarize_reading_list_processes_pdfs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    papers_dir = Path("papers")
    papers_dir.mkdir()
    (papers_dir / "paper-one.pdf").write_bytes(b"dummy pdf content")
    (papers_dir / "ignore.txt").write_text("not a pdf")

    uploads = []
    responses = ["{\"Title\": \"Paper One\"}"]
    client = StubClient(responses=responses, upload_captures=uploads)
    summaries = arxiv_pipeline.summarize_reading_list([], client)

    assert summaries == responses
    assert uploads == [papers_dir / "paper-one.pdf"]


def test_remove_downloaded_papers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    papers_dir = Path("papers")
    papers_dir.mkdir()
    file_path = papers_dir / "temp.pdf"
    file_path.write_bytes(b"binary")

    arxiv_pipeline.remove_downloaded_papers()

    assert papers_dir.exists()
    assert not file_path.exists()


def test_parse_summary_matches_titles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    summary_payload = [
        json.dumps(
            {
                "Title": "OneThinker: Unified Reasoning",
                "Field & Subfield": "Machine Learning",
            }
        ),
        json.dumps(
            {
                "Title": "CAMEO - Multi-View Diffusion",
                "Field & Subfield": "Computer Vision",
            }
        ),
    ]

    reading_list = [
        {"title": "CAMEO: Multi-View Diffusion", "id": "http://arxiv.org/abs/0002.00002v1"},
        {"title": "OneThinker - Unified Reasoning", "id": "http://arxiv.org/abs/0001.00001v1"},
    ]

    parsed = arxiv_pipeline.parse_summary(summary_payload, reading_list)

    assert len(parsed) == 2

    first_entry = _kv_list_to_dict(parsed[0])
    second_entry = _kv_list_to_dict(parsed[1])

    assert first_entry["arxiv_id"] == "http://arxiv.org/abs/0001.00001v1"
    assert second_entry["arxiv_id"] == "http://arxiv.org/abs/0002.00002v1"

    log_path = Path("log.json")
    assert log_path.exists()
    contents = json.loads(log_path.read_text())
    assert [item["arxiv_id"] for item in contents] == [
        "http://arxiv.org/abs/0001.00001v1",
        "http://arxiv.org/abs/0002.00002v1",
    ]


def test_parse_summary_handles_unmatched_titles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    summary_payload = [
        json.dumps({"Title": "Paper Without Match", "Field & Subfield": "Other"})
    ]

    reading_list = [
        {"title": "Some Other Paper", "id": "http://arxiv.org/abs/9999.99999v1"}
    ]

    parsed = arxiv_pipeline.parse_summary(summary_payload, reading_list)

    assert len(parsed) == 1
    entry = _kv_list_to_dict(parsed[0])
    assert "arxiv_id" not in entry

    log_contents = json.loads(Path("log.json").read_text())
    assert "arxiv_id" not in log_contents[0]


def test_parse_summary_skips_invalid_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    parsed = arxiv_pipeline.parse_summary(["not valid json"], [])
    captured = capsys.readouterr()

    assert parsed == []
    assert "Error parsing summary" in captured.out
    assert not Path("log.json").exists()
