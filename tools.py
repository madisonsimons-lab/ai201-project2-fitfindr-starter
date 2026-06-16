"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def _extract_keywords(text: str) -> set[str]:
    return {token for token in re.findall(r"\w+", _normalize_text(text)) if token}


def _size_matches(requested_size: str, listing_size: str) -> bool:
    requested = _normalize_text(requested_size)
    listing = _normalize_text(listing_size)
    if not requested or not listing:
        return False
    return requested in listing or listing in requested


def _score_listing(listing: dict, keywords: set[str], size_filter: str | None) -> int:
    title = _normalize_text(listing.get("title", ""))
    description = _normalize_text(listing.get("description", ""))
    category = _normalize_text(listing.get("category", ""))
    style_tags = [_normalize_text(tag) for tag in listing.get("style_tags", []) if tag]
    colors = [_normalize_text(color) for color in listing.get("colors", []) if color]
    brand = _normalize_text(listing.get("brand", "") or "")
    platform = _normalize_text(listing.get("platform", ""))

    searchable = " ".join(
        [title, description, category, brand, platform, " ".join(style_tags), " ".join(colors)]
    )

    score = 0
    for keyword in keywords:
        if keyword in searchable:
            score += 2
        if keyword == category:
            score += 1
        if keyword in style_tags:
            score += 1
        if keyword in colors:
            score += 1
        if keyword == brand or keyword == platform:
            score += 1

    if size_filter and _size_matches(size_filter, listing.get("size", "")):
        score += 1

    return score


def _get_condition_rank(condition: str) -> int:
    rank = {"excellent": 0, "good": 1, "fair": 2}
    return rank.get(_normalize_text(condition), 3)


def _call_groq(messages: list[dict], model: str, temperature: float, max_completion_tokens: int) -> str | None:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
        if not response or not getattr(response, "choices", None):
            return None
        choice = response.choices[0]
        if not getattr(choice, "message", None):
            return None
        content = choice.message.content
        if content is None:
            return None
        return content.strip()
    except Exception:
        return None


def _generate_groq_response(prompt: str, temperature: float = 0.8, max_tokens: int = 220) -> str | None:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful fashion stylist and caption writer."
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    return _call_groq(messages, model="gemma-7b-it", temperature=temperature, max_completion_tokens=max_tokens)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    description = description or ""
    keywords = _extract_keywords(description)

    listings = load_listings()
    matches: list[tuple[int, dict]] = []

    for listing in listings:
        if max_price is not None and listing.get("price", float("inf")) > max_price:
            continue
        if size and not _size_matches(size, listing.get("size", "")):
            continue

        score = _score_listing(listing, keywords, size)
        if keywords and score == 0:
            continue
        if not keywords:
            score = 1

        matches.append((score, listing))

    matches.sort(
        key=lambda pair: (
            -pair[0],
            _get_condition_rank(pair[1].get("condition", "")),
            pair[1].get("price", 0),
        )
    )

    return [listing for _, listing in matches][:5]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

CATEGORY_COMPATIBILITY = {
    "tops": ["bottoms", "outerwear", "shoes", "accessories"],
    "bottoms": ["tops", "outerwear", "shoes", "accessories"],
    "outerwear": ["tops", "bottoms", "shoes", "accessories"],
    "shoes": ["tops", "bottoms", "outerwear", "accessories"],
    "accessories": ["tops", "bottoms", "outerwear", "shoes"],
}


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    new_item_title = new_item.get("title", "this item")

    if not wardrobe_items:
        fallback = (
            "I couldn't find a good match in your current wardrobe — add more pieces and "
            "I can pair this item perfectly."
        )
        prompt = (
            f"The user is considering buying a thrifted item: {new_item_title}. "
            f"The item details are: {new_item.get('description', '').strip()} "
            f"Category: {new_item.get('category', '').strip()}, "
            f"colors: {', '.join(new_item.get('colors', []))}. "
            "The wardrobe is currently empty. Give 1-2 styling ideas for this piece, "
            "including what vibes it suits and what kinds of pieces would pair well. "
            "Keep the answer conversational and helpful."
        )
        response = _generate_groq_response(prompt)
        return response or fallback

    item_tags = {_normalize_text(tag) for tag in new_item.get("style_tags", []) if tag}
    item_colors = {_normalize_text(color) for color in new_item.get("colors", []) if color}
    new_category = _normalize_text(new_item.get("category", ""))
    item_text = _normalize_text(new_item.get("title", "") + " " + new_item.get("description", ""))

    scored_items: list[tuple[int, dict]] = []
    for wardrobe_item in wardrobe_items:
        score = 0
        wardrobe_category = _normalize_text(wardrobe_item.get("category", ""))
        wardrobe_tags = {_normalize_text(tag) for tag in wardrobe_item.get("style_tags", []) if tag}
        wardrobe_colors = {_normalize_text(color) for color in wardrobe_item.get("colors", []) if color}

        if wardrobe_category in CATEGORY_COMPATIBILITY.get(new_category, []):
            score += 3
        elif wardrobe_category == new_category:
            score += 1

        shared_tags = item_tags.intersection(wardrobe_tags)
        score += len(shared_tags) * 2

        if item_colors.intersection(wardrobe_colors):
            score += 1

        if any(tag in item_text for tag in wardrobe_tags):
            score += 1

        if score > 0:
            scored_items.append((score, wardrobe_item))

    if not scored_items:
        fallback = (
            "I couldn't find a good match in your current wardrobe — add more pieces and "
            "I can pair this item perfectly."
        )
        prompt = (
            f"The user is considering buying a thrifted item: {new_item_title}. "
            f"Item details: {new_item.get('description', '').strip()} "
            f"Category: {new_item.get('category', '').strip()}, colors: {', '.join(new_item.get('colors', []))}. "
            "The user's wardrobe has items, but none are a strong match. "
            "Give styling advice for how this piece could work with a few versatile basics. "
            "Keep the answer conversational and helpful."
        )
        response = _generate_groq_response(prompt)
        return response or fallback

    scored_items.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    selected_items = [item for _, item in scored_items[:2]]
    selected_names = [item.get("name", "a wardrobe piece") for item in selected_items]

    if len(selected_names) == 1:
        outfit_description = (
            f"Pair the {new_item_title} with your {selected_names[0]}. "
            "This combination keeps the look cohesive while letting the new piece shine."
        )
    else:
        outfit_description = (
            f"Pair the {new_item_title} with your {selected_names[0]} and {selected_names[1]}. "
            "It creates a complete outfit with a balanced, easygoing vibe."
        )

    if item_tags:
        shared = item_tags.intersection(
            {_normalize_text(tag) for tag in selected_items[0].get("style_tags", [])}
        )
        if shared:
            outfit_description += f" The shared {', '.join(shared)} energy helps the look feel intentional."

    prompt = (
        f"You are a fashion stylist. The user is considering buying this thrifted item: {new_item_title}. "
        f"Item details: {new_item.get('description', '').strip()} Category: {new_item.get('category', '').strip()}. "
        f"Current wardrobe pieces to pair it with: {', '.join(selected_names)}. "
        f"Write a friendly, specific styling suggestion using those pieces and the vibe of the new item."
    )
    response = _generate_groq_response(prompt)
    return response or outfit_description


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return (
            "I found a great piece — once you add more wardrobe details, "
            "I can pair it with your closet and create a fit card."
        )

    title = new_item.get("title", "this find")
    platform = _normalize_text(new_item.get("platform", ""))
    price = new_item.get("price")
    try:
        price_value = float(price)
        if price_value.is_integer():
            price_str = f"${int(price_value)}"
        else:
            price_str = f"${price_value:.2f}"
    except Exception:
        price_str = str(price or "unknown price")

    prompt = (
        f"You are a social fashion caption writer. "
        f"Write a 2-4 sentence caption for an OOTD post that mentions the item name, "
        f"price, and platform naturally. The caption should feel authentic and casual. "
        f"Item: {title}. Price: {price_str}. Platform: {platform}. "
        f"Outfit suggestion: {outfit.strip()}"
    )

    response = _generate_groq_response(prompt, temperature=1.0, max_tokens=120)
    if response:
        return response

    first_clause = outfit.strip().split(".")[0].strip()
    if not first_clause:
        first_clause = "This piece is a perfect thrift find."

    caption = (
        f"Snagged the {title} for {price_str} on {platform}. "
        f"{first_clause} It feels effortless, wearable, and totally shareable."
    )
    return caption
