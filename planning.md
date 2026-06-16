# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Filters the `listings.json` dataset for items that match the user's requested description, preferred size, and maximum budget. It uses the listing fields `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform` to determine relevance.

**Input parameters:**
- `description` (str): the search text the user provides describing the item they want, such as "vintage graphic tee" or "chunky sneakers".
- `size` (str): the size preference from the user, such as "M", "S/M", "W30", "US 7", or a fit term like "baggy".
- `max_price` (float): the highest price the user is willing to pay.

**What it returns:**
A list of listing dictionaries sorted by relevance. Each dictionary contains:
- `id` (str)
- `title` (str)
- `description` (str)
- `category` (str)
- `style_tags` (list[str])
- `size` (str)
- `condition` (str)
- `price` (float)
- `colors` (list[str])
- `brand` (str or None)
- `platform` (str)

The tool should return the top matches, up to 5 results, with the most relevant result first.

**What happens if it fails or returns nothing:**
If the search returns no matching listings, the agent stops the tool chain and returns a user-facing error message such as "I couldn't find any listings that match that description and budget. Try broadening the search, changing the size, or increasing the budget." It must not call `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Chooses wardrobe pieces that complement the selected marketplace item. It compares the new item to the wardrobe by category, shared `style_tags`, and color compatibility, then describes how to wear the item with existing closet pieces.

**Input parameters:**
- `new_item` (dict): the selected listing object from `search_listings`.
- `wardrobe` (dict): a wardrobe dictionary with an `items` list following the structure in `wardrobe_schema.json`.

**What it returns:**
A dictionary with:
- `outfit_description` (str): a styling recommendation describing how to pair the new item with existing wardrobe pieces.
- `matched_items` (list[dict]): one or more wardrobe items used in the suggestion, each containing `id`, `name`, `category`, `colors`, `style_tags`, and optional `notes`.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or no good matches are found, return `matched_items=[]` and a fallback `outfit_description` like "I couldn't find a good match in your current wardrobe — add more pieces and I can pair this item perfectly." The agent should still proceed to `create_fit_card` using this fallback text.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, social-style caption that highlights the selected listing and the outfit recommendation, in the tone of a fit card or fashion caption.

**Input parameters:**
- `outfit` (dict): the output from `suggest_outfit`, containing `outfit_description` and `matched_items`.
- `new_item` (dict): the selected listing returned by `search_listings`.

**What it returns:**
A dictionary containing:
- `fit_card` (str): a concise caption that frames the recommendation in stylish language.

**What happens if it fails or returns nothing:**
If `outfit` is missing or incomplete, return a safe fallback `fit_card` such as "I found a great piece — once you add more wardrobe details, I can pair it with your closet and create a fit card." This fallback should be included in the final response.

---

### Additional Tools (if any)

No additional tools are required for the core FitFindr flow.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The planning loop follows a fixed sequence with conditional checks at each step:

1. Parse the user query into structured values: `description`, `size`, and `max_price`.
2. Call `search_listings(description, size, max_price)`.
3. If `search_listings` returns an empty list, set `session['error']` and return immediately with a message asking the user to broaden the search, change size, or increase the budget. Do not call `suggest_outfit` or `create_fit_card`.
4. Otherwise, set `session['search_results'] = results` and `session['selected_item'] = results[0]`.
5. Call `suggest_outfit(new_item=session['selected_item'], wardrobe=wardrobe)`.
6. If `suggest_outfit` returns `matched_items=[]` or an empty `outfit_description`, set `session['warning']` to a fallback wardrobe message but continue the flow.
7. Set `session['outfit'] = suggest_outfit_result`.
8. Call `create_fit_card(outfit=session['outfit'], new_item=session['selected_item'])`.
9. Set `session['fit_card']` to the returned caption.
10. Return the final response object containing `selected_item`, `outfit_suggestion`, `fit_card`, and any `error` or `warning`.

The planner completes after `create_fit_card` succeeds, or earlier if the search result list is empty.

---

## State Management

**How does information from one tool get passed to the next?**
The agent keeps a session dictionary to pass data between tools. The session stores:
- `query`: parsed user request values.
- `search_results`: the list of listings returned by `search_listings`.
- `selected_item`: the top listing from `search_results`.
- `outfit`: the object returned by `suggest_outfit`.
- `fit_card`: the caption returned by `create_fit_card`.
- `error`: any early-stop error message.
- `warning`: recoverable messages about weak wardrobe matching.

After `search_listings`, `selected_item` and `search_results` are saved. After `suggest_outfit`, `outfit` is saved. After `create_fit_card`, `fit_card` is saved. If the wardrobe is empty, the agent should source `get_empty_wardrobe()` and allow `suggest_outfit` to return a fallback description.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Return: "I couldn't find any listings that match that description and budget. Try broadening the description, choosing a different size, or increasing the budget." Stop the flow and do not call `suggest_outfit` or `create_fit_card`. |
| suggest_outfit | Wardrobe is empty or no compatible items | Return `matched_items=[]` and `outfit_description` fallback text. Continue to `create_fit_card` so the user still receives a helpful response. |
| create_fit_card | Outfit input is missing or incomplete | Return a fallback `fit_card` such as "I found a great piece — once you add more wardrobe details, I can pair it with your closet and create a fit card." Include this in the final response. |

---

## Architecture

```mermaid
flowchart TD
    User[User query] --> Planner[Planning Loop]
    Planner --> Search[search_listings(description, size, max_price)]
    Search -->|results=[]| Error[No listings found]
    Error -->|return early| FinalError[Final response with guidance]
    Search -->|results=[item,...]| Select[Set selected_item = results[0]]
    Select --> Planner
    Planner --> Suggest[suggest_outfit(new_item, wardrobe)]
    Suggest -->|matched_items=[]| Warning[Set warning and use fallback description]
    Warning --> Planner
    Suggest -->|matched_items>0| Planner
    Planner --> Create[create_fit_card(outfit, selected_item)]
    Create --> Final[Final response with item, outfit, fit_card]
    Planner --> Final
```

This diagram shows the normal flow from user query to search to outfit suggestion to fit card, the early error branch when no listings are found, and the recoverable wardrobe fallback path.

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
- For `search_listings`, I will use ChatGPT with the `Tool 1` section and the loader helper doc from `utils/data_loader.py`. I expect a function that uses `load_listings()` to filter by description text, size matching, and maximum price. I will verify that the function returns full listing dictionaries and handles empty results by returning `[]`.
- For `suggest_outfit`, I will use ChatGPT with the `Tool 2` section and the wardrobe schema from `wardrobe_schema.json`. I expect a function that returns `{'outfit_description': str, 'matched_items': list}` and that it handles empty wardrobes or weak matches gracefully. I will verify by testing with both `get_example_wardrobe()` and `get_empty_wardrobe()`.
- For `create_fit_card`, I will use ChatGPT with the `Tool 3` section and sample `outfit` / `new_item` payloads. I expect a function that returns a dictionary with `fit_card` and uses the listing title and outfit description in a friendly caption. I will verify by calling it directly with valid and incomplete inputs.

**Milestone 4 — Planning loop and state management:**
- I will use ChatGPT with the `## Planning Loop`, `## State Management`, and `## Architecture` sections. I expect a controller implementation that parses the query, calls `search_listings` first, stops early if there are no results, then calls `suggest_outfit`, then `create_fit_card`, and stores the session state at each step. I will verify by simulating an example query and ensuring the planner returns `selected_item`, `outfit_suggestion`, `fit_card`, and any error or warning messages.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into `description = "vintage graphic tee"`, `size = "M"` if provided, and `max_price = 30.0`, then calls `search_listings(description, size, max_price)`.

**Step 2:**
`search_listings` loads `listings.json` and filters for listings whose `title`, `description`, or `style_tags` match the query keywords, whose `size` matches or includes the requested size, and whose `price <= 30.0`. It returns a ranked list of matching listings.

**Step 3:**
The planner selects the top result as `selected_item` and calls `suggest_outfit(new_item=selected_item, wardrobe=get_example_wardrobe())`.

**Step 4:**
`suggest_outfit` compares the selected listing with the wardrobe items using category compatibility, shared `style_tags`, and color harmony. It returns `outfit_description` and `matched_items` describing a suggested outfit.

**Step 5:**
The planner calls `create_fit_card(outfit=outfit_result, new_item=selected_item)`.

**Step 6:**
`create_fit_card` returns a short caption such as "Snagged this vintage graphic tee for under $30 — pairing it with my baggy jeans and chunky sneakers for an easy streetwear fit.".

**Final output to user:**
A response containing the selected listing, why it was chosen, the outfit suggestion using the wardrobe, and a short fit card caption.

> `get_example_wardrobe()` is used for testing and example output. `get_empty_wardrobe()` is the empty wardrobe template used when the user has not provided closet items yet.
