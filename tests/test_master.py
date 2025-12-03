from types import SimpleNamespace

import pytest

import arxiv_pipeline
import main
import x_tweet_module


def test_main_happy_path(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    monkeypatch.setattr(x_tweet_module, "authenticate", lambda: "auth")

    stub_client = SimpleNamespace()

    def fake_client(*, api_key):
        assert api_key == "test-key"
        return stub_client

    monkeypatch.setattr(main.genai, "Client", fake_client)

    search_calls = []

    def fake_search(client):
        search_calls.append(client)
        return ["paper-object"]

    monkeypatch.setattr(arxiv_pipeline, "search_papers", fake_search)
    monkeypatch.setattr(
        arxiv_pipeline,
        "summarize_reading_list",
        lambda result, client: ["summary-json"],
    )
    monkeypatch.setattr(
        arxiv_pipeline,
        "judge_papers",
        lambda papers, client: [{"id": "http://arxiv.org/abs/0001.00001v1"}],
    )
    monkeypatch.setattr(
        arxiv_pipeline,
        "parse_summary",
        lambda summaries, reading: [["Title: Example", "arxiv_id: http://arxiv.org/abs/0001.00001v1"]],
    )

    posted = {}

    def fake_post(auth, data, dry_run=True):
        posted["payload"] = (auth, data, dry_run)

    monkeypatch.setattr(x_tweet_module, "post", fake_post)

    remove_called = {"called": False}

    def fake_remove():
        remove_called["called"] = True

    monkeypatch.setattr(arxiv_pipeline, "remove_downloaded_papers", fake_remove)

    main.main()

    assert search_calls == [stub_client]
    assert posted["payload"][0] == "auth"
    assert posted["payload"][2] is True
    assert remove_called["called"] is True


def test_main_requires_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(x_tweet_module, "authenticate", lambda: "auth")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        main.main()
