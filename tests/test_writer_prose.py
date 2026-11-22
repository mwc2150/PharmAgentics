"""brief-008 packet W: the agent Writer's paragraphs. Prose checks (short sentences, one paragraph, no raw IDs, no
spelled-out numbers, no cause below High, nothing from the folded detail), the Writer's view of the memo, the prompts,
and the whole `_write` step with stubbed replies. No model is called."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api import service  # noqa: E402
from pharmagentics.mcp_server import RunSession  # noqa: E402

needs_db = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
Q = "Weeks of 2026-08-03 to 2026-08-31, Southeast: What should I do, and who should I loop in?"
GOOD_STORY = "Southeast sold less than before. Calls to its prescribers moved with the drop. That is an association, not proof."


def problems(piece, allowed=frozenset({"{c1}", "{c2}"}), **kw):
    from briefing_agent import write

    return write.problems(piece, set(allowed), 5, **kw)


def test_a_short_plain_paragraph_passes():
    assert problems("Southeast fell {c1}. Calls were lower in the same weeks, which fits the drop.") == []


@pytest.mark.parametrize("piece, fragment", [
    ("- Southeast fell {c1}.\n- Calls were lower.", "list"),
    ("Southeast fell {c1}.\nCalls were lower.", "list"),
    ("**Southeast** fell {c1}.", "list"),
    ("Southeast fell, so SYN_GREAT_LAKES_MEDICARE_PART_D_1 matters.", "raw IDs"),
    ("The cut by PRIMARY_CARE moved most.", "raw IDs"),
    ("territory:SOUTHEAST fell {c1}.", "raw IDs"),
    ("SOUTHEAST fell {c1}.", "raw IDs"),
    ("primary_care fell {c1}.", "raw IDs"),
    ("Southeast fell by half.", "spells out"),
    ("Two territories fell {c1}.", "spells out"),
    ("Southeast fell {c1} percent.", "spells out"),
    ("Rep Smith made fewer calls.", "rep"),
    ("The split by plan shows Commercial down.", "folded"),
    ("Six territories moved within their normal range (considered and dropped).", "folded"),
    ("The method divides TRx by coverage. Method: see the appendix.", "folded"),
])
def test_prose_rules_reject(piece, fragment):
    found = problems(piece)
    assert any(fragment in p for p in found), found


def test_words_that_code_writes_are_not_spelled_out_numbers():
    assert problems("Against {cmp}, the week of 2026-08-03 fell {c1} in the four-brand basket.") == []


def test_long_sentences_and_long_paragraphs_are_rejected():
    long = " ".join(["word"] * 26) + "."
    assert any("26 words" in p for p in problems(long))
    assert problems(" ".join(["word"] * 25) + ".") == []
    assert any("5 sentences" in p for p in problems("A b. C d. E f. G h. I j.", max_sentences=4))


def test_causal_words_need_a_high_confidence_story():
    from briefing_agent import write

    tokens = {"territory:SOUTHEAST": {"{c1}"}, "_sections": {"{c2}"}}
    reply = {"answer": "Fine overall.", "stories": {"territory:SOUTHEAST": "Southeast fell {c1} because calls dropped."}}
    assert "territory:SOUTHEAST" in write.check(reply, tokens, 2, confidences={"territory:SOUTHEAST": "Medium"})
    assert write.check(reply, tokens, 2, confidences={"territory:SOUTHEAST": "High"}) == {}
    assert write.check(reply, tokens, 2) == {}  # no confidences given: the check is skipped, as before
    caused = {"answer": "Calls caused the fall.", "stories": {}}
    assert "answer" in write.check(caused, tokens, 2, confidences={"territory:SOUTHEAST": "Medium"})
    assert "answer" in write.check(caused, {"_sections": set()}, 2, confidences={})  # no story: no cause either
    assert write.check(caused, tokens, 2, confidences={"territory:SOUTHEAST": "High"}) == {}
    assert write.check({"answer": "That is an association, not a cause."}, tokens, 2, confidences={"territory:SOUTHEAST": "Low"}) == {}


def test_confidence_is_read_from_the_stories_own_line():
    from briefing_agent import write

    assert write.confidence("Story one.\nConfidence for Southeast: Medium. Candidate drivers: promotion.") == "Medium"
    assert write.confidence("Story two: competitor Metacora. Confidence: High. The share loss is measured.") == "High"
    assert write.confidence("No driver was tested before the cap.") is None


def test_chart_lines_follow_the_same_prose_rules():
    from briefing_agent import write

    close = {"charts": {"2": {"caption": "BXA TRx a week.", "explanation": "It moved from {c1} to {c2}."}}}
    kept, dropped = write.chart_explanations({"charts": {"2": "- It moved from {c1} to {c2}."}}, close, [], 2)
    assert kept == {} and "list" in dropped[0]
    kept, dropped = write.chart_explanations({"charts": {"2": "It moved from {c1} to {c2}."}}, close, [], 2)
    assert kept == {"2": "It moved from {c1} to {c2}."} and dropped == []


def test_prompts_fill_and_describe_the_new_memo():
    here = ROOT / "agents" / "brand-briefing" / "briefing_agent" / "prompts"
    writer = (here / "writer.md").read_text(encoding="utf-8").format(question="q", sections="[story x]", glossary="g", comparison="c")
    revise = (here / "revise.md").read_text(encoding="utf-8").format(problems="p", allowed="a", glossary="g", reply="{}")
    for needle in ("association", "folded", "tiles", "territory table", "card", "at most 25 words", "no line breaks"):
        assert needle in writer
    for needle in ("association", "folded", "at most 25 words", "no line breaks"):
        assert needle in revise
    assert '"answer"' in writer and '"stories"' in writer and '"charts"' in writer


@pytest.fixture
def brief():
    s = RunSession()
    s.open_run(Q)
    sec = s.brief_sections()
    for check in (s.check_data, s.check_access, s.check_promotion, s.check_supply, s.check_competitor):
        check("SOUTHEAST")
    stories = [{"id": "territory:SOUTHEAST", "n": 1, "section": s.story_section("SOUTHEAST", 1), "territory": "SOUTHEAST"},
               {"id": "competitor:BXE", "n": 2, "section": s.competitor_section("Story two: competitor Metacora")}]
    close = s.memo_close(competitor=True)
    yield s, sec, close, stories
    s.close()


@needs_db
def test_the_writer_sees_the_tiles_and_the_table_but_no_folded_detail(brief):
    from briefing_agent import write

    s, sec, close, stories = brief
    shown = write.sections_text(sec, close, stories)
    assert "[figure tiles" in shown and "National BXA TRx: " in shown and "[territory table" in shown
    for folded in ("Cuts of the change", "Considered and dropped", "Glossary", "Method:"):
        assert folded not in shown
    tiles = write.tokens(shown.split("[the numbers]")[0])
    assert tiles <= write.section_tokens(sec, close)  # every token the tiles show may be used in the answer


def _run_write(monkeypatch, brief, replies):
    """Run the Writer step with `replies` for the writer, then the reviser."""
    import briefing_agent as agent
    from briefing_lowcode.team import RunLog

    s, sec, close, stories = brief
    seen = []

    async def ask(spec, prompt, log, role):
        seen.append((role, prompt))
        return replies[min(len(seen), len(replies)) - 1]

    monkeypatch.setattr(agent, "_ask", ask)
    out = asyncio.run(agent._write(agent.load_config(), "stub:model", Q, sec, close, stories, s.reg.claims,
                                   s.reg.evidence, RunLog()))
    return out, seen


@needs_db
def test_good_paragraphs_are_kept_and_no_revision_runs(monkeypatch, brief):
    reply = json.dumps({"answer": "Southeast is the story to follow. The change is real but its cause is not settled.",
                        "stories": {"territory:SOUTHEAST": GOOD_STORY}, "charts": {}})
    (answer, sentences, _charts, revised, dropped), seen = _run_write(monkeypatch, brief, [reply])
    assert revised is False and dropped == [] and [r for r, _ in seen] == ["writer"]
    assert answer.startswith("Southeast is the story") and sentences == {"territory:SOUTHEAST": GOOD_STORY}
    assert "[story territory:SOUTHEAST]" in seen[0][1] and "[figure tiles" in seen[0][1]


@needs_db
def test_bad_paragraphs_get_one_revision_and_what_still_fails_is_dropped(monkeypatch, brief):
    bad = json.dumps({"answer": "- Southeast fell.\n- Fix it.",
                      "stories": {"territory:SOUTHEAST": "Calls dropped, so SOUTHEAST fell because of promotion.",
                                  "competitor:BXE": "Metacora gained share. It is an association."}})
    fixed = json.dumps({"answer": "Southeast needs a follow-up. Sales operations can confirm the calls.",
                        "stories": {"territory:SOUTHEAST": "Southeast fell because of promotion, SOUTHEAST said.",
                                    "competitor:BXE": "Metacora gained share. It is an association."}})
    (answer, sentences, _charts, revised, dropped), seen = _run_write(monkeypatch, brief, [bad, fixed])
    assert revised is True and [r for r, _ in seen] == ["writer", "reviser"]
    revise_prompt = seen[1][1]
    assert "is a list" in revise_prompt and "raw IDs" in revise_prompt and "not High" in revise_prompt
    assert answer == "Southeast needs a follow-up. Sales operations can confirm the calls."  # fixed in one round
    assert "territory:SOUTHEAST" not in sentences and sentences["competitor:BXE"].startswith("Metacora gained share")
    assert len(dropped) == 1 and dropped[0].startswith("territory:SOUTHEAST")  # the code text stands for this story


@needs_db
def test_a_typed_digit_or_invented_token_never_reaches_the_brief(monkeypatch, brief):
    reply = json.dumps({"answer": "Down 24.8% in Southeast {c9999}.", "stories": {"territory:SOUTHEAST": "Fell {c33} {c52}."}})
    (answer, sentences, *_), _seen = _run_write(monkeypatch, brief, [reply, reply])
    assert answer == "" and sentences == {}


def test_the_prompts_and_the_revise_message_state_the_limits_the_code_checks():
    from briefing_agent import write

    here = ROOT / "agents" / "brand-briefing" / "briefing_agent" / "prompts"
    words = {"4": "four", "5": "five"}
    writer = (here / "writer.md").read_text(encoding="utf-8")
    revise = (here / "revise.md").read_text(encoding="utf-8")
    assert f"at most {write.MAX_WORDS} words" in writer and f"at most {write.MAX_WORDS} words" in revise
    assert f"two to {words[str(write.ANSWER_SENTENCES)]} short sentences" in writer
    assert f"two to {words[str(write.STORY_SENTENCES)]} sentences" in writer
    assert f"The answer has at most {words[str(write.ANSWER_SENTENCES)]} sentences and a story at most {words[str(write.STORY_SENTENCES)]}" in revise
    message = next(p for p in problems(" ".join(["word"] * (write.MAX_WORDS + 1)) + "."))
    assert f"at most {write.MAX_WORDS}" in message and "under 26" not in message


@pytest.mark.parametrize("phrase", ["the week before", "last week", "the previous week", "the prior weeks", "four weeks before",
                                    "the previous four weeks", "a week earlier", "week over week", "the preceding weeks"])
def test_the_model_never_words_the_comparison_itself(phrase):
    found = problems(f"Southeast fell {{c1}} against {phrase}.")
    assert any("words the comparison itself" in p for p in found), found


def test_the_comparison_token_is_the_only_placeholder_and_needs_a_comparison():
    assert problems("Southeast fell {c1} against {cmp}.") == []
    assert any("{cmp}" in p for p in problems("Southeast fell {c1} against {cmp}.", has_cmp=False))
    assert any("{link:x}" in p for p in problems("Southeast fell {c1} {link:x} it."))


def test_fill_puts_the_phrase_in_and_capitalises_a_sentence_start():
    from briefing_agent import write

    assert write.fill("Down {c1} against {cmp}. {cmp} was higher.", "the previous four weeks") == (
        "Down {c1} against the previous four weeks. The previous four weeks was higher.")
    assert write.fill("Down {c1}.", None) == "Down {c1}."


def test_comparison_phrase_by_window():
    from types import SimpleNamespace as NS

    from pharmagentics.tools.memo import comparison_phrase

    four = ["2026-07-27", "2026-08-03", "2026-08-10", "2026-08-17"]
    assert comparison_phrase(NS(baseline=four, comparison=None)) == "the previous four weeks"
    assert comparison_phrase(NS(baseline=four, comparison=NS(kind="previous"))) == "the previous four weeks"
    assert comparison_phrase(NS(baseline=four, comparison=NS(kind="last_year"))) == "the same weeks last year"
    assert comparison_phrase(NS(baseline=four, comparison=NS(kind="custom"))) == "the weeks from 2026-07-27 to 2026-08-17"
    assert comparison_phrase(NS(baseline=["2026-08-17"], comparison=None)) == "the week of 2026-08-17"
    assert comparison_phrase(NS(baseline=[], comparison=None)) is None


def test_glossary_marks_the_numbers_the_comparison_token_names():
    from briefing_agent import write

    claims = [{"value": "-3.0%", "evidence_id": "e1"}, {"value": "-2.0%", "evidence_id": "e2"}]
    q = ("select 100.0 * (a - b) / b from (select 1 a, 2 b) where week_start in (DATE '2026-08-24') and "
         "week_start in (DATE '%s')")
    evidence = [{"id": "e1", "query": q % "2026-07-27", "params": {}}, {"id": "e2", "query": q % "2026-08-17", "params": {}}]
    _t, data = write.glossary("{c1} {c2}", claims, evidence, ["2026-07-27"])
    assert data["{c1}"]["uses_cmp"] is True and "{cmp}" in data["{c1}"]["text"]
    assert data["{c2}"]["uses_cmp"] is False and "do not name" in data["{c2}"]["text"]


@needs_db
def test_the_comparison_token_is_filled_by_code_after_the_checks(monkeypatch, brief):
    reply = json.dumps({"answer": "Southeast is the story to follow. It fell against {cmp}.",
                        "stories": {"territory:SOUTHEAST": "Southeast fell against {cmp}. The cause is not settled."}, "charts": {}})
    (answer, sentences, _charts, revised, dropped), seen = _run_write(monkeypatch, brief, [reply])
    phrase = brief[1]["comparison_phrase"]
    assert phrase == "the previous four weeks" and revised is False and dropped == []
    assert answer.endswith(f"It fell against {phrase}.") and f"against {phrase}." in sentences["territory:SOUTHEAST"]
    assert "{cmp}" not in answer and "{cmp}" in seen[0][1]


@needs_db
def test_a_comparison_the_model_words_itself_is_revised_then_dropped(monkeypatch, brief):
    slip = json.dumps({"answer": "Southeast fell against the week before. Please check it.", "stories": {}})
    (answer, _s, _c, revised, dropped), seen = _run_write(monkeypatch, brief, [slip, slip])
    assert revised is True and answer == "" and "words the comparison itself" in seen[1][1] and dropped


def test_link_verb_follows_confidence_and_the_answer_follows_the_stories_it_names():
    from briefing_agent import write

    assert write.link_verb(True) == "drove" and write.link_verb(False) == "moved with"
    conf = {"territory:SOUTHEAST": "High", "competitor:BXE": "Medium"}
    who = {"territory:SOUTHEAST": "Southeast", "competitor:BXE": "Metacora"}
    assert write.answer_high("Southeast fell.", conf, who) is True  # names only the High story
    assert write.answer_high("Metacora gained.", conf, who) is False
    assert write.answer_high("Southeast fell and Metacora gained.", conf, who) is False
    assert write.answer_high("The brief is quiet.", conf, who) is False  # names none: every story counts
    assert write.answer_high("Anything.", {}, {}) is False  # no story, nothing to be sure of
    assert write.fill("Calls {link} the fall in {c1}.", None, write.link_verb(False)) == "Calls moved with the fall in {c1}."


def test_the_causal_rule_in_the_answer_covers_only_the_stories_it_names():
    from briefing_agent import write

    tokens = {"territory:SOUTHEAST": {"{c1}"}, "competitor:BXE": {"{c2}"}, "_sections": set()}
    conf = {"territory:SOUTHEAST": "High", "competitor:BXE": "Medium"}
    who = {"territory:SOUTHEAST": "Southeast", "competitor:BXE": "Metacora"}
    assert write.check({"answer": "Calls caused the Southeast fall.", "stories": {}}, tokens, 2, confidences=conf, mentions=who) == {}
    assert "answer" in write.check({"answer": "Metacora caused the fall.", "stories": {}}, tokens, 2, confidences=conf, mentions=who)
    assert "answer" in write.check({"answer": "Calls caused the fall.", "stories": {}}, tokens, 2, confidences=conf, mentions=who)
    assert write.check({"answer": "Calls {link} the Southeast fall.", "stories": {}}, tokens, 2, confidences=conf, mentions=who) == {}


@needs_db
def test_the_link_token_is_filled_with_the_verb_the_story_confidence_allows(monkeypatch, brief):
    from briefing_agent import write

    reply = json.dumps({"answer": "Southeast needs a follow-up. Calls {link} the fall there.",
                        "stories": {"territory:SOUTHEAST": "Southeast fell. Calls {link} the fall."}, "charts": {}})
    (answer, sentences, _charts, revised, dropped), _seen = _run_write(monkeypatch, brief, [reply])
    high = write.confidence(brief[3][0]["section"]) == "High"
    verb = "drove" if high else "moved with"
    assert revised is False and dropped == [] and "{link}" not in answer and "{link}" not in sentences["territory:SOUTHEAST"]
    assert f"Calls {verb} the fall." in sentences["territory:SOUTHEAST"]
    assert f"Calls {verb} the fall there." in answer  # the answer names only Southeast, so its confidence decides
