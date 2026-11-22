"""core-011 FR-016: numbers are scored against the fact's exact value at the precision the answer prints, so a
brief that rounds the true value once is never failed by a golden figure that was already rounded."""
from eval.harness.numbers import extract
from eval.harness.scorers import fact_stated, golden_number_recall, key_fact_recall, numbers_match_golden


def text(answer):
    return {"system": "test", "answer": answer}


# Pacific backorder, week of 2026-06-08: the data holds 22.45, the golden file writes 22.5.
PACIFIC = {"id": "pacific_backorder", "value": 22.5, "exact": 22.45, "tolerance": None, "percent": True}


def test_whole_percent_of_the_exact_value_states_the_fact():
    assert fact_stated(PACIFIC, extract("Distribution backorders ran at 22% in Pacific."))


def test_rounding_the_written_figure_again_does_not_count():
    assert not fact_stated(PACIFIC, extract("Distribution backorders ran at 23% in Pacific."))


def test_one_decimal_must_still_be_right():
    assert fact_stated(PACIFIC, extract("Backorders ran at 22.5%."))  # 22.45 at one decimal, half up
    assert not fact_stated(PACIFIC, extract("Backorders ran at 22.4%."))


def test_unit_still_checked():
    assert not fact_stated(PACIFIC, extract("Pacific wrote 22 TRx more."))


def test_no_exact_value_falls_back_to_the_written_figure():
    written_only = {**PACIFIC, "exact": None}
    assert fact_stated(written_only, extract("Backorders ran at 22.5%."))
    assert not fact_stated(written_only, extract("Backorders ran at 22%."))


def test_key_fact_recall_uses_the_exact_value():
    fb = key_fact_recall(outputs=text("Backorders ran at 22%."), expectations={"key_facts": [PACIFIC]})
    assert fb.value == 1.0


# Metacora's basket share: the data holds 15.47; the golden answer says "16%" (15.5 rounded again).
SHARE = {"expected_response": "Metacora held 16% of the basket.", "fact_exact": [{"value": 15.5, "exact": 15.47}]}


def test_golden_prose_number_backed_by_a_fact_is_scored_on_the_exact_value():
    assert golden_number_recall(outputs=text("Metacora held 15% of the basket."), expectations=SHARE).value == 1.0
    assert golden_number_recall(outputs=text("Metacora held 15.5% of the basket."), expectations=SHARE).value == 1.0
    assert golden_number_recall(outputs=text("Metacora held 17% of the basket."), expectations=SHARE).value == 0.0


def test_golden_prose_number_no_fact_backs_keeps_the_old_match():
    expectations = {"expected_response": "Calls fell 21%.", "fact_exact": [{"value": 15.5, "exact": 15.47}]}
    assert golden_number_recall(outputs=text("Calls fell 21%."), expectations=expectations).value == 1.0
    assert golden_number_recall(outputs=text("Calls fell 20%."), expectations=expectations).value == 0.0


def test_numbers_match_golden_accepts_the_exact_value_once_rounded():
    fb = numbers_match_golden(outputs=text("Metacora held 15% of the basket."), expectations=SHARE)
    assert fb.value == 1.0


def test_a_coarser_fact_does_not_back_a_finer_golden_number():
    """A flag fact written "1" must not back the golden "coverage 0.656" (same() rounds to the coarser figure)."""
    expectations = {"expected_response": "Coverage was 0.656 and the actual is provisional.",
                    "fact_exact": [{"value": 1, "exact": 1.0}]}
    fb = golden_number_recall(outputs=text("Coverage was 0.656."), expectations=expectations)
    assert fb.value == 1.0, fb.rationale
