"""End to end: the reference control logs a parent run, a rerun and one trace per case to MLflow."""
import mlflow

from eval.harness.run import run_suite


def test_reference_control_logs_runs_and_traces(tmp_path):
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    parent = run_suite("reference", stories=["P1-Q2", "CA-Q1"], uri=uri, experiment="smoke", artifacts=tmp_path / "a")
    client = mlflow.MlflowClient(uri)
    metrics = client.get_run(parent).data.metrics
    assert metrics["numbers_match_golden/mean"] == 1.0
    assert metrics["must_not_say/mean"] == 1.0
    exp = client.get_experiment_by_name("smoke").experiment_id
    children = client.search_runs([exp], filter_string=f"tags.mlflow.parentRunId = '{parent}'")
    assert len(children) == 1
    assert len(mlflow.search_traces(run_id=children[0].info.run_id, return_type="list")) == 2
