from __future__ import annotations

import json

from rgen.cli import main
from rgen.roi_benchmark import build_demo_requests, compare_roi_strategies


def test_roi_benchmark_uses_10_requests_per_strategy() -> None:
    results = compare_roi_strategies()

    assert results["no_routing"].requests == 10
    assert results["free_routing"].requests == 10
    assert results["paid_routing"].requests == 10


def test_roi_benchmark_shows_progressive_total_cost_reduction() -> None:
    results = compare_roi_strategies()

    no_routing = results["no_routing"].total_cost_usd
    free_routing = results["free_routing"].total_cost_usd
    paid_routing = results["paid_routing"].total_cost_usd

    assert paid_routing < free_routing < no_routing


def test_roi_benchmark_paid_reduces_operational_cost() -> None:
    results = compare_roi_strategies()

    assert results["paid_routing"].op_cost_usd < results["free_routing"].op_cost_usd
    assert results["free_routing"].op_cost_usd < results["no_routing"].op_cost_usd


def test_roi_benchmark_demo_requests_have_expected_shape() -> None:
    requests = build_demo_requests()

    assert len(requests) == 10
    assert any(r.needs_clarification for r in requests)
    assert any(r.priority == "high" for r in requests)


def test_roi_benchmark_cli_json_output(capsys) -> None:
    ret = main(["--roi-benchmark"])
    assert ret == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["benchmark_name"] == "roi_routing_comparison"
    assert payload["per_batch_requests"] == 10
    assert payload["strategies"]["paid_routing"]["total_cost_usd"] < payload["strategies"]["free_routing"]["total_cost_usd"]


def test_roi_benchmark_cli_text_output(capsys) -> None:
    ret = main(["--roi-benchmark", "--roi-format", "text"])
    assert ret == 0

    out = capsys.readouterr().out
    assert "ROI Benchmark - Routing Comparison" in out
    assert "free vs no routing" in out


def test_roi_benchmark_cli_scale_and_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "roi.json"
    ret = main(
        [
            "--roi-benchmark",
            "--roi-scale",
            "3",
            "--roi-output",
            str(output),
        ]
    )
    assert ret == 0
    assert output.exists()

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["scale_batches"] == 3
    assert payload["strategies"]["no_routing"]["requests"] == 30
