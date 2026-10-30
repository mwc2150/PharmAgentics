"""Answer-key isolation (EV-9.3, FE-30): the scans pass on the tree and fail on planted violations."""
from eval.harness import isolation
from eval.harness.paths import SOT_DIR

FILES = isolation.repo_files()


def test_only_the_store_module_reads_the_store_variable():
    assert isolation.store_readers(FILES) == []


def test_no_ground_truth_file_in_the_repository():
    assert isolation.ground_truth_files(FILES) == []


def test_agent_code_never_reads_the_golden_set():
    assert isolation.agent_code_reading_eval(FILES) == []


def test_sot_drops_hold_no_answer_key():
    assert isolation.sot_drop_violations(SOT_DIR) == []


def test_planted_violations_are_caught(tmp_path):
    assert isolation.ground_truth_files(["data/answer_key.csv", "x/heldout_params.json", "notes.md"]) == [
        "data/answer_key.csv", "x/heldout_params.json"]
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "leak.py").write_text('import os\nos.environ["PHARMAGENTICS_EVAL_STORE"]\n')
    assert isolation.store_readers(["src/leak.py"], root=tmp_path) == ["src/leak.py"]
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "peek.py").write_text("from eval.harness.cases import load_cases\n")
    assert isolation.agent_code_reading_eval(["agents/peek.py"], root=tmp_path) == ["agents/peek.py"]
    drop = tmp_path / "2026-11-01"
    drop.mkdir()
    (drop / "Answer Key v2.xlsx").write_text("x")
    assert isolation.sot_drop_violations(tmp_path) == ["2026-11-01/Answer Key v2.xlsx"]
