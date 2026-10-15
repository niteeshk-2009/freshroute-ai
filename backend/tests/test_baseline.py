"""Tests for Earliest-Expiry-First (EEF) Baseline Strategy in FreshRoute AI."""

import pytest
from app.data.scenarios import get_scenario
from app.engine.baseline import run_baseline
from app.engine.constraints import validate_shipment_plan


def test_baseline_execution_on_default_scenario():
    """EEF Baseline runs cleanly and produces a valid shipment plan."""
    scenario = get_scenario("EVAL-01-NORMAL")
    assert scenario is not None

    result = run_baseline(scenario)
    assert "Earliest-Expiry-First" in result.strategy_name
    assert len(result.shipments) > 0
    assert result.net_revenue > 0.0
    assert result.fulfillment_pct > 0.0
    assert result.inventory_utilization_pct > 0.0

    # Strict audit check on shipments
    report = validate_shipment_plan(scenario, result.shipments)
    assert report.is_valid, f"Baseline produced invalid plan: {report.violations}"


def test_baseline_eef_ordering_rule():
    """Verifies that baseline prioritizes batches with shortest shelf life."""
    scenario = get_scenario("EVAL-01-NORMAL")
    result = run_baseline(scenario)

    batches_by_id = {b.id: b for b in scenario.inventory_batches}
    dispatched_shelf_lives = [
        batches_by_id[s.batch_id].remaining_shelf_life_hours
        for s in result.shipments
    ]

    # The first dispatched batch must have one of the shortest shelf lives
    min_shelf_life = min(b.remaining_shelf_life_hours for b in scenario.inventory_batches)
    assert dispatched_shelf_lives[0] <= min_shelf_life + 24.0


def test_baseline_deterministic_behavior():
    """Identical scenario input must produce identical baseline output."""
    scenario1 = get_scenario("EVAL-01-NORMAL")
    scenario2 = get_scenario("EVAL-01-NORMAL")

    res1 = run_baseline(scenario1)
    res2 = run_baseline(scenario2)

    assert res1.total_revenue == res2.total_revenue
    assert res1.net_revenue == res2.net_revenue
    assert len(res1.shipments) == len(res2.shipments)
    assert [s.allocated_qty_kg for s in res1.shipments] == [s.allocated_qty_kg for s in res2.shipments]


def test_baseline_handles_zero_demand():
    """Baseline handles market with 0 demand gracefully without divide-by-zero."""
    scenario = get_scenario("EVAL-09-ZERO-DEMAND")
    assert scenario is not None

    res = run_baseline(scenario)
    assert len(res.shipments) == 0
    assert res.total_revenue == 0.0
    assert res.demand_fulfilled_qty_kg == 0.0
    assert res.fulfillment_pct == 0.0
