"""Tests for held-out evaluation scenarios and what-if scenario management."""

import pytest
from app.data.scenarios import (
    get_all_scenarios,
    get_scenario,
    list_scenarios,
    apply_modifications,
)
from app.engine.baseline import run_baseline
from app.engine.optimizer import run_optimizer
from app.engine.constraints import validate_shipment_plan


def test_ten_evaluation_scenarios_exist():
    """Confirms all 10 held-out scenarios are registered with unique IDs."""
    scenarios = list_scenarios()
    scenario_ids = [s.id for s in scenarios]

    expected_prefixes = [
        "EVAL-01", "EVAL-02", "EVAL-03", "EVAL-04", "EVAL-05",
        "EVAL-06", "EVAL-07", "EVAL-08", "EVAL-09", "EVAL-10",
    ]
    for prefix in expected_prefixes:
        assert any(sid.startswith(prefix) for sid in scenario_ids), f"Missing scenario with prefix {prefix}"


def test_scenario_execution_robustness():
    """Runs baseline and optimizer on every held-out scenario to verify stability."""
    scenarios = list_scenarios()
    assert len(scenarios) >= 10

    for sc in scenarios:
        base_res = run_baseline(sc)
        opt_res = run_optimizer(sc)

        # Baseline plan must always be strictly valid
        base_val = validate_shipment_plan(sc, base_res.shipments)
        assert base_val.is_valid, f"Scenario {sc.id} produced invalid baseline plan: {base_val.violations}"

        # Optimizer plan must always be strictly valid
        opt_val = validate_shipment_plan(sc, opt_res.shipments)
        assert opt_val.is_valid, f"Scenario {sc.id} produced invalid optimizer plan: {opt_val.violations}"


def test_apply_modifications_immutability():
    """Ensures scenario modification returns a new object without mutating base scenario."""
    base = get_scenario("EVAL-01-NORMAL")
    orig_delhi_demand = base.destinations[0].demand.get("Tomatoes", 0.0)

    mod_dict = {
        "demand_multiplier": 2.5,
        "travel_time_multiplier": 1.5,
    }
    modified = apply_modifications(base, mod_dict)

    # Base scenario remains unmutated
    assert base.destinations[0].demand.get("Tomatoes", 0.0) == orig_delhi_demand

    # Modified scenario reflects scaling
    mod_delhi_demand = modified.destinations[0].demand.get("Tomatoes", 0.0)
    assert mod_delhi_demand == round(orig_delhi_demand * 2.5, 0)
    assert modified.id.endswith("-SIM")
