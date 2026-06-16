from agent import run_agent
from app import handle_query
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_run_agent_returns_selected_item_and_outfit_state(monkeypatch):
    called = {}

    def fake_suggest_outfit(item, wardrobe):
        called["selected_item"] = item
        called["wardrobe"] = wardrobe
        return "Styled with your favorite denim jacket."

    def fake_create_fit_card(outfit, item):
        called["outfit_suggestion"] = outfit
        called["selected_item_for_caption"] = item
        return "Caption text."

    monkeypatch.setattr("agent.suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr("agent.create_fit_card", fake_create_fit_card)

    wardrobe = get_example_wardrobe()
    session = run_agent("vintage graphic tee under $30", wardrobe)

    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["search_results"]
    assert session["outfit_suggestion"] == "Styled with your favorite denim jacket."
    assert session["fit_card"] == "Caption text."
    assert session["selected_item"] == called["selected_item"]
    assert session["selected_item"] == called["selected_item_for_caption"]
    assert called["outfit_suggestion"] == session["outfit_suggestion"]
    assert called["wardrobe"] == wardrobe


def test_run_agent_stops_when_search_returns_no_results(monkeypatch):
    def fake_search_listings(description, size=None, max_price=None):
        return []

    monkeypatch.setattr("agent.search_listings", fake_search_listings)
    monkeypatch.setattr("agent.suggest_outfit", lambda item, wardrobe: "SHOULD NOT BE CALLED")
    monkeypatch.setattr("agent.create_fit_card", lambda outfit, item: "SHOULD NOT BE CALLED")

    wardrobe = get_example_wardrobe()
    session = run_agent("designer ballgown size XXS under $5", wardrobe)

    assert session["error"] is not None
    assert session["fit_card"] is None
    assert session["outfit_suggestion"] is None
    assert session["search_results"] == []
    assert session["selected_item"] is None


def test_handle_query_returns_error_for_empty_query():
    listing, outfit, fit_card = handle_query("", "Example wardrobe")
    assert "please type what you're looking for" in listing.lower()
    assert outfit == ""
    assert fit_card == ""


def test_handle_query_maps_session_values_to_outputs(monkeypatch):
    def fake_run_agent(query, wardrobe):
        return {
            "error": None,
            "selected_item": {
                "title": "Test Item",
                "description": "A great find.",
                "price": 12.0,
                "platform": "depop",
                "size": "M",
                "condition": "good",
            },
            "outfit_suggestion": "Pair it with black jeans.",
            "fit_card": "Caption text.",
        }

    monkeypatch.setattr("app.run_agent", fake_run_agent)
    listing_text, outfit, fit_card = handle_query("vintage tee", "Example wardrobe")

    assert "Test Item" in listing_text
    assert "A great find." in listing_text
    assert outfit == "Pair it with black jeans."
    assert fit_card == "Caption text."
