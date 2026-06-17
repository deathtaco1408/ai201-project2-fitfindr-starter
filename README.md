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

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
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

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.** Your documented interfaces will be checked against your actual function signatures in `tools.py` — if the parameter count or types contradict what's in the code, you may not receive full credit for that tool.

---

## Interaction Walkthrough

<!-- Walk through a complete interaction step by step: natural language query → each tool call (and why) → final fit card.
     Walk through this carefully — it's how graders follow your agent's reasoning without a live demo.
     Use a specific example — do not leave this as a template. -->

**User query:**
"looking for a vintage graphic tee under $30"

**Step 1 — Tool called:**
- Tool: search_listings
- Input: description="looking for a vintage graphic tee", size=None, max_price=30.0
- Why this tool: The agent always searches first — it needs a matching listing before it can suggest an outfit or generate a fit card. The query is parsed with regex to extract the price ceiling ($30) and leave the rest as the description.
- Output: A ranked list of listings under $30 that match "vintage graphic tee" by keyword overlap. Top result: lst_006 — "Graphic Tee — 2003 Tour Bootleg Style", $24, size L, on depop.

**Step 2 — Tool called:**
- Tool: suggest_outfit
- Input: new_item=lst_006, wardrobe=example_wardrobe (10 items loaded from wardrobe_schema.json)
- Why this tool: Now that we have a selected item, the agent pairs it with the user's existing wardrobe pieces using the Groq LLM.
- Output: "Pair the bootleg tee with your baggy straight-leg jeans [w_001] and chunky white sneakers [w_007] for a classic streetwear look. For a grungier take, try it with your black combat boots [w_008] and vintage denim jacket [w_006]."

**Step 3 — Tool called:**
- Tool: create_fit_card
- Input: outfit=<suggestion from step 2>, new_item=lst_006
- Why this tool: The final step — takes the item and outfit and generates a shareable OOTD caption for the fit card panel.
- Output: "Found this faded bootleg tee on depop for $24 and it's already my new favorite. Styled it with baggy dark wash jeans and chunky sneakers — pure 90s streetwear energy. Condition is good and honestly the worn-in look makes it better."

**Final output to user:**
The Gradio UI populates three panels: panel 1 shows the listing details (title, price, size, condition, platform, colors, style tags); panel 2 shows the wardrobe-specific outfit suggestion; panel 3 shows the OOTD fit card caption.

---

## Error Handling and Fail Points

<!-- For each tool, describe the specific failure mode and what your agent does in response.
     This maps to the error handling section of the rubric (F5-C1). -->

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the description, size, or price filter | Returns an empty list. run_agent() detects this, sets session["error"] to a helpful message ("No listings matched — try raising your price limit, adjusting your size, or using a broader description."), and returns early. suggest_outfit and create_fit_card are never called. |
| `suggest_outfit` | wardrobe["items"] is an empty list | Handled internally — the tool detects the empty wardrobe and calls the Groq LLM for general styling advice instead of wardrobe-specific pairings. Always returns a non-empty string; the planning loop never branches here. |
| `create_fit_card` | outfit is an empty or whitespace-only string | Handled internally — the tool short-circuits before calling the LLM and returns a descriptive error string instead of raising an exception. The session still completes and session["fit_card"] is set. |

---

## Spec Reflection

<!-- Answer both questions with at least 2–3 sentences each. -->

**One way planning.md helped during implementation:**
Writing out the step-by-step interaction walkthrough in planning.md made it straightforward to know exactly what inputs to test at each stage. Rather than guessing what a "good" test query looked like, the walkthrough gave a concrete example — a vintage graphic tee under $30 — that I could run directly against each tool as I built it. This made it much easier to catch issues early, before wiring everything together in agent.py.

**One divergence from your spec, and why:**
The planning.md noted that query parsing could use regex, string splitting, or an LLM call, but didn't commit to one approach. During implementation, regex turned out to be the right choice — it's fast, deterministic, and doesn't consume an extra Groq API call just to extract a price and size from a short string. An LLM-based parser would have added latency and cost with no real benefit for the simple patterns ($30, size M) the queries contain.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
