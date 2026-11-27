"""Run a system on the golden set and log one MLflow parent run with a child run per rerun."""
from __future__ import annotations

import os
import statistics
import time
from pathlib import Path

import mlflow

from .cases import golden_fingerprint, load_cases
from .cost import usage_metrics
from .paths import EXPERIMENT, MLFLOW_DIR, tracking_uri
from .scorers import (DETERMINISTIC, EVIDENCE, REPORT_ONLY, TARGETS, TRAJECTORY, WORD_BUDGET, count_words, finding_counts,
                      judge_scorers, key_fact_counts, leader_words)
from .systems import BRIEFING_SYSTEMS, SYSTEMS, brand_option, briefing_question, definition_option
from .versions import code_version, data_fingerprint


def configure(uri: str | None = None, experiment: str = EXPERIMENT, artifacts: Path | None = None) -> None:
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    mlflow.set_tracking_uri(uri or tracking_uri())
    if mlflow.get_experiment_by_name(experiment) is None:
        artifacts = artifacts or MLFLOW_DIR / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        mlflow.create_experiment(experiment, artifact_location=artifacts.as_uri())
    mlflow.set_experiment(experiment)


def run_suite(system: str, lane: str = "all", reruns: int = 1, judge: str | None = None,
              stories: list[str] | None = None, uri: str | None = None, experiment: str = EXPERIMENT,
              artifacts: Path | None = None, model: str | None = None, brand: str = "BXA") -> str:
    """`brand` picks the cases: "BXA" (the default, so a run is what it was before Lipidara), "BXC", or "all". A case about
    a brand the system cannot answer for is skipped: listed on the run, never run, never scored, never a run error."""
    selected = load_cases(lane, stories, brand=brand)
    if not selected:
        raise SystemExit("No golden cases match; run `python -m eval import-stories` first.")
    sut = SYSTEMS[system](selected, model=model) if model else SYSTEMS[system](selected)
    supported = tuple(getattr(sut, "brands", ("BXA",)))
    cases = [c for c in selected if c.brand in supported]
    skipped = [c for c in selected if c.brand not in supported]
    brands = sorted({c.brand for c in selected})
    label = system if brands == ["BXA"] else f"{system}@{'+'.join(brands)}"  # a Lipidara or mixed run is its own system row
    if skipped:
        print(f"  skipping {len(skipped)} case(s) {system} has no {'/'.join(sorted({c.brand for c in skipped}))} support for: "
              + ", ".join(c.id for c in skipped))
    if not cases:
        return _record_skipped(label, lane, skipped, experiment, uri, artifacts)
    scorers = (DETERMINISTIC + REPORT_ONLY + (EVIDENCE if sut.returns_evidence else [])
               + (TRAJECTORY if getattr(sut, "returns_trajectory", False) else []))
    judges = judge_scorers(judge) if judge else []
    os.environ["PHARMAGENTICS_TRACING"] = "1"  # stage and tool spans inside the system under test
    # One prediction at a time: parallel trace writes to the SQLite store lose traces to lock
    # contention, and a local model serves one request at a time anyway.
    os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "1")
    if sut.uses_llm or judge:
        os.environ.setdefault("MLFLOW_GENAI_EVAL_LLM_TIMEOUT", "600")
    os.environ.setdefault("MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION", "True")

    configure(uri, experiment, artifacts)
    # MLflow refuses a None expectation ("The `value` field must be specified"), so a key with no value is left out of the
    # logged rows; every scorer reads expectations with .get, so an absent key reads as None.
    rows = [{"inputs": c.inputs(), "expectations": {k: v for k, v in c.expectations().items() if v is not None}} for c in cases]
    latency: dict[str, list[float]] = {"brief": [], "turn": []}  # brief-006 FR-011

    # Traced here because skipping MLflow's first-row validation also skips its auto-tracing wrapper.
    errors: list[str] = []
    answered: dict[tuple, dict] = {}  # what the system returned per input, for the pooled key-fact share

    def input_key(question, follow_up=None, section=None, comparison=None, brand=None) -> tuple:
        key = question, follow_up, section, repr(sorted(comparison.items())) if comparison else None
        return key + (brand,) if brand and brand != "BXA" else key  # a Cardiovela key is the key it always was

    @mlflow.trace(name=f"{system}.predict", span_type="AGENT")
    def predict_fn(question: str, follow_up: str | None = None, section: str | None = None,
                   comparison: dict | None = None, definition: dict | None = None, intent: str = "brief",
                   brand: str = "BXA") -> dict:
        try:
            started = time.perf_counter()
            options = {"comparison": comparison} if comparison and system in ("briefing_scripted", "briefing_agent") else {}
            # The case's question as the app sends it (its intent); the answer is still filed under the case's own question
            sent = briefing_question(question, intent) if isinstance(sut, BRIEFING_SYSTEMS) else question
            if follow_up and hasattr(sut, "predict_follow_up"):
                method = sut.predict_follow_up
                out = method(sent, follow_up, section, **options, **definition_option(method, definition),
                             **brand_option(method, brand))
            else:
                out = sut.predict(sent, **options, **definition_option(sut.predict, definition),
                                  **brand_option(sut.predict, brand))
            timed = (out.get("latency") if isinstance(out, dict) else None) or {"brief": time.perf_counter() - started}
            for kind, secs in timed.items():
                if kind in latency and secs is not None:
                    latency[kind].append(float(secs))
            answered[input_key(question, follow_up, section, comparison, brand)] = out
            return out
        except Exception as exc:  # MLflow records the failure per row; count it so it is never read as a score
            errors.append(f"{question[:70]}: {type(exc).__name__}: {exc}")
            raise

    model = getattr(sut, "model", None)
    params = {
        "system": f"{label}:{model}" if model else label,
        "lane": lane, "cases": len(cases), "reruns": reruns, "judge": judge or "off",
        "golden_version": golden_fingerprint(None if lane == "all" else lane, brand=brand),
        "data_version": data_fingerprint(), "code_version": code_version(),
        **getattr(sut, "params", {}),  # e.g. an agent's configuration version
        **({"brand": "+".join(brands)} if brands != ["BXA"] else {}),  # a BXA-only run logs what it always logged
        **({"skipped_cases": ",".join(c.id for c in skipped)} if skipped else {}),
    }
    per_rerun: list[dict] = []
    with mlflow.start_run(run_name=f"{label} · {lane}") as parent:
        mlflow.log_params(params)
        mlflow.set_tags({"suite": "golden", "system": label, "lane": lane})
        if skipped:
            mlflow.log_text("\n".join(f"{c.id} ({c.brand})" for c in skipped), "skipped_cases.txt")
            mlflow.log_metric("cases_skipped", float(len(skipped)))
        for i in range(1, reruns + 1):
            with mlflow.start_run(run_name=f"{label} · {lane} · rerun {i}", nested=True) as child:
                mlflow.log_params({**params, "rerun": i})
                errors.clear()
                answered.clear()
                latency["brief"].clear(); latency["turn"].clear()
                result = mlflow.genai.evaluate(data=rows, predict_fn=predict_fn, scorers=scorers)
                metrics = {k: float(v) for k, v in result.metrics.items() if isinstance(v, (int, float))}
                if hasattr(sut, "runtime"):  # before the judge, which may evict a local agent model
                    mlflow.set_tags(sut.runtime())
                if judges:
                    metrics.update(_judge_rerun(child.info.run_id, judges, len(rows)))
                for kind, values in latency.items():  # median and 95th percentile per brief and per turn
                    if values:
                        ordered = sorted(values)
                        metrics[f"latency_{kind}_p50/mean"] = statistics.median(ordered)
                        metrics[f"latency_{kind}_p95/mean"] = ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]
                        mlflow.log_metric(f"latency_{kind}_p50/mean", metrics[f"latency_{kind}_p50/mean"])
                        mlflow.log_metric(f"latency_{kind}_p95/mean", metrics[f"latency_{kind}_p95/mean"])
                for key, value in usage_metrics(answered.values()).items():  # tokens and estimated dollars, report only
                    metrics[key] = value
                    mlflow.log_metric(key, value)
                for key, value in pooled_by_brand(cases, answered, input_key).items():
                    metrics[key] = value  # report-only (core-011 FR-019); `<scorer>/mean` stays per case
                    mlflow.log_metric(key, value)
                metrics["run_errors/mean"] = float(len(errors))  # failure tag "run error" (Evaluation Pack section 8)
                mlflow.log_metric("run_errors/mean", float(len(errors)))
                if errors:
                    mlflow.log_text("\n".join(errors), "run_errors.txt")
                    print(f"  RUN ERRORS in rerun {i}: {len(errors)} of {len(cases)} cases crashed, e.g. {errors[0]}")
                per_rerun.append(metrics)
        keys = sorted({k for m in per_rerun for k in m})
        for key in keys:
            values = [m[key] for m in per_rerun if key in m]
            mlflow.log_metric(key, statistics.fmean(values))
            if len(values) > 1:
                mlflow.log_metric(key.replace("/mean", "") + "/rerun_std", statistics.pstdev(values))
        spent = [m["cost_usd_rerun"] for m in per_rerun if "cost_usd_rerun" in m]
        if spent:
            mlflow.log_metric("cost_usd_run", sum(spent))  # every rerun together: what the run cost (estimated)
    print(f"\nRun {parent.info.run_id} ({label}, {lane}, {len(cases)} cases, {reruns} rerun(s))")
    if spent:
        print(f"  Model cost, estimated: ${sum(spent):.4f} for the run, ${sum(spent) / len(spent):.4f} a rerun")
    for key in keys:
        values = [m[key] for m in per_rerun if key in m]
        print(f"  {key:<40} {statistics.fmean(values):.3f}")
    return parent.info.run_id


def _answer_of(case, answered: dict, input_key) -> dict | None:
    inputs = case.inputs()
    brand = [inputs["brand"]] if inputs.get("brand") else []  # only a Lipidara input carries a brand
    return answered.get(input_key(inputs["question"], inputs["follow_up"], inputs["section"], inputs.get("comparison"), *brand))


def _pooled_key_facts(cases, answered: dict, input_key) -> float | None:
    """Stated must facts over all must facts across all cases; None when no case has a must fact. A case that crashed
    or never answered still counts its must facts in the total, with none stated, so a crash lowers the share.
    A case with no must facts is "not scored" in `key_fact_recall`, which MLflow leaves out of the mean (None
    values are dropped by compute_aggregated_metrics), so `key_fact_recall/mean` is already over scored cases."""
    stated = total = 0
    for case in cases:
        out = _answer_of(case, answered, input_key)
        if out is None:
            total += len(case.expectations().get("key_facts") or [])
            continue
        s, _, t = key_fact_counts(out, case.expectations())
        stated, total = stated + s, total + t
    return round(stated / total, 4) if total else None


def _pooled_findings(cases, answered: dict, input_key) -> float | None:
    """Points over possible points across all cases with expected findings; None when none has one. A case that
    never answered, or whose brief has no story cards, counts its possible points with none earned."""
    got = possible = 0
    for case in cases:
        expectations = case.expectations()
        out = _answer_of(case, answered, input_key)
        g, p, _ = finding_counts(out if out is not None else {}, expectations)
        got, possible = got + g, possible + p
    return round(got / possible, 4) if possible else None


def pooled_metrics(cases, answered: dict, input_key) -> dict[str, float]:
    """Report-only run metrics for the Briefing cases (core-011 FR-019, FR-020): pooled key-fact and finding recall,
    whether each meets its target (1.0 or 0.0), and the count of cases whose brief is over the word budget."""
    briefing = [c for c in cases if c.lane == "briefing"]
    out: dict[str, float] = {}
    if (pooled := _pooled_key_facts(briefing, answered, input_key)) is not None:
        out["key_fact_recall_pooled"] = pooled
        out["key_fact_target_met"] = float(pooled >= TARGETS["key_fact_recall"])
    if (pooled := _pooled_findings(briefing, answered, input_key)) is not None:
        out["finding_recall_pooled"] = pooled
        out["finding_target_met"] = float(pooled >= TARGETS["finding_recall"])
    if briefing:
        over = 0
        for case in briefing:
            sections = (_answer_of(case, answered, input_key) or {}).get("sections")
            if sections:
                over += count_words(sections) > WORD_BUDGET["analyst"] or leader_words(sections) > WORD_BUDGET["leader"]
        out["over_word_budget"] = float(over)
    return out


def pooled_by_brand(cases, answered: dict, input_key) -> dict[str, float]:
    """`pooled_metrics` over the whole run, as always. A run that mixes brands adds the same metrics per brand with a
    lower-case brand suffix (`key_fact_recall_pooled_bxa`, `..._bxc`), so Cardiovela's numbers stay comparable with its
    BXA-only runs and Lipidara's are read on their own."""
    out = pooled_metrics(cases, answered, input_key)
    present = sorted({c.brand for c in cases})
    if len(present) > 1:
        for brand in present:
            for key, value in pooled_metrics([c for c in cases if c.brand == brand], answered, input_key).items():
                out[f"{key}_{brand.lower()}"] = value
    return out


def _record_skipped(label: str, lane: str, skipped, experiment: str, uri: str | None, artifacts) -> str:
    """A run where the system supports none of the selected cases: recorded with what was skipped, nothing run."""
    configure(uri, experiment, artifacts)
    with mlflow.start_run(run_name=f"{label} · {lane}") as parent:
        mlflow.log_params({"system": label, "lane": lane, "cases": 0, "skipped_cases": ",".join(c.id for c in skipped)[:500],
                           "data_version": data_fingerprint(), "code_version": code_version()})
        mlflow.set_tags({"suite": "golden", "system": label, "lane": lane,
                         "note": "every selected case is about a brand this system does not support"})
        mlflow.log_text("\n".join(f"{c.id} ({c.brand})" for c in skipped), "skipped_cases.txt")
        mlflow.log_metric("cases_skipped", float(len(skipped)))
    print(f"\nRun {parent.info.run_id} ({label}, {lane}): nothing run, {len(skipped)} case(s) skipped.")
    return parent.info.run_id


def _judge_rerun(run_id: str, judges: list, expected: int) -> dict:
    """Judge a rerun's traces once every case is answered. MLflow 3.17 otherwise scores one case while it
    predicts the next, and on one small GPU the judge and a local agent model then swap on every request.
    Same experiment, so MLflow links the existing traces instead of copying them; the judge reads each
    trace's inputs, outputs and the expectations phase one logged on it."""
    traces = mlflow.search_traces(run_id=run_id, return_type="list")
    traces = [t for t in traces if t.info.trace_metadata.get("mlflow.sourceRun") == run_id]
    if len(traces) != expected:
        print(f"  judge: found {len(traces)} traces for {expected} cases in run {run_id}")
    result = mlflow.genai.evaluate(data=[{"trace": t} for t in traces], scorers=judges)
    return {k: float(v) for k, v in result.metrics.items() if isinstance(v, (int, float))}


def gate(candidate: str, baseline: str, uri: str | None = None) -> int:
    """Exit 1 when any gated code check scores lower than on the baseline run (Briefing B-VII)."""
    from .scorers import GATED

    configure(uri)
    client = mlflow.MlflowClient()
    cand, base = client.get_run(candidate).data.metrics, client.get_run(baseline).data.metrics
    failed = cand.get("run_errors/mean", 0) > base.get("run_errors/mean", 0)
    if failed:
        print(f"  run_errors/mean                  baseline {base.get('run_errors/mean', 0):.0f}  candidate {cand['run_errors/mean']:.0f}  REGRESSION")
    for name in GATED:
        key = f"{name}/mean"
        if key not in base or key not in cand:
            print(f"  {key:<32} missing on one run")
            continue
        drop = cand[key] < base[key] - 1e-9
        failed |= drop
        print(f"  {key:<32} baseline {base[key]:.3f}  candidate {cand[key]:.3f}  {'REGRESSION' if drop else 'ok'}")
    return 1 if failed else 0
