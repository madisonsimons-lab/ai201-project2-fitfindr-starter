# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`
- Inputs:
  - `description`: user search text
  - `size`: optional size filter
  - `max_price`: optional upper budget bound
- Outputs:
  - list of listing dictionaries sorted by relevance, with up to 5 results
- Purpose:
  - filter `data/listings.json` and rank matching items by keyword overlap, size match, condition, and price.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`
- Inputs:
  - `new_item`: the selected marketplace listing
  - `wardrobe`: a wardrobe dict containing `items`
- Outputs:
  - styling recommendation string
- Purpose:
  - suggest how to wear the selected item using existing wardrobe pieces or, when the wardrobe is empty, provide general styling advice.

### `create_fit_card(outfit: str, new_item: dict) -> str`
- Inputs:
  - `outfit`: outfit suggestion text
  - `new_item`: selected listing dict
- Outputs:
  - social caption string
- Purpose:
  - convert the outfit recommendation into a casual Instagram-style fit caption that mentions item name, price, and platform.

## Planning Loop

The agent uses a session-based pipeline in `agent.py`. Each request follows these steps:

1. Parse the user query into `description`, `size`, and `max_price`.
2. Store the parsed values in `session["parsed"]`.
3. Call `search_listings()` and write the returned matches into `session["search_results"]`.
4. If `search_results` is empty, stop early and set `session["error"]`.
5. Otherwise select the top result as `session["selected_item"]`.
6. Call `suggest_outfit()` with the selected item and wardrobe, storing the response in `session["outfit_suggestion"]`.
7. Call `create_fit_card()` with the outfit suggestion and selected item, storing the output in `session["fit_card"]`.

This means the agent only advances to outfit generation when a valid search result exists. If `search_listings()` returns `[]`, the agent does not call `suggest_outfit()` or `create_fit_card()`.

## State Management

The session dict is the single source of truth for one interaction. It contains:

- `query`: raw user text
- `parsed`: extracted structured inputs
- `search_results`: listings returned from search
- `selected_item`: the chosen top listing
- `wardrobe`: the user wardrobe passed in
- `outfit_suggestion`: text returned from `suggest_outfit()`
- `fit_card`: caption returned from `create_fit_card()`
- `error`: early stop message when the flow cannot continue

This keeps the agent from hardcoding tool outputs or re-invoking the same step unnecessarily.

## Error Handling

Each tool includes a deliberate failure mode with a user-friendly message.

- `search_listings()` returns `[]` when no matching items exist. Example: searching for a `designer ballgown` under `$5` yields an empty list, and the agent returns: `I couldn't find any listings that match that description and budget. Try broadening the description, choosing a different size, or increasing the budget.`
- `suggest_outfit()` returns a fallback styling tip if the wardrobe is empty instead of raising an exception. Example: with an empty wardrobe it returns: `I couldn't find a good match in your current wardrobe — add more pieces and I can pair this item perfectly.`
- `create_fit_card()` returns a fallback caption when `outfit` is empty, such as: `I found a great piece — once you add more wardrobe details, I can pair it with your closet and create a fit card.`

## AI Usage

I used AI assistance for two main tasks:

1. **Planning loop implementation**
   - Input: the `planning.md` tool definitions, planning loop diagram, and state management sections.
   - Output: a candidate `run_agent()` implementation with explicit session tracking.
   - Review: I verified the generated code only advanced when search results existed, preserved state in `session`, and returned early on no-results.

2. **Error handling and message design**
   - Input: the tool failure cases and expected user-facing fallback strings.
   - Output: phrasing for graceful fallback responses and guidance for when an empty wardrobe or empty outfit is encountered.
   - Review: I refined the results to ensure each fallback was helpful and not just generic "error" text.

## Running the App

Install dependencies and set your Groq key:

```bash
pip install -r requirements.txt
```

Create a `.env` with:

```text
GROQ_API_KEY=your_key_here
```

Start the app:

```bash
python app.py
```

Then open the URL shown in the terminal.

## Current Notes

The Gradio app launch currently hits a runtime error in the local environment before the UI fully renders. The agent logic and CLI tests are implemented and verified, but the app page startup needs a dependency/runtime fix before the browser UI can be used.
