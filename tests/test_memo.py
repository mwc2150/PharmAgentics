"""brief-003 slice 1: the memo outline (User Story 2, FR-004, FR-020, FR-021), restatements and next checks in
the memo (User Story 4), and the leadership cut (FR-026). Runs the real scripted engine; no model."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api.views import executive_summary  # noqa: E402
from pharmagentics.tools import DEFAULT_DB  # noqa: E402
from pharmagentics.tools.memo import HEADINGS, MemoParts, StoryBlock, compose  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
ROUTINE, WITHHELD, EVENTFUL, RESTATED = "2025-04-21", "2026-05-04", "2026-08-24", "2026-07-13"


def brief(week: str, territory: str | None = None) -> dict:
    from briefing_baseline import answer

    return answer(f"Week of {week}" + (f" in {territory}" if territory else "") + ": Generate the weekly brand-performance briefing.")


def section(text: str, title: str) -> list[str]:
    lines, out, inside = text.splitlines(), [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:] == title
            continue
        if inside:
            out.append(line)
    return out


def _parts(**kw) -> MemoParts:
    base = dict(title=["Brief."], bottom_line=["National {c1}."], numbers=["Table {c2}."], limits=[],
                next_checks=[], appendix=["Method."])
    return MemoParts(**{**base, **kw})


def test_composition_is_pure_and_keeps_the_outline():
    parts = _parts(stories=[StoryBlock("territory:PACIFIC", "Pacific", ["Story one: Pacific {c3}.", "Confidence: High."], "Supply fell.")],
                   story_notes=["Considered and dropped: {c4} territories moved within their normal range."], answer="It fell.")
    first, second = compose(parts), compose(parts)
    assert first == second
    template, sections = first
    assert [x for x in template.splitlines() if x.startswith("## ")] == [f"## {t}" for _, t in HEADINGS]
    assert [s["number"] for s in sections] == ["1", "2", "3", "3.1", "4", "5", "6"]
    lines = template.splitlines()
    assert lines[lines.index("Story one: Pacific {c3}.") + 1] == "Supply fell."  # the story's prose sits under its head
    assert section(template, "What the data can't tell us") == ["Nothing in this period limits the figures above."]
    assert section(template, "Next checks") == ["No check is open."]


@needs_db
@pytest.mark.parametrize("week", [ROUTINE, WITHHELD, EVENTFUL])
def test_every_brief_is_the_six_section_memo(week):
    env = brief(week)
    text = env["answer"]
    assert [x for x in text.splitlines() if x.startswith("## ")] == [f"## {t}" for _, t in HEADINGS]
    assert not re.search(r"\{c\d+\}", text)
    assert [s["number"] for s in env["sections"]][:3] == ["1", "2", "3"] and env["sections"][-1]["number"] == "6"
    for s in env["sections"]:  # every claim a section cites is one of the envelope's claims
        assert all(0 <= i < len(env["claims"]) for i in s["claims"])


@needs_db
@pytest.mark.parametrize("week", [ROUTINE, WITHHELD, EVENTFUL, RESTATED])
def test_no_digit_outside_a_claim(week):
    from briefing_baseline.pipeline import Registry, _brief  # the template before rendering

    reg = Registry()
    try:
        captured = {}
        import pharmagentics.tools.memo as memo

        real = memo.compose
        memo.compose = lambda parts: captured.setdefault("t", real(parts))
        try:
            _brief(reg, f"Week of {week}: Generate the weekly brand-performance briefing.")
        finally:
            memo.compose = real
        assert digits_outside_tokens(captured["t"][0]) == []
    finally:
        reg.close()


@needs_db
def test_bottom_line_order_on_the_withheld_week():
    bottom = section(brief(WITHHELD)["answer"], "Bottom line")
    assert bottom[0].startswith("Data warning: New England's feed for 2026-05-04 is incomplete")
    assert bottom[1] == "Projected national BXA TRx is 4,491 for the week of 2026-05-04."
    assert bottom[2] == ("Like for like on 6 of 8 territories, BXA TRx is down 5.2% against the four weeks before "
                         "(2026-04-06 to 2026-04-27).")  # brief-007 FR-004: the comparison weeks are named
    assert bottom[3].startswith("BXA held ") and bottom[3].endswith("of the four-brand market basket.")
    assert bottom[4] == "Least sure: New England's TRx of 407 is an assumption, projected from panel coverage of 0.656."


@needs_db
@pytest.mark.parametrize("week, territory", [(WITHHELD, "New England"), ("2026-07-06", "Great Lakes"), ("2026-04-06", "Mid-Atlantic")])
def test_every_projected_or_estimated_level_is_flagged_as_an_assumption(week, territory):
    """FR-022 (Michael, 2026-11-20): a level the feed did not deliver is always called an assumption."""
    text = brief(week)["answer"]
    row = next(x for x in section(text, "The numbers") if x.startswith(f"{territory}:"))  # the folded level line
    assert "an assumption" in row
    assert "an assumption" in section(text, "Bottom line")[0]  # the data warning
    assert any(x.startswith("Assumption:") for x in section(text, "What the data can't tell us"))


@needs_db
def test_least_sure_falls_to_the_lowest_confidence_story_then_the_smallest_change():
    restated = section(brief(RESTATED)["answer"], "Bottom line")
    assert ("Least sure: the Pacific change (up 45%); its confidence, Low, is the lowest of this brief's stories."
            in restated)
    routine = section(brief(ROUTINE)["answer"], "Bottom line")
    assert any(x.startswith("Least sure: the week-over-week change") for x in routine)
    numbers = section(brief(ROUTINE)["answer"], "The numbers")
    levels = [x for x in numbers if re.match(r"[A-Z][A-Za-z\- ]+: [\d,]+ BXA TRx a week", x)]  # the folded level lines
    assert len(levels) == 8 and not any("(projected" in x or "(estimated" in x for x in levels)  # nothing marked
    assert len([x for x in levels if "on the week before" in x]) == 8  # brief-007 FR-007: one change line per territory


@needs_db
def test_restatement_reaches_the_numbers_and_the_bottom_line():
    text = brief(RESTATED)["answer"]
    assert "Data note: an earlier week was restated." in section(text, "Bottom line")[0]
    assert any(x.startswith("Restated: Mid-Atlantic BXA TRx for the week of 2026-04-06 was 692 when first reported and is now 742")
               for x in section(text, "The numbers"))


@needs_db
def test_next_checks_name_an_owner_and_a_decision():
    checks = section(brief(RESTATED)["answer"], "Next checks")
    assert checks[0].startswith("- Pacific: split by plan and specialty") and "Owner: sales leadership." in checks[0]
    assert checks[-1].startswith("- Metacora:") and "Owner: marketing and sales." in checks[-1]
    assert all("Unlocks: " in x for x in checks)
    assert not any("Next:" in x for x in section(brief(RESTATED)["answer"], "What changed and why"))


@needs_db
def test_leaders_get_bottom_line_numbers_stories_without_checks_and_next_checks():
    text = brief(RESTATED)["answer"]
    env = brief(RESTATED)
    summary = executive_summary(text, env["sections"])
    heads = [x for x in summary.splitlines() if x.startswith("## ")]
    assert heads == ["## Bottom line", "## The numbers", "## What changed and why", "## What the data can't tell us",
                     "## Next checks", "## Assumptions"]  # brief-008 FR-005: a short limits paragraph, the Assumptions
    assert "Checked, in this order:" not in summary and "Considered and dropped" not in summary
    assert not any(x in summary for x in ("Data version", "Method:", "Glossary", "Cuts of the change", "Feed for "))
    assert "Restated: Mid-Atlantic" in summary and "- Comparison weeks:" in summary
    assert len(section(summary, "What the data can't tell us")) == 1  # the first paragraph only


def test_a_brief_from_before_the_memo_is_cut_as_before():
    old = "Brief.\nKPIs: x.\nStory one: P.\nChecked, in this order:\n- Supply: supported.\nConfidence: High.\nConsidered and dropped: y."
    assert executive_summary(old) == "Brief.\nKPIs: x.\nStory one: P.\nConfidence: High."


# --- brief-007 slice A: windows named, per-territory changes, feed figures, Assumptions block ---------------

SOUTHEAST_GAP = "Weeks of 2026-08-03 to 2026-08-31, Southeast: What should I do, and who should I loop in?"


@needs_db
def test_a_multi_week_window_compares_with_the_four_weeks_before():
    """FR-001, SC-005: the P3-Q5 window is compared with 2026-07-06 to 2026-07-27, so Southeast's baseline is 639."""
    from briefing_baseline import answer

    text = answer(SOUTHEAST_GAP)["answer"]
    assert "Southeast. BXA TRx averaged 481 a week against 639 before (down 25%)" in text
    bottom = section(text, "Bottom line")
    assert bottom[0].startswith("Southeast: BXA TRx is down 25% against the four weeks before (2026-07-06 to 2026-07-27).")  # 3.7
    assert "against the four weeks before (2026-07-06 to 2026-07-27)." in bottom[2]


@needs_db
@pytest.mark.parametrize("brand_id", ["BXA", "BXC"])
def test_screening_uses_common_reportable_weeks_in_the_longer_comparison(brand_id):
    from pharmagentics.tools import queries, stages
    from pharmagentics.tools.registry import Registry

    reg = Registry()
    try:
        p = stages.resolve(reg, "What changed from 2026-06-08 to 2026-07-13?", brand_id=brand_id)
        details = {}
        stages.screen(reg, p, details)

        # New England is withheld on May 4, so every territory's screening comparison drops that week.
        expected_weeks = ["2026-04-27", *p.baseline]
        for territory in ("NEW_ENGLAND", "PACIFIC"):
            actual = queries.mean_weekly(p.weeks, terrs=[territory], product=brand_id)
            baseline = queries.mean_weekly(expected_weeks, terrs=[territory], product=brand_id)
            expected = reg.scalar(queries.pct_change(actual, baseline)) / 100
            assert details[territory]["change"] == pytest.approx(expected)
    finally:
        reg.close()


@needs_db
def test_scope_line_and_assumptions_name_the_comparison_weeks():
    """FR-004, FR-012: leaders keep the scope line; the Assumptions block closes the Appendix."""
    text = brief(WITHHELD)["answer"]
    numbers = section(text, "The numbers")
    assert numbers[0] == ("Scope: week of 2026-05-04, compared with the four weeks before (2026-04-06 to 2026-04-27). "
                          "Levels marked projected or estimated are assumptions.")
    appendix = section(text, "Appendix")
    i = appendix.index("Assumptions:")
    assert appendix[i + 1].startswith("- Comparison weeks: the four weeks before (2026-04-06 to 2026-04-27).")
    assert any(x.startswith("- Not observed: New England is projected or estimated") for x in appendix[i:])
    assert not digits_outside_tokens("\n".join(appendix[i:]).replace("2026-04-06", "").replace("2026-04-27", ""))


@needs_db
def test_territory_changes_match_the_golden_swings():
    """FR-007 (P1-Q3): each territory's week-over-week change, with its direction."""
    numbers = section(brief(ROUTINE)["answer"], "The numbers")
    assert any(x.startswith("Pacific: ") and x.endswith("up 25% on the week before; up 8.4% on the comparison weeks.") for x in numbers)
    assert any(x.startswith("Southeast: ") and x.endswith("down 11% on the week before; down 16% on the comparison weeks.") for x in numbers)


@needs_db
def test_feed_figures_carry_the_floor_target_and_comparison_range():
    """FR-009 (P1-Q2): coverage against the gate floor, lateness against its target, and the comparison range."""
    limits = section(brief(WITHHELD)["answer"], "What the data can't tell us")
    joined = "\n".join(limits)
    assert "panel coverage 0.656 against a 0.98 floor, 10.29 days after week end against a target of 7 days" in joined
    assert "New England's observed BXA TRx ranged from 397 to 422 a week in the comparison weeks" in joined
    focus = section(brief(WITHHELD, "New England")["answer"], "What the data can't tell us")
    assert any(x.startswith("Feed for New England in these weeks: 84 rows received against 128 expected") for x in focus)


@needs_db
def test_bxc_memo_uses_the_selected_brand_for_withheld_cut_evidence():
    from briefing_baseline import answer

    result = answer(f"Week of {WITHHELD} in New England: What changed?", brand_id="BXC")
    assert "New England's observed BXC TRx ranged from" in result["answer"]
    assert "Product: BXC (Lipidara), synthetic data." in result["answer"]
    assert any("product_id = 'BXC'" in e["query"] and "select min(s)" in e["query"] for e in result["evidence"])
    assert not any("product_id = 'BXA'" in e["query"] for e in result["evidence"])


# --- brief-008: the blocks, the paragraphs, the folded detail ---------------------------------------------------

RAW_ID = re.compile(r"\bSYN_|\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")  # SYN_GREAT_LAKES_MEDICARE_PART_D_1, PRIMARY_CARE
SIGNED = re.compile(r"(?<![\w.-])-\d[\d,]*\.\d+")  # -158.40
PLURAL_SLIP = re.compile(r"\b1 (?:weeks|territories|territory-weeks)\b")
ANCHORS = [f"Week of {ROUTINE}: Generate the weekly brand-performance briefing.",
           f"Week of {WITHHELD}: Generate the weekly brand-performance briefing.",
           f"Week of {EVENTFUL}: Generate the weekly brand-performance briefing.",
           f"Week of {RESTATED}: Generate the weekly brand-performance briefing.", SOUTHEAST_GAP,
           "Weeks of 2026-06-01 to 2026-06-29, Pacific: Why did BXA prescriptions fall?"]


def built(question: str) -> tuple[str, list[dict], dict]:
    """The template and unrendered sections of one scripted brief, with its envelope."""
    from briefing_baseline.pipeline import Registry, _brief

    import pharmagentics.tools.memo as memo

    reg, captured, real = Registry(), {}, memo.compose
    memo.compose = lambda parts: captured.setdefault("t", real(parts))
    try:
        env = _brief(reg, question)
    finally:
        memo.compose = real
        reg.close()
    return captured["t"][0], captured["t"][1], env


def by_number(env: dict) -> dict[str, dict]:
    return {s["number"]: s for s in env["sections"]}


def _tokens(*texts) -> set[str]:
    return {t for x in texts for t in re.findall(r"\{c\d+\}", x or "")}


def _block_strings(s: dict) -> list[str]:
    out = [f"{k['value']} {k.get('detail') or ''}" for k in s.get("kpis", [])]
    if s.get("territory_table"):
        out += [c for r in s["territory_table"]["rows"] for c in r["cells"]] + [s["territory_table"].get("note") or ""]
    if s.get("card"):
        out.append(s["card"]["headline"])
    return out


@needs_db
@pytest.mark.parametrize("question", ANCHORS)
def test_every_block_number_is_in_the_scored_answer(question):
    """FR-002: a token used in a block also appears in the section's text or detail, so the answer keeps every claim."""
    template, sections, _env = built(question)
    for s in sections:
        shown = _tokens("\n".join(s["lines"]), s["prose"], s.get("detail"), (s.get("chart") or {}).get("caption"),
                        (s.get("chart") or {}).get("explanation"))
        assert _tokens(*_block_strings(s)) <= shown, s["number"]
    assert _tokens(template) >= _tokens(*[x for s in sections for x in _block_strings(s)])
    assert digits_outside_tokens(template) == []


@needs_db
def test_blocks_follow_the_schema_for_a_one_week_brief():
    env = brief(EVENTFUL)
    one, two = by_number(env)["1"], by_number(env)["2"]
    assert [k["label"] for k in one["kpis"]] == ["National BXA TRx", "Change on the comparison weeks", "BXA basket share", "Territories reportable"]
    assert [k["direction"] for k in one["kpis"]] == [None, "down", "down", None]
    assert one["kpis"][0]["value"] == "4,105" and one["kpis"][1]["value"] == "4.4%" and one["kpis"][3]["value"] == "8"
    assert all(k["value_citation"] and not re.search(r"\{c\d+\}", k["value"] + (k["detail"] or "")) for k in one["kpis"])
    table = two["territory_table"]
    assert table["columns"] == ["Territory", "BXA TRx", "On the week before", "On the comparison weeks", "Basis"]
    assert [r["cells"][0] for r in table["rows"]][:2] == ["Great Lakes", "Mid-Atlantic"] and len(table["rows"]) == 8
    assert table["rows"][0]["cells"] == ["Great Lakes", "556", "down 12%", "down 13%", "observed"]
    assert all(len(r["cells"]) == len(table["columns"]) == len(r["cell_citations"]) for r in table["rows"])
    assert table["rows"][0]["cell_citations"][0] == [] and len(table["rows"][0]["cell_citations"][1]) == 1
    assert "four weeks before" in table["note"]
    southeast = by_number(env)["3.1"]["card"]  # brief-010 FR-012: the Southeast lapse, still running on 2026-08-24, comes first
    assert (southeast["territory"], southeast["continuing"], southeast["drivers_supported"]) == ("SOUTHEAST", True, ["promotion"])
    story = next(s for n, s in by_number(env).items() if n.startswith("3.") and (s.get("card") or {}).get("territory") == "NATIONAL")
    assert story["card"]["confidence"] == "Medium" and story["card"]["drivers_checked"][0] == "competitor"  # the competitor story
    assert "Metacora holds 16%" in story["card"]["headline"] and story["card"]["headline_citations"]
    card = story["card"]  # brief-010 FR-006: the national card
    assert (card["territory"], card["cut"], card["drivers_supported"]) == ("NATIONAL", None, ["competitor"])
    assert set(card["drivers_ruled_out"]) <= {"access", "promotion", "supply"}  # only drivers every territory rules out (packet N)
    assert card["drivers_checked"] == ["competitor"] + card["drivers_ruled_out"]
    assert card["direction"] == card["directions"]["bxa_share"] in ("up", "down", "flat")
    assert "detail" in by_number(env)["6"] and "Glossary" in by_number(env)["6"]["detail"]


@needs_db
def test_a_multi_week_brief_quotes_no_single_week_change():
    """FR-011: no 'week before' change in the table, the lines or the detail of a multi-week period."""
    template, sections, env = built(SOUTHEAST_GAP)
    assert "On the week before" not in by_number(env)["2"]["territory_table"]["columns"]
    assert "on the week before" not in env["answer"] and "Week over week" not in env["answer"]
    card = by_number(env)["3.1"]["card"]
    assert card["headline"].startswith("Southeast fell 25% on the comparison weeks, while the other territories were up 2.8%")
    assert card["drivers_checked"] == ["data quality", "access", "promotion", "supply", "competitor"]
    # core-011: territory id, own direction and the drivers the checks supported and ruled out, in the eval's ids
    assert (card["territory"], card["direction"]) == ("SOUTHEAST", "down")
    assert card["drivers_supported"] == ["promotion"] and card["drivers_ruled_out"] == ["data", "access", "supply", "competitor"]


@needs_db
@pytest.mark.parametrize("question", ANCHORS)
def test_paragraphs_have_no_raw_ids_signed_decimals_or_long_lists(question):
    env = built(question)[2]
    for s in env["sections"]:
        shown = "\n".join([s["text"], s["prose"], s.get("detail") or "", *_block_strings(s)])
        assert not RAW_ID.findall(shown), (s["number"], RAW_ID.findall(shown))
        assert not SIGNED.findall(shown) and not PLURAL_SLIP.findall(shown), (s["number"], shown)
        run = 0
        for line in s["text"].splitlines():  # no list of more than five items in the visible text
            run = run + 1 if line.startswith("- ") else 0
            assert run <= 5, (s["number"], line)
    assert not RAW_ID.findall(env["answer"].replace("Product:", ""))


@needs_db
def test_the_splits_are_readable_rounded_and_folded():
    story = by_number(brief(SOUTHEAST_GAP))["3.1"]
    assert "Cuts of the change" not in story["text"] and "Cuts of the change by plan" in story["detail"]
    assert "- Commercial plan one: down 48 TRx a week." in story["detail"]
    assert "- Internal medicine: down 52 TRx a week." in story["detail"] and "(small cell: noisy)" in story["detail"]
    assert story["detail_citations"] and all(story["detail"][c["start"]:c["end"]] for c in story["detail_citations"])


@needs_db
def test_old_sections_without_blocks_render_as_before():
    from pharmagentics.tools.memo import render_sections

    old = [{"number": "1", "title": "Bottom line", "lines": ["A {c1}."], "prose": ""}]
    out = render_sections(old, [{"value": "5", "evidence_id": "e1"}])
    assert out[0]["text"] == "A 5." and not {"kpis", "territory_table", "card", "detail"} & set(out[0])


@needs_db
def test_a_supply_story_card_names_the_supported_driver_and_what_was_ruled_out():
    from briefing_baseline import answer

    env = answer("Weeks of 2026-06-01 to 2026-06-29, Pacific: Why did BXA prescriptions fall?")
    card = by_number(env)["3.1"]["card"]
    assert (card["territory"], card["direction"]) == ("PACIFIC", "down")
    assert card["drivers_supported"] == ["supply"] and card["drivers_ruled_out"] == ["data", "access", "competitor"]
    assert card["promotion"]["verdict"] == "not_testable"  # Pacific held its promotion level: not ruled out, not testable


def test_card_driver_lists_use_the_evals_ids_and_leave_inconclusive_checks_out():
    from pharmagentics.tools.checks import Check
    from pharmagentics.tools.memo import competitor_card, story_card

    facts = {"pct": "{c1}", "word": "down", "peer_pct": "{c2}", "peer_word": "up"}
    checks = [Check("data", "ruled_out", ""), Check("access", "supported", ""), Check("promotion", "insufficient", ""),
              Check("supply", "ruled_out", ""), Check("competitor", "insufficient", "")]
    card = story_card("Pacific", facts, "High", [c.driver for c in checks], territory="PACIFIC", checks=checks)
    assert card["drivers_checked"] == ["data quality", "access", "promotion", "supply", "competitor"]  # display names, unchanged
    assert card["territory"] == "PACIFIC" and card["direction"] == "down"
    assert card["drivers_supported"] == ["access"] and card["drivers_ruled_out"] == ["data", "supply"]
    assert not re.search(r"\d", repr({k: card[k] for k in ("territory", "direction", "drivers_supported", "drivers_ruled_out")}))
    bare = competitor_card(type("P", (), {"brand_id": "BXA"})(), {"bxe": "{c3}", "bxa": "{c4}"})
    assert bare["territory"] == "NATIONAL" and bare["drivers_supported"] == [] and bare["drivers_ruled_out"] == []


NATIONAL_ANCHORS = {  # the dev anchors: (question, BXA share, Metacora share, drivers ruled out in every story territory)
    "P3-Q1": ("Week of 2026-04-27: What changed this week that I need to know about?", "flat", "up", ["access", "promotion", "supply"]),
    "P3-Q4": ("Week of 2026-09-28: Is this new or the same issue as last week, and is it getting better or worse?", "up", "flat", ["access", "supply"]),
    "P1-Q5": ("Week of 2026-06-08: Am I confident nothing material was left out?", "down", "up", ["access", "promotion"]),
}


def _national_cards(env: dict) -> list[dict]:
    return [s["card"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card") and s["card"].get("territory") == "NATIONAL"]


@needs_db
@pytest.mark.parametrize("anchor", sorted(NATIONAL_ANCHORS))
def test_the_competitor_story_is_one_national_card_with_a_direction_for_each_measure(anchor):
    from briefing_baseline import answer

    question, bxa, bxe, ruled_out = NATIONAL_ANCHORS[anchor]
    env = answer(question)
    (card,) = _national_cards(env)  # at most one a brief
    assert card["cut"] is None and card["drivers_supported"] == ["competitor"]
    assert card["drivers_ruled_out"] == ruled_out  # from the territory checks, by code (P1-Q5: supply is live in Pacific)
    assert card["drivers_checked"] == ["competitor"] + [{"promotion": "promotion"}.get(d, d) for d in ruled_out]
    assert {k: v for k, v in card["directions"].items() if k != "trx"} == {"bxa_share": bxa, "competitor_share": bxe}
    assert card["directions"]["trx"] in ("up", "down", "flat") and card["direction"] == bxa  # share story first; national TRx beside it (packet NC)
    assert not re.search(r"\{c\d+\}", card["headline"]) and card["headline_citations"]  # filled, and every number cited
    assert re.search(r"Metacora holds \d+(?:\.\d)?% of the four-brand basket, and BXA holds \d+(?:\.\d)?%\.", card["headline"])  # whole from 10%, one decimal below (brief-008 FR-016)


@needs_db
def test_the_national_card_reaches_a_leader_as_its_headline_and_verdicts_only():
    from briefing_baseline import answer
    from pharmagentics.api.views import leadership_sections

    env = answer(NATIONAL_ANCHORS["P3-Q4"][0])
    seen = [s["card"] for s in leadership_sections(env["sections"]) if s.get("card") and s["card"]["territory"] == "NATIONAL"]
    assert len(seen) == 1 and "directions" not in seen[0] and seen[0]["headline"] and seen[0]["confidence"] == "Medium"
    assert seen[0]["drivers_supported"] == ["competitor"]


def test_the_national_card_states_a_ruled_out_competitor_and_keeps_its_headline():
    from pharmagentics.tools.checks import Check
    from pharmagentics.tools.memo import competitor_card

    p = type("P", (), {"brand_id": "BXA"})()
    out = competitor_card(p, {"bxe": "{c1}", "bxa": "{c2}", "check": Check("competitor", "ruled_out", ""),
                              "directions": {"bxa_share": "flat", "competitor_share": "flat"}})
    assert out["drivers_supported"] == [] and out["drivers_ruled_out"] == ["competitor"] and out["direction"] == "flat"
    assert out["headline"] == "Metacora holds {c1} of the four-brand basket, and BXA holds {c2}."
