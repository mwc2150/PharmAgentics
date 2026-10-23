"""Stand-in semantic configuration for the brief-006 prototype.

Briefing B-I deviation, logged in specs/brief-006-agent-demo-ui/plan.md: until
core-002 ships the versioned semantic layer, every threshold, catalog entry, cap and
governed term the prototype uses lives here and nowhere else. Values are starting
points, not decisions on Evaluation Pack item 17.
"""

from __future__ import annotations

from datetime import date

RELEASE = "day1-v1"
SEED = 7
FIRST_WEEK = date(2024, 10, 14)
LAST_WEEK = date(2026, 10, 5)
INDEX_PRODUCT = "BXA"

PRODUCTS = {
    "BXA": "Cardiovela (BXA)",
    "BXC": "Lipidara (BXC)",
    "BXD": "Vascriva (BXD)",
    "BXE": "Metacora (BXE)",
}

TERRITORIES = {
    "NEW_ENGLAND": "New England",
    "MID_ATLANTIC": "Mid-Atlantic",
    "GREAT_LAKES": "Great Lakes",
    "SOUTHEAST": "Southeast",
    "SOUTH_CENTRAL": "South Central",
    "MOUNTAIN": "Mountain",
    "PACIFIC": "Pacific",
    "NORTHWEST": "Northwest",
}

# Aliases the intake parser accepts for each territory (lower case).
TERRITORY_ALIASES = {
    "NEW_ENGLAND": ["new england"],
    "MID_ATLANTIC": ["mid-atlantic", "mid atlantic", "midatlantic"],
    "GREAT_LAKES": ["great lakes"],
    "SOUTHEAST": ["southeast", "south east", "south-east"],
    "SOUTH_CENTRAL": ["south central", "south-central"],
    "MOUNTAIN": ["mountain"],
    "PACIFIC": ["pacific"],
    "NORTHWEST": ["northwest", "north west", "north-west"],
}

METRICS = {
    "trx": "TRx: total prescriptions filled (new and refills)",
    "nrx": "NRx: new prescriptions; a subset of TRx",
    "nbrx": "NBRx: new-to-brand prescriptions; a subset of NRx. The only metric that may be called new patients",
    "share": "Market share: index-brand TRx over TRx of the four-brand fictional basket",
}

# Competitive intelligence (stage 3) thresholds.
DETECTION = {
    "national_rel": 0.08,          # like-for-like national change vs 4-week average
    "single_gap": 0.22,            # peer-adjusted single-week change vs 4-week average
    "single_abs": 50,              # TRx
    "sustained_gap": 0.15,         # last 4 weeks vs 8 before, minus the same for peers
    "sustained_abs": 40,           # TRx a week
    "competitor_share": 0.05,      # share at which a recent launch is a story
    "competitor_launch_weeks": 52,
    "max_candidates": 15,
}

# Verdict rules for the hypothesis checks (stage 4).
DRIVER_RULES = {
    "material_gap": 0.10,          # peer gap a "why" story needs to count as material
    "promo_change": 0.25,          # relative change in aggregated rep calls
    "fill_floor": 0.95,            # inventory fill rate below this is a shortfall
    "competitor_excess": 0.03,     # share above every peer territory
    "plan_change": 0.10,           # plan-level TRx change behind an access event
    "default_window_weeks": 4,
    "default_baseline_weeks": 8,
}

# Hypothesis catalog: the finite search space (shared Principle VII, rule 2).
CATALOG = {
    "feed_health": {"specialist": "data_forensics", "kind": "artifact",
                    "label": "Data artifact",
                    "description": "Feed-health gate for the cut and window: missing or duplicate keys, coverage, lag, restatement review."},
    "restatement": {"specialist": "data_forensics", "kind": "artifact",
                    "label": "Restatement",
                    "description": "Restated Rx records for the cut and window, with prior and revised values."},
    "calendar": {"specialist": "data_forensics", "kind": "calendar",
                 "label": "Calendar effect",
                 "description": "Holiday weeks, business days and plan-year reset in the window, and the same weeks last year."},
    "access": {"specialist": "driver_investigator", "kind": "driver",
               "label": "Access",
               "description": "Formulary changes (coverage, tier, prior authorization, step therapy) on plans in the territory, and that plan's TRx."},
    "promotion": {"specialist": "driver_investigator", "kind": "driver",
                  "label": "Promotion",
                  "description": "Aggregated rep calls, digital impressions and rep-coverage gaps for the territory. Verdict either way."},
    "inventory": {"specialist": "driver_investigator", "kind": "driver",
                  "label": "Supply",
                  "description": "Inventory fill rate and backorders for the territory."},
    "competitor": {"specialist": "driver_investigator", "kind": "driver",
                   "label": "Competitor",
                   "description": "Recent competitor launches and their share in the territory against peer territories."},
    "concentration": {"specialist": "driver_investigator", "kind": "context",
                      "label": "Concentration",
                      "description": "Contribution decomposition of the change by payer channel, plan and specialty (or by territory for a national story)."},
}

# Which checks apply to which story kind.
APPLICABLE = {
    "territory": ["feed_health", "restatement", "access", "promotion", "inventory", "competitor", "concentration"],
    "national": ["feed_health", "restatement", "calendar", "concentration", "competitor"],
    "competitor": ["feed_health", "competitor"],
}
# Drivers that must all be tested before a territory story can close at High.
HIGH_REQUIRES = {"territory": ["access", "promotion", "inventory", "competitor"],
                 "national": [], "competitor": ["competitor"]}

# Loop caps (Briefing B-V). Backstops only.
CAPS = {
    "rounds_per_story": 3,
    "checks_per_story": 8,
    "stalls": 2,
    "stories_per_run": 6,
    "run_seconds": 120,
    "checks_per_round": 4,
}

FUNCTIONS_TO_INVOLVE = {
    "access": "Market access",
    "promotion": "Sales operations and marketing",
    "inventory": "Supply chain and trade",
    "competitor": "Sales and marketing",
    "artifact": "Data vendor",
    "calendar": "No one; expect the rebound",
    "unresolved": "Sales leadership, for local context",
}

# Verifier vocabulary (governed terms).
BANNED_TERMS = ["surveillance"]
CAUSAL_WORDS = ["because", "caused", "causes", "due to", "drove", "driven by", "led to", "result of", "resulted in"]
NUMBER_WORDS = ["two", "three", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
                "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
                "million", "percent", "half", "dozen", "quarter"]
NUMBER_WORD_ALLOW = ["four-week"]

PROMPT_VERSION = "agentdemo-v1"
