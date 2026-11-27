"""The promotion verdict a marketer can act on: controls first (not_separable), not testable when activity held level,
new patients first, all four channels at the verdict's lag, the effect against territories without a promotion change,
and the re-check date. Every number is a claim token; both engines share the checks (brief-011 invariants keep holding).

No model is called. The agent's tool calls go through the real MCP session.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api import service  # noqa: E402
from pharmagentics.mcp_server import RunSession  # noqa: E402
from pharmagentics.tools import Registry, stages  # noqa: E402
from pharmagentics.tools.checks import Check, confidence  # noqa: E402
from pharmagentics.tools.events import verdict_of  # noqa: E402
from pharmagentics.tools.lag_checks import check_promotion, run_checks  # noqa: E402
from pharmagentics.tools.memo import story_card  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

needs_db = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
SOUTHEAST = "Week of 2026-10-05 in Southeast: What moved?"
FLAT = "Week of 2025-03-03 in Great Lakes: What moved?"  # promotion activity held level in all four channels
ACCESS = "Week of 2025-09-01 in Mid-Atlantic: What moved?"  # an access change and a calls move in the same weeks
CHANNELS = ["rep calls", "digital impressions", "samples", "speaker programs"]


def _promotion(question, terr, brand="BXA"):
    reg = Registry(service.DB)
    try:
        p = stages.resolve(reg, question, brand)
        check = check_promotion(reg, terr, p.weeks, p.baseline, brand)
        return check, reg.render(check.text), p
    finally:
        reg.close()


@needs_db
def test_a_supported_promotion_states_new_patients_first_the_lag_the_comparison_and_the_recheck_date():
    check, text, p = _promotion(SOUTHEAST, "SOUTHEAST")
    assert check.verdict == "supported" and text.startswith("Promotion: supported as recovery after the promotion lapse of 2026-08-03 to 2026-08-31")
    assert text.index("New patients (NBRx)") < text.index("TRx rose")  # NBRx first, TRx as the follow-through
    assert "Compared with territories without a promotion change" in text and re.search(r"(extra|fewer) TRx a week|a change of", text)
    assert text.endswith("Re-check after 2026-11-02.")  # the last week plus as many weeks as the comparison
    assert "two-week lag" in text
    assert not digits_outside_tokens(check.text) and "ROI" not in text and "attribut" not in text


@needs_db
def test_the_promotion_structure_leads_with_new_patients_and_holds_all_four_channels_and_the_effect():
    check, _, _ = _promotion(SOUTHEAST, "SOUTHEAST")
    d = check.detail["promotion"]
    keys = list(d)
    assert keys.index("new_patients") < keys.index("trx") < keys.index("channels")
    assert [c["channel"] for c in d["channels"]] == CHANNELS
    assert d["new_patients"]["measure"] == "NBRx" and d["trx"]["measure"] == "TRx"
    assert (d["lag"], d["lag_label"], d["recheck"]) == (2, "two-week lag", "2026-11-02")
    assert d["tested"] == ["same week", "one-week lag", "two-week lag"]
    e = d["effect"]
    assert {"low", "high", "territories", "method"} <= set(e) and "SOUTHEAST" not in e["held_level"] and e["held_level"]
    assert all(re.fullmatch(r"\{c\d+\}", v) for v in (e["low"], e["high"], e["territories"]))  # figures are claim tokens
    assert not digits_outside_tokens(json.dumps({k: v for k, v in d.items() if k != "lag"}).replace("2026-11-02", ""))  # nothing but tokens, labels and the date
    assert "rep_vacancy" not in json.dumps(d)  # aggregated channels only; nothing at rep level


@needs_db
def test_effect_claims_carry_the_trx_measure_and_the_new_patients_claims_the_nbrx_measure():
    reg = Registry(service.DB)
    try:
        p = stages.resolve(reg, SOUTHEAST, "BXA")
        check = check_promotion(reg, "SOUTHEAST", p.weeks, p.baseline)
        d = check.detail["promotion"]
        claim = lambda token: reg.claims[int(token[2:-1]) - 1]  # noqa: E731
        assert claim(d["new_patients"]["change"])["labels"]["measure"] == "nbrx"
        assert claim(d["trx"]["change"])["labels"]["measure"] == "trx"
        assert claim(d["effect"]["low"])["labels"]["measure"] == "trx"
        assert float(claim(d["effect"]["low"])["value"].replace(",", "")) <= float(claim(d["effect"]["high"])["value"].replace(",", ""))
    finally:
        reg.close()


@needs_db
def test_activity_that_held_level_is_not_testable_never_ruled_out():
    check, text, _ = _promotion(FLAT, "GREAT_LAKES")
    assert check.verdict == "not_testable"
    assert text.startswith("Promotion: not testable; activity held level, so its effect cannot be measured this period.")
    assert text.endswith("Re-check after 2025-03-31.")
    assert not any(ch["moved"] for ch in check.detail["promotion"]["channels"]) and check.detail["promotion"]["effect"] is None
    assert "lag" not in check.detail  # no driver timing is stated for a promotion that is not a driver of the story


@needs_db
def test_promotion_that_moved_without_trx_following_is_still_ruled_out():
    check, text, _ = _promotion("Week of 2025-03-03 in Mountain: What moved?", "MOUNTAIN")  # samples moved, TRx fell
    assert check.verdict == "ruled_out" and text.startswith("Promotion: ruled out. No tested lag lines up with TRx.")
    assert [ch["channel"] for ch in check.detail["promotion"]["channels"] if ch["moved"]] == ["samples"]
    assert "Samples moved, and TRx did not follow." in text and check.detail["promotion"]["effect"] is None


@needs_db
def test_a_supported_control_makes_promotion_not_separable_and_it_is_in_neither_driver_list():
    check, text, p = _promotion(ACCESS, "MID_ATLANTIC")
    assert check.verdict == "not_separable"
    assert text.startswith("Promotion: cannot be separated from access in these weeks.")
    assert check.detail["promotion"]["separable_from"] == ["access"] and "lag" not in check.detail
    reg = Registry(service.DB)
    try:
        checks = run_checks(reg, "MID_ATLANTIC", p.weeks, p.baseline)
        by = {c.driver: c for c in checks}
        assert by["access"].verdict == "supported" and by["promotion"].verdict == "not_separable"
        level, lead = confidence(checks)
        assert level == "Medium" and lead.startswith("access; promotion cannot be separated from access")
        card = story_card("Mid-Atlantic", {"word": "up", "pct": "{c1}"}, level, [c.driver for c in checks], territory="MID_ATLANTIC", checks=checks)
        assert card["drivers_supported"] == ["access"] and "promotion" not in card["drivers_ruled_out"]
        assert card["promotion"]["verdict"] == "not_separable" and card["promotion"]["separable_from"] == ["access"]
    finally:
        reg.close()


def test_confidence_never_leads_with_a_driver_promotion_cannot_be_separated_from():
    tangled = Check("promotion", "not_separable", "", {"promotion": {"separable_from": ["competitor"]}})
    out = confidence([Check("data", "ruled_out", ""), Check("competitor", "supported", ""), tangled, Check("supply", "ruled_out", "")])
    assert out == ("Medium", "competitor; promotion cannot be separated from competitor")
    flat = Check("promotion", "not_testable", "")  # a promotion that did not move is no competing explanation
    assert confidence([Check("access", "supported", ""), flat, Check("supply", "ruled_out", "")])[0] == "High"
    assert confidence([flat, Check("access", "insufficient", "")]) == ("Low", "unresolved, investigate next")


def test_the_events_log_reads_the_two_new_verdicts_as_inconclusive():
    assert verdict_of("check_promotion", "Promotion: cannot be separated from access in these weeks. ...") == "inconclusive"
    assert verdict_of("check_promotion", "Promotion: not testable; activity held level, so its effect cannot be measured this period.") == "inconclusive"


@needs_db
def test_the_scripted_brief_card_has_the_promotion_data_filled_and_the_detail_folds_the_channels():
    from briefing_baseline.pipeline import answer

    from pharmagentics.tools.window import Comparison

    # Southeast in the lapse week against the July weeks (WIN-2's reading): material, and promotion is supported.
    env = answer("Week of 2026-08-24, Southeast: How did BXA TRx move, and why?",
                 comparison=Comparison(kind="custom", start="2026-07-06", end="2026-07-27"))
    section = next(s for s in env["sections"] if s["number"] == "3.1")
    card = section["card"]
    assert card["drivers_supported"] == ["promotion"] and card["promotion"]["verdict"] == "supported"
    assert "{c" not in json.dumps(card["promotion"])  # tokens are filled in the card's structured data
    assert card["promotion"]["recheck"] == "2026-09-21"
    assert "during the promotion lapse of 2026-08-03 to 2026-08-31" in env["answer"] and "fewer TRx a week" in env["answer"]
    for label in ("New patients (NBRx)", "Rep calls", "Digital impressions", "Samples", "Speaker programs", "A fuller read is possible after 2026-09-21"):
        assert label in section["detail"]
    assert section["detail"].index("New patients (NBRx):") < section["detail"].index("- TRx:")
    assert "promotion change" in env["answer"] and "Promotion: controls first, then comparable territories." in env["answer"]  # the Assumptions line
    # The mentor's week (REV-1): within its normal range, so the card credits nothing and states no effect (brief-011 I6).
    mentor = next(s for s in answer(SOUTHEAST)["sections"] if s["number"] == "3.1")["card"]
    assert mentor["drivers_supported"] == [] and mentor["promotion"]["verdict"] == "within_range" and mentor["promotion"]["effect"] is None


@needs_db
def test_the_agents_promotion_check_equals_the_scripted_check_whatever_order_it_is_called_in():
    """I5: the MCP tool calls the same check. The controls are read inside it, so calling it before access changes nothing."""
    for brand in ("BXA", "BXC"):
        reg = Registry(service.DB)
        try:
            p = stages.resolve(reg, SOUTHEAST, brand)
            scripted = {c.driver: reg.render(stages.credit_rule(reg, p, "SOUTHEAST", c).text)  # the story's own rule (I6)
                        for c in run_checks(reg, "SOUTHEAST", p.weeks, p.baseline, brand_id=brand)}
        finally:
            reg.close()
        s = RunSession()
        try:
            s.open_run(SOUTHEAST, brand_id=brand)
            s.check_promotion("SOUTHEAST")  # first, before access and competitor
            s.check_access("SOUTHEAST")
            s.check_competitor("SOUTHEAST")
            assert s.reg.render(s.checks["SOUTHEAST"]["promotion"].text) == scripted["promotion"], brand
            # BXA: supported, then not credited, as Southeast moved within its normal range (REV-1); BXC: ruled out.
            assert s.checks["SOUTHEAST"]["promotion"].detail["promotion"]["verdict"] == ("within_range" if brand == "BXA" else "ruled_out")
        finally:
            s.close()


@needs_db
def test_the_agent_story_card_carries_the_promotion_data_and_the_not_separable_verdict_stays_off_the_lists():
    s = RunSession()
    try:
        s.open_run(ACCESS)
        for tool in (s.check_data, s.check_access, s.check_promotion, s.check_supply, s.check_competitor):
            tool("MID_ATLANTIC")
        s.story_section("MID_ATLANTIC", 1)
        assert any("Promotion detail" in line for line in s.story_detail["MID_ATLANTIC"])
        done = list(s.checks["MID_ATLANTIC"].values())
        card = story_card("Mid-Atlantic", s.story_facts["MID_ATLANTIC"], "Medium", [c.driver for c in done], territory="MID_ATLANTIC", checks=done)
        assert card["promotion"]["verdict"] == "not_separable"
        assert "promotion" not in card["drivers_supported"] + card["drivers_ruled_out"]
        assert "cannot be separated" in s.checks["MID_ATLANTIC"]["promotion"].text
    finally:
        s.close()
