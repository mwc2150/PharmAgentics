"""brief-010 packet N (FR-006): a finding's direction belongs to a named measure; the national card states each
measure in `directions`. No model, no MLflow run."""
from eval.harness.scorers import false_drivers, finding_recall


def national(direction="down", directions=None, supported=("competitor",), ruled_out=()):
    card = {"headline": "Metacora", "territory": "NATIONAL", "cut": None, "direction": direction,
            "drivers_supported": list(supported), "drivers_ruled_out": list(ruled_out)}
    if directions is not None:
        card["directions"] = directions
    return {"answer": "", "sections": [{"number": "3.2", "title": "Competitor Metacora", "text": "", "card": card}]}


def finding(direction, measure=None, ruled_out=()):
    out = {"id": "f", "territory": "NATIONAL", "direction": direction, "drivers_supported": ["competitor"],
           "drivers_ruled_out": list(ruled_out), "withheld": False, "cut": None}
    if measure:
        out["measure"] = measure
    return {"findings": [out]}


def test_competitor_share_flat_is_read_from_directions_not_the_card_direction():
    card = national(direction="down", directions={"bxa_share": "down", "competitor_share": "flat"})
    assert finding_recall(outputs=card, expectations=finding("flat", "competitor_share")).value == 1.0
    assert finding_recall(outputs=card, expectations=finding("up", "competitor_share")).value == 0.0


def test_bxa_share_down_with_other_drivers_ruled_out():
    card = national(directions={"bxa_share": "down", "competitor_share": "up"}, ruled_out=["access", "promotion", "supply"])
    expected = finding("down", "bxa_share", ruled_out=["access", "promotion", "supply"])
    assert finding_recall(outputs=card, expectations=expected).value == 1.0
    assert finding_recall(outputs=national(directions={"bxa_share": "flat"}), expectations=expected).value == 0.0


def test_no_measure_uses_the_cards_direction_and_any_direction_still_matches():
    card = national(direction="down", directions={"competitor_share": "flat"})
    assert finding_recall(outputs=card, expectations=finding("down")).value == 1.0
    assert finding_recall(outputs=card, expectations=finding("flat")).value == 0.0
    assert finding_recall(outputs=card, expectations=finding(None, "competitor_share")).value == 1.0


def test_a_card_without_directions_cannot_meet_a_measured_finding():
    assert finding_recall(outputs=national(direction="flat"), expectations=finding("flat", "competitor_share")).value == 0.0


def test_a_supported_competitor_the_finding_expects_is_not_a_false_driver():
    card = national(directions={"competitor_share": "flat"})
    assert false_drivers(outputs=card, expectations=finding("flat", "competitor_share")).value == 0
