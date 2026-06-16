import pytest

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_listings_filters_by_price_and_size():
    results = search_listings("vintage graphic tee", size="M", max_price=30)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(result["price"] <= 30 for result in results)
    assert all("S/M" in result["size"] or "M" in result["size"] or "m" in result["size"].lower() for result in results)


def test_search_listings_returns_empty_when_no_match():
    results = search_listings("designer ball gown", size="XXS", max_price=5)
    assert results == []


def test_suggest_outfit_returns_fallback_for_empty_wardrobe(monkeypatch):
    new_item = {
        "title": "Vintage Graphic Tee",
        "description": "A soft black graphic tee with faded print.",
        "category": "tops",
        "colors": ["black"],
        "style_tags": ["vintage", "graphic tee"],
    }

    monkeypatch.setattr("tools._generate_groq_response", lambda prompt, temperature=0.8, max_tokens=220: None)

    result = suggest_outfit(new_item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert "couldn't find a good match" in result.lower()


def test_suggest_outfit_returns_custom_text_when_llm_available(monkeypatch):
    new_item = {
        "title": "Vintage Graphic Tee",
        "description": "A soft black graphic tee with faded print.",
        "category": "tops",
        "colors": ["black"],
        "style_tags": ["vintage", "graphic tee"],
    }

    monkeypatch.setattr("tools._generate_groq_response", lambda prompt, temperature=0.8, max_tokens=220: "Style it with your favorite denim jacket and chunky sneakers.")

    result = suggest_outfit(new_item, get_example_wardrobe())
    assert result == "Style it with your favorite denim jacket and chunky sneakers."


def test_create_fit_card_returns_fallback_for_empty_outfit():
    result = create_fit_card("", {"title": "Vintage Graphic Tee", "platform": "depop", "price": 18.0})
    assert isinstance(result, str)
    assert "add more wardrobe details" in result.lower()


def test_create_fit_card_uses_llm_response_when_available(monkeypatch):
    outfit = "Pair this tee with your denim jacket and white sneakers for an easy streetwear look."
    item = {"title": "Vintage Graphic Tee", "platform": "depop", "price": 18.0}

    monkeypatch.setattr("tools._generate_groq_response", lambda prompt, temperature=1.0, max_tokens=120: "Vintage fit: black tee, denim jacket, and chunky sneakers. Perfect thrifted style.")

    result = create_fit_card(outfit, item)
    assert result == "Vintage fit: black tee, denim jacket, and chunky sneakers. Perfect thrifted style."


def test_create_fit_card_generates_fallback_caption_when_llm_fails(monkeypatch):
    outfit = "Pair this tee with your denim jacket and white sneakers for an easy streetwear look."
    item = {"title": "Vintage Graphic Tee", "platform": "depop", "price": 18.0}

    monkeypatch.setattr("tools._generate_groq_response", lambda prompt, temperature=1.0, max_tokens=120: None)

    result = create_fit_card(outfit, item)
    assert "Snagged the Vintage Graphic Tee" in result
    assert "on depop" in result
    assert "effortless" in result or "wearable" in result
