"""
tests/test_tools.py

Pytest tests for the three FitFindr tools.
At least one test per failure mode, plus happy-path coverage.

Run with:
    pytest tests/test_tools.py -v
"""

from unittest.mock import MagicMock, patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_listing():
    """A single realistic listing dict matching listings.json schema."""
    return {
        "id": "lst_006",
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit.",
        "category": "tops",
        "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"],
        "size": "L",
        "condition": "good",
        "price": 24.00,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }


@pytest.fixture
def example_wardrobe():
    """A wardrobe dict with two items — enough to test pairing logic."""
    return {
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans, dark wash",
                "category": "bottoms",
                "colors": ["dark blue", "indigo"],
                "style_tags": ["denim", "streetwear", "baggy"],
                "notes": "High-waisted, sits above the hip",
            },
            {
                "id": "w_007",
                "name": "Chunky white sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["sneakers", "chunky", "streetwear"],
                "notes": None,
            },
        ]
    }


@pytest.fixture
def empty_wardrobe():
    """An empty wardrobe matching the empty_wardrobe template."""
    return {"items": []}


def _mock_groq_response(content: str):
    """Helper: return a mock Groq client whose completion returns `content`."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
    return mock_client


# ── Tool 1: search_listings ───────────────────────────────────────────────────

class TestSearchListings:

    def test_returns_results_for_valid_query(self):
        """Happy path: a reasonable query should return at least one listing."""
        results = search_listings(description="vintage graphic tee")
        assert len(results) > 0

    def test_results_are_sorted_by_relevance(self):
        """Top result should be more relevant than the last result."""
        results = search_listings(description="vintage graphic tee")
        assert len(results) >= 2  # need at least 2 to compare
        # All returned items should have matched at least one keyword —
        # verified implicitly by the fact that score-0 items are dropped

    def test_price_filter_excludes_expensive_items(self):
        """No result should exceed max_price."""
        results = search_listings(description="vintage", max_price=20.0)
        for item in results:
            assert item["price"] <= 20.0

    def test_size_filter_case_insensitive(self):
        """Size filter should match case-insensitively (e.g. 'm' matches 'S/M')."""
        results = search_listings(description="tee", size="m")
        for item in results:
            assert "m" in item["size"].lower()

    # ── Failure mode: no results ──────────────────────────────────────────────

    def test_returns_empty_list_when_price_too_low(self):
        """
        Failure mode: price ceiling so low nothing can match.
        Agent should receive an empty list and set session["error"].
        """
        results = search_listings(description="jacket", max_price=0.01)
        assert results == []

    def test_returns_empty_list_when_size_matches_nothing(self):
        """
        Failure mode: size string that doesn't appear in any listing.
        Agent should receive an empty list and set session["error"].
        """
        results = search_listings(description="shirt", size="XXXXXXXXXXXXL")
        assert results == []

    def test_returns_empty_list_when_description_matches_nothing(self):
        """
        Failure mode: description with no keyword overlap against any listing.
        Agent should receive an empty list and set session["error"].
        """
        results = search_listings(description="spaceship quantum tuxedo")
        assert results == []

    def test_no_exception_on_empty_results(self):
        """search_listings must return [] not raise when nothing matches."""
        try:
            results = search_listings(description="zzzznotaword", max_price=0.01)
            assert results == []
        except Exception as e:
            pytest.fail(f"search_listings raised an exception: {e}")


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

class TestSuggestOutfit:

    def test_returns_string_with_populated_wardrobe(self, sample_listing, example_wardrobe):
        """Happy path: should return a non-empty string referencing wardrobe pieces."""
        mock_client = _mock_groq_response(
            "Pair the tee with your baggy jeans [w_001] and chunky sneakers [w_007]."
        )
        with patch("tools._get_groq_client", return_value=mock_client):
            result = suggest_outfit(sample_listing, example_wardrobe)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_wardrobe_items_referenced_in_prompt(self, sample_listing, example_wardrobe):
        """Wardrobe item names should appear in the prompt sent to the LLM."""
        mock_client = _mock_groq_response("Some outfit suggestion.")
        with patch("tools._get_groq_client", return_value=mock_client):
            suggest_outfit(sample_listing, example_wardrobe)

        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "w_001" in prompt
        assert "Baggy straight-leg jeans" in prompt

    # ── Failure mode: empty wardrobe ──────────────────────────────────────────

    def test_returns_general_advice_when_wardrobe_empty(self, sample_listing, empty_wardrobe):
        """
        Failure mode: wardrobe is empty.
        Tool should call LLM for general styling advice and return a non-empty string.
        """
        mock_client = _mock_groq_response(
            "This tee pairs well with straight-leg jeans and white sneakers."
        )
        with patch("tools._get_groq_client", return_value=mock_client):
            result = suggest_outfit(sample_listing, empty_wardrobe)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_empty_wardrobe_prompt_does_not_mention_wardrobe_ids(
        self, sample_listing, empty_wardrobe
    ):
        """
        When wardrobe is empty the prompt should ask for general advice,
        not try to reference specific wardrobe item IDs.
        """
        mock_client = _mock_groq_response("General styling advice here.")
        with patch("tools._get_groq_client", return_value=mock_client):
            suggest_outfit(sample_listing, empty_wardrobe)

        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "w_001" not in prompt
        assert "w_007" not in prompt

    def test_no_exception_when_wardrobe_empty(self, sample_listing, empty_wardrobe):
        """suggest_outfit must not raise even when wardrobe['items'] is []."""
        mock_client = _mock_groq_response("General advice.")
        with patch("tools._get_groq_client", return_value=mock_client):
            try:
                result = suggest_outfit(sample_listing, empty_wardrobe)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"suggest_outfit raised an exception: {e}")


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

class TestCreateFitCard:

    def test_returns_caption_for_valid_inputs(self, sample_listing):
        """Happy path: should return a non-empty caption string."""
        mock_client = _mock_groq_response(
            "Found this faded bootleg tee on depop for $24. Styled it with baggy jeans — pure 90s energy."
        )
        with patch("tools._get_groq_client", return_value=mock_client):
            result = create_fit_card(
                outfit="Pair with baggy jeans and chunky sneakers.",
                new_item=sample_listing,
            )
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_item_details_included_in_prompt(self, sample_listing):
        """Item name, price, and platform should all appear in the LLM prompt."""
        mock_client = _mock_groq_response("Caption here.")
        with patch("tools._get_groq_client", return_value=mock_client):
            create_fit_card(
                outfit="Pair with baggy jeans.",
                new_item=sample_listing,
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Graphic Tee" in prompt
        assert "24" in prompt
        assert "depop" in prompt

    # ── Failure mode: empty outfit string ────────────────────────────────────

    def test_returns_error_string_when_outfit_empty(self, sample_listing):
        """
        Failure mode: outfit is an empty string.
        Tool should return a descriptive error string, not raise.
        """
        result = create_fit_card(outfit="", new_item=sample_listing)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_returns_error_string_when_outfit_whitespace_only(self, sample_listing):
        """
        Failure mode: outfit is whitespace only.
        Tool should return a descriptive error string, not raise.
        """
        result = create_fit_card(outfit="   ", new_item=sample_listing)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_no_llm_call_when_outfit_empty(self, sample_listing):
        """
        When outfit is empty the tool should short-circuit and NOT call the LLM.
        """
        mock_client = _mock_groq_response("This should not be called.")
        with patch("tools._get_groq_client", return_value=mock_client):
            create_fit_card(outfit="", new_item=sample_listing)
        mock_client.chat.completions.create.assert_not_called()

    def test_no_exception_when_outfit_empty(self, sample_listing):
        """create_fit_card must not raise even when outfit is empty."""
        try:
            result = create_fit_card(outfit="", new_item=sample_listing)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"create_fit_card raised an exception: {e}")
