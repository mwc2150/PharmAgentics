"""brief-010 packet N (FR-006): a finding's direction belongs to a named measure; the national card states each
measure in `directions`. No model, no MLflow run."""
from eval.harness.scorers import false_drivers, finding_recall


def national(direction="down", directions=None, supported=("competitor",), ruled_out=()):
    card = {"headline": "Metacora", "territory": "NATIONAL", "cut": None, "direction": direction,
            "drivers_supported": list(supported), "drivers_ruled_out": list(ruled_out)}
    if directions is not None:
        card["directions"] = directions
    return {"answer": "", "sections": [{"number": "3.2", "title": "Competitor Metacora", "text": "", "card": card}]}


def finding(direction, measure=None, ruled_out=(), supported=("competitor",)):
    out = {"id": "f", "territory": "NATIONAL", "direction": direction, "drivers_supported": list(supported),
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


def test_a_card_covers_the_measures_in_its_directions_and_a_card_without_directions_covers_trx_only():
    share_card = national(direction="down", directions={"competitor_share": "flat", "bxa_share": "down"})
    assert finding_recall(outputs=share_card, expectations=finding("down")).value == 0.0  # no measure = trx: not covered
    assert finding_recall(outputs=share_card, expectations=finding(None, "competitor_share")).value == 1.0
    plain = national(direction="down", supported=())  # an old-style card: its direction is the TRx direction
    assert finding_recall(outputs=plain, expectations=finding("down", supported=())).value == 1.0
    assert finding_recall(outputs=plain, expectations=finding("down", "trx", supported=())).value == 1.0
    assert finding_recall(outputs=plain, expectations=finding("flat", "competitor_share")).value == 0.0


def test_a_card_without_directions_cannot_meet_a_measured_share_finding():
    assert finding_recall(outputs=national(direction="flat"), expectations=finding("flat", "competitor_share")).value == 0.0


def test_a_supported_competitor_the_finding_expects_is_not_a_false_driver():
    card = national(directions={"competitor_share": "flat"})
    assert false_drivers(outputs=card, expectations=finding("flat", "competitor_share")).value == 0


def test_a_national_share_card_is_no_false_driver_for_a_trx_finding():
    """P2-Q1, P3-Q2 and WIN-1 expect NATIONAL TRx findings (no measure): a national competitor card covers share only."""
    card = national(direction="down", directions={"bxa_share": "down", "competitor_share": "up"})
    for direction, drivers in (("down", ["data"]), ("down", ["holiday"]), ("up", [])):
        expected = finding(direction, supported=drivers)
        assert false_drivers(outputs=card, expectations=expected).value == 0
        assert finding_recall(outputs=card, expectations=expected).value == 0.0  # and it earns no point either
    assert false_drivers(outputs=national(directions={"bxa_share": "down"}), expectations=finding("down", "bxa_share", supported=["access"])).value == 1
