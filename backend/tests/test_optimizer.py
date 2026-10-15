"""Tests for Constraint-Aware Heuristic Optimizer in FreshRoute AI."""

import pytest
from app.data.scenarios import get_scenario
from app.engine.optimizer import run_optimizer
from app.engine.baseline import run_baseline
from app.engine.constraints import validate_shipment_plan


def test_optimizer_execution_and_heuristics_classification():
    """Optimizer executes successfully and clearly labels result as heuristic-optimized."""
    scenario = get_scenario("EVAL-01-NORMAL")
    assert scenario is not None

    result = run_optimizer(scenario)
    assert len(result.shipments) > 0
    assert result.net_revenue > 0.0

    # Ensure result is labeled heuristic-optimized, NEVER optimal
    assert "heuristic" in result.strategy_name.lower() or "optimizer" in result.strategy_name.lower()
    assert "optimal" not in result.strategy_name.lower() or "heuristic" in result.strategy_name.lower()
    assert result.metadata.get("classification") == "heuristic-optimized (NOT globally optimal)"

    # Strict audit check on shipments
    report = validate_shipment_plan(scenario, result.shipments)
    assert report.is_valid, f"Optimizer plan failed constraint audit: {report.violations}"


def test_optimizer_improves_or_matches_baseline():
    """Optimizer achieves higher or equal net revenue compared to baseline EEF."""
    scenario = get_scenario("EVAL-01-NORMAL")

    base_result = run_baseline(scenario)
    opt_result = run_optimizer(scenario)

    # Heuristic optimizer should achieve equal or better net revenue on benchmark
    assert opt_result.net_revenue >= base_result.net_revenue - 1e-4
    # Spoilage rate should not be worse
    assert opt_result.spoilage_rate_pct <= base_result.spoilage_rate_pct + 1e-4


def test_optimizer_deterministic_reproducibility():
    """Running optimizer twice on identical input produces identical allocations."""
    scenario1 = get_scenario("EVAL-01-NORMAL")
    scenario2 = get_scenario("EVAL-01-NORMAL")

    opt1 = run_optimizer(scenario1)
    opt2 = run_optimizer(scenario2)

    assert opt1.total_revenue == opt2.total_revenue
    assert opt1.net_revenue == opt2.net_revenue
    assert len(opt1.shipments) == len(opt2.shipments)
    assert [s.allocated_qty_kg for s in opt1.shipments] == [s.allocated_qty_kg for s in opt2.shipments]


def test_optimizer_no_feasible_scenario():
    """Gracefully handles completely infeasible conditions without unhandled exceptions."""
    scenario = get_scenario("EVAL-08-NO-FEASIBLE")
    assert scenario is not None

    res = run_optimizer(scenario)
    assert len(res.shipments) == 0
    assert res.demand_fulfilled_qty_kg == 0.0
    assert res.total_revenue == 0.0
