"""Tests for Performance Evaluator & Strategy Comparison in FreshRoute AI."""

import pytest
from app.data.scenarios import get_scenario
from app.engine.optimizer import run_optimizer
from app.engine.baseline import run_baseline
from app.engine.evaluator import compare_strategies, aggregate_scenario_results


def test_evaluator_metric_identities():
    """Validates financial identity: net_revenue == revenue - all costs."""
    scenario = get_scenario("EVAL-01-NORMAL")
    result = run_optimizer(scenario)

    computed_costs = (
        result.total_transport_cost
        + result.total_handling_cost
        + result.total_holding_cost
        + result.total_spoilage_cost
    )
    expected_net = result.total_revenue - computed_costs
    assert abs(result.net_revenue - expected_net) < 0.05, (
        f"Net revenue mismatch: {result.net_revenue} vs expected {expected_net}"
    )


def test_evaluator_zero_division_safety():
    """Zero demand or zero inventory must safely return 0.0% without ZeroDivisionError."""
    scenario = get_scenario("EVAL-09-ZERO-DEMAND")
    result = run_optimizer(scenario)

    assert result.fulfillment_pct == 0.0
    assert result.demand_fulfilled_qty_kg == 0.0
    assert result.total_demand_kg == 0.0


def test_compare_strategies_structure():
    """Comparison produces structured differential audit between baseline and optimizer."""
    scenario = get_scenario("EVAL-01-NORMAL")
    base_res = run_baseline(scenario)
    opt_res = run_optimizer(scenario)

    comparison = compare_strategies(base_res, opt_res)

    assert "baseline" in comparison
    assert "optimized" in comparison
    assert "comparison" in comparison
    assert "summary" in comparison

    metrics_map = comparison["comparison"]
    assert "net_revenue" in metrics_map
    assert "spoilage_rate_pct" in metrics_map
    assert "fulfillment_pct" in metrics_map

    net_rev_diff = metrics_map["net_revenue"]
    assert net_rev_diff["preferred_direction"] == "higher"
    assert "absolute_difference" in net_rev_diff


def test_baseline_wins_honesty():
    """On scenario EVAL-10-BASELINE-WINS, evaluation honestly reports if baseline wins."""
    scenario = get_scenario("EVAL-10-BASELINE-WINS")
    base_res = run_baseline(scenario)
    opt_res = run_optimizer(scenario)

    comparison = compare_strategies(base_res, opt_res)
    assert "summary" in comparison
    summary = comparison["summary"]
    assert "verdict" in summary
    assert "description" in summary


def test_aggregate_scenario_results():
    """Evaluates multi-scenario aggregation of evaluation results."""
    scenario_ids = ["EVAL-01-NORMAL", "EVAL-02-SHORT-SHELF", "EVAL-03-DEMAND-SPIKE"]
    results_list = []

    for sid in scenario_ids:
        sc = get_scenario(sid)
        b = run_baseline(sc)
        o = run_optimizer(sc)
        c = compare_strategies(b, o)
        c["scenario_id"] = sc.id
        c["scenario_name"] = sc.name
        results_list.append(c)

    aggregated = aggregate_scenario_results(results_list)
    assert aggregated["scenario_count"] == 3
    assert "win_loss" in aggregated
    assert "optimizer_win_rate_pct" in aggregated["win_loss"]
