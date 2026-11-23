"""Unit tests for integrations.critiquebrainz.reviews (CB-1)."""

from __future__ import annotations

from typing import Any

from integrations.critiquebrainz.reviews import (
    CRITIQUEBRAINZ_REVIEW_URL,
    MAX_PAGES,
    fetch_critiquebrainz_reviews,
    reflow_paragraphs,
)


def test_reflow_preserves_existing_paragraph_breaks() -> None:
    text = "First paragraph here.\r\n\r\n\r\nSecond paragraph here."
    assert reflow_paragraphs(text) == [
        "First paragraph here.",
        "Second paragraph here.",
    ]


def test_reflow_splits_unbroken_block_at_sentence_boundary_near_90_words() -> None:
    sentence_a = " ".join(["alpha"] * 44) + "."
    sentence_b = " ".join(["beta"] * 44) + "."
    sentence_c = " ".join(["gamma"] * 30) + "."
    text = f"{sentence_a} {sentence_b} {sentence_c}"

    paragraphs = reflow_paragraphs(text)
    assert len(paragraphs) == 2
    assert paragraphs[0].endswith("beta.")
    assert paragraphs[1].startswith("gamma")


def test_reflow_supports_arabic_question_mark_boundary() -> None:
    part1 = " ".join(["كلمة"] * 88) + "؟"
    part2 = " ".join(["جملة"] * 20) + "."
    paragraphs = reflow_paragraphs(f"{part1} {part2}")
    assert len(paragraphs) == 2
    assert paragraphs[0].endswith("؟")


def test_reflow_falls_back_to_word_boundary_when_no_sentence_in_window() -> None:
    text = " ".join(["word"] * 150)
    paragraphs = reflow_paragraphs(text)
    assert len(paragraphs) == 2
    assert len(paragraphs[0].split()) == 90
    assert len(paragraphs[1].split()) == 60


def test_fetch_filters_orders_and_paginates() -> None:
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, *, params: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        offset = params["offset"]
        if offset == 0:
            return {
                "count": 3,
                "reviews": [
                    {
                        "id": "rev-draft",
                        "language": "en",
                        "is_draft": True,
                        "is_hidden": False,
                        "text": "This is a draft review that is definitely longer than forty characters.",
                    },
                    {
                        "id": "rev-hidden",
                        "language": "en",
                        "is_draft": False,
                        "is_hidden": True,
                        "text": "This is a hidden review that is definitely longer than forty characters.",
                    },
                    {
                        "id": "rev-es",
                        "language": "es",
                        "is_draft": False,
                        "is_hidden": False,
                        "text": "Esta reseña está en español y tiene más de cuarenta caracteres.",
                    },
                    {
                        "id": "rev-short",
                        "language": "en",
                        "is_draft": False,
                        "is_hidden": False,
                        "text": "Too short.",
                    },
                    {
                        "id": "rev-fr",
                        "language": "fr",
                        "is_draft": False,
                        "is_hidden": False,
                        "text": "Un album remarquable avec une production très soignée du début à la fin.",
                        "user": {"display_name": "Claire"},
                        "rating": 4,
                        "popularity": 5,
                        "published_on": "2024-01-10",
                        "license": {"id": "CC BY-SA 3.0", "info_url": "https://creativecommons.org/licenses/by-sa/3.0/"},
                    },
                ],
            }
        return {
            "count": 3,
            "reviews": [
                {
                    "id": "rev-bbc",
                    "language": "en",
                    "is_draft": False,
                    "is_hidden": False,
                    "source": "BBC",
                    "text": "A landmark release that reshaped the genre with unmistakable clarity.",
                    "user": {"display_name": "BBC Reviewer"},
                    "rating": 5,
                    "popularity": 5,
                    "published_on": "2020-05-01",
                    "license": {"id": "CC BY 3.0", "info_url": "https://creativecommons.org/licenses/by/3.0/"},
                },
                {
                    "id": "rev-ar",
                    "language": "ar",
                    "is_draft": False,
                    "is_hidden": False,
                    "text": "ألبوم رائع يتميز بتوزيع موسيقي متقن وأداء صوتي مميز للغاية.",
                    "user": {"display_name": "طارق"},
                    "popularity": 10,
                    "published_on": "2023-06-01",
                },
            ],
        }

    results = fetch_critiquebrainz_reviews("rg-123", get=fake_get, page_limit=2)

    assert len(calls) == 2
    assert calls[0]["url"] == CRITIQUEBRAINZ_REVIEW_URL
    assert calls[0]["params"]["entity_id"] == "rg-123"
    assert calls[0]["params"]["entity_type"] == "release_group"
    assert calls[1]["params"]["offset"] == 2

    # Ordered by popularity desc (10 -> rev-ar), then BBC tie-break (rev-bbc), then rev-fr.
    assert [r["id"] for r in results] == ["rev-ar", "rev-bbc", "rev-fr"]
    assert results[1]["origin"] == "BBC"
    assert results[1]["source"] == "CritiqueBrainz"
    assert results[1]["url"] == "https://critiquebrainz.org/review/rev-bbc"
    assert results[1]["license"] == "CC BY 3.0"


def test_fetch_respects_max_pages_ceiling() -> None:
    calls = 0

    def fake_get(url: str, *, params: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"count": 1000, "reviews": [{"id": f"r-{calls}", "language": "en", "text": "x" * 50}]}

    results = fetch_critiquebrainz_reviews("rg-big", get=fake_get, page_limit=1)
    assert calls == MAX_PAGES
    assert len(results) == MAX_PAGES


def test_fetch_empty_mbid_returns_empty() -> None:
    called = False

    def fake_get(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {}

    assert fetch_critiquebrainz_reviews("", get=fake_get) == []
    assert not called
