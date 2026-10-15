"""Tests for Discount Recommendation Engine in FreshRoute AI."""

import pytest
from app.data.scenarios import get_scenario
from app.engine.optimizer import run_optimizer
from app.engine.discount import generate_discount_recommendations


def test_discount_recommendations_on_at_risk_batches():
    """Generates valid discount recommendations for unallocated or urgent inventory."""
    scenario = get_scenario("EVAL-01-NORMAL")
    assert scenario is not None

    opt_result = run_optimizer(scenario)
    recommendations = generate_discount_recommendations(scenario, opt_result.shipments)

    # If there are any recommendations, verify their structure and economic validity
    assert isinstance(recommendations, list)
    for rec in recommendations:
        assert "batch_id" in rec
        assert "commodity" in rec
        assert "recommended_discount_pct" in rec
        assert rec["recommended_discount_pct"] in scenario.discount_config.steps

        if rec["recommended_discount_pct"] > 0.0:
            assert rec.get("expected_net_contribution_change_inr", rec.get("net_contribution_change", 0.0)) > 0.0

        # Explanation or recommendation string should be present
        explanation = rec.get("explanation") or rec.get("recommendation") or ""
        assert len(explanation) > 0


def test_discount_disabled_config():
    """When discount config is disabled, returns empty recommendation list."""
    scenario = get_scenario("EVAL-01-NORMAL")
    scenario.discount_config.enabled = False

    opt_result = run_optimizer(scenario)
    recommendations = generate_discount_recommendations(scenario, opt_result.shipments)
    assert len(recommendations) == 0


def test_discount_elasticity_assumptions_documented():
    """Confirms conservative illustrative elasticity multiplier is explicitly disclosed."""
    scenario = get_scenario("EVAL-02-SHORT-SHELF")
    opt_result = run_optimizer(scenario)
    recommendations = generate_discount_recommendations(scenario, opt_result.shipments)

    for rec in recommendations:
        explanation = rec.get("explanation", "")
        # Check that assumptions disclose elasticity multiplier
        assert "elasticity" in explanation.lower() or "elasticity" in rec.get("assumptions", "").lower()
