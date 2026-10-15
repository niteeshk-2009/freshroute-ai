"""Performance evaluation and comparison engine for FreshRoute AI.

Computes and compares metrics between baseline and optimized strategies.
Both strategies use identical inputs and metric calculations.
Negative results are shown honestly.

Metrics (from official PS 07):
- Estimated spoilage (quantity, rate, disposal cost)
- Demand fulfillment (quantity, percentage, unfulfilled)
- Net revenue (revenue - transport - handling - holding - spoilage costs)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.domain import EvaluationResult, Scenario


def compare_strategies(
    baseline: EvaluationResult,
    optimized: EvaluationResult,
) -> Dict[str, Any]:
    """Compare baseline and optimized strategies on identical scenarios.

    Returns a comprehensive comparison dict with:
    - Both strategy results
    - Absolute and relative differences
    - Direction indicators (which is better)
    - Honest reporting of negative results
    """
    comparison = {
        "baseline": _result_to_dict(baseline),
        "optimized": _result_to_dict(optimized),
        "comparison": {},
        "summary": {},
    }

    # Define metrics and their preferred direction
    metrics = [
        ("net_revenue", "higher", "₹"),
        ("total_revenue", "higher", "₹"),
        ("total_transport_cost", "lower", "₹"),
        ("total_handling_cost", "lower", "₹"),
        ("total_holding_cost", "lower", "₹"),
        ("total_spoilage_cost", "lower", "₹"),
        ("spoiled_qty_kg", "lower", "kg"),
        ("spoilage_rate_pct", "lower", "%"),
        ("demand_fulfilled_qty_kg", "higher", "kg"),
        ("fulfillment_pct", "higher", "%"),
        ("inventory_utilization_pct", "higher", "%"),
        ("unallocated_qty_kg", "lower", "kg"),
        ("feasible_shipment_count", "higher", ""),
        ("shelf_life_violations", "lower", ""),
        ("capacity_violations", "lower", ""),
    ]

    for metric_name, preferred_direction, unit in metrics:
        baseline_val = getattr(baseline, metric_name, 0.0)
        optimized_val = getattr(optimized, metric_name, 0.0)

        absolute_diff = optimized_val - baseline_val

        # Relative difference (avoid divide by zero)
        if baseline_val != 0:
            relative_diff_pct = (absolute_diff / abs(baseline_val)) * 100
        else:
            relative_diff_pct = None  # N/A when baseline is zero

        # Determine if optimizer is better
        if preferred_direction == "higher":
            optimizer_better = absolute_diff > 0
        else:
            optimizer_better = absolute_diff < 0

        comparison["comparison"][metric_name] = {
            "baseline": round(baseline_val, 2),
            "optimized": round(optimized_val, 2),
            "absolute_difference": round(absolute_diff, 2),
            "relative_difference_pct": round(relative_diff_pct, 2) if relative_diff_pct is not None else None,
            "preferred_direction": preferred_direction,
            "unit": unit,
            "optimizer_better": optimizer_better,
            "display": _format_comparison(
                metric_name, baseline_val, optimized_val,
                absolute_diff, relative_diff_pct, preferred_direction, unit
            ),
        }

    # Generate summary
    comparison["summary"] = _generate_summary(baseline, optimized, comparison["comparison"])

    return comparison


def aggregate_scenario_results(
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate results across multiple scenarios.

    Computes mean, min, max, and worst-case for key metrics.
    """
    if not results:
        return {"error": "No results to aggregate", "scenarios": 0}

    n = len(results)
    metrics_to_aggregate = [
        "net_revenue", "spoilage_rate_pct", "fulfillment_pct",
        "inventory_utilization_pct", "spoiled_qty_kg",
    ]

    aggregated = {
        "scenario_count": n,
        "total_scenarios": n,
        "baseline": {},
        "optimized": {},
        "comparison": {},
    }

    for strategy in ["baseline", "optimized"]:
        for metric in metrics_to_aggregate:
            values = []
            for r in results:
                if strategy in r and metric in r[strategy]:
                    values.append(r[strategy][metric])

            if values:
                aggregated[strategy][metric] = {
                    "mean": round(sum(values) / len(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "total": round(sum(values), 2),
                }

    # Count wins/losses
    optimizer_wins = 0
    baseline_wins = 0
    ties = 0

    for r in results:
        if "comparison" in r and "net_revenue" in r["comparison"]:
            diff = r["comparison"]["net_revenue"].get("absolute_difference", 0)
            if diff > 0.01:
                optimizer_wins += 1
            elif diff < -0.01:
                baseline_wins += 1
            else:
                ties += 1

    aggregated["win_loss"] = {
        "optimizer_wins": optimizer_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "optimizer_win_rate_pct": round(optimizer_wins / n * 100, 1) if n > 0 else 0,
    }

    # Cases where optimizer underperformed
    aggregated["optimizer_underperformed"] = [
        {
            "scenario": r.get("scenario_name", f"Scenario {i+1}"),
            "baseline_net_revenue": r.get("baseline", {}).get("net_revenue", 0),
            "optimized_net_revenue": r.get("optimized", {}).get("net_revenue", 0),
            "difference": r.get("comparison", {}).get("net_revenue", {}).get("absolute_difference", 0),
        }
        for i, r in enumerate(results)
        if r.get("comparison", {}).get("net_revenue", {}).get("absolute_difference", 0) < -0.01
    ]

    return aggregated


def _result_to_dict(result: EvaluationResult) -> Dict[str, Any]:
    """Convert EvaluationResult to a clean dict for comparison."""
    return {
        "strategy_name": result.strategy_name,
        "net_revenue": result.net_revenue,
        "total_revenue": result.total_revenue,
        "total_transport_cost": result.total_transport_cost,
        "total_handling_cost": result.total_handling_cost,
        "total_holding_cost": result.total_holding_cost,
        "total_spoilage_cost": result.total_spoilage_cost,
        "spoiled_qty_kg": result.spoiled_qty_kg,
        "spoilage_rate_pct": result.spoilage_rate_pct,
        "demand_fulfilled_qty_kg": result.demand_fulfilled_qty_kg,
        "total_demand_kg": result.total_demand_kg,
        "fulfillment_pct": result.fulfillment_pct,
        "inventory_utilization_pct": result.inventory_utilization_pct,
        "unallocated_qty_kg": result.unallocated_qty_kg,
        "feasible_shipment_count": result.feasible_shipment_count,
        "shelf_life_violations": result.shelf_life_violations,
        "capacity_violations": result.capacity_violations,
        "execution_time_ms": result.execution_time_ms,
        "shipment_count": len(result.shipments),
    }


def _format_comparison(
    name: str, baseline: float, optimized: float,
    diff: float, rel_pct: Optional[float],
    direction: str, unit: str,
) -> str:
    """Format a human-readable comparison string."""
    direction_arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="

    better = (direction == "higher" and diff > 0) or (direction == "lower" and diff < 0)
    worse = (direction == "higher" and diff < 0) or (direction == "lower" and diff > 0)

    label = name.replace("_", " ").title()
    verdict = "✅ Better" if better else "❌ Worse" if worse else "➖ Equal"

    rel_str = f" ({rel_pct:+.1f}%)" if rel_pct is not None else ""

    return (
        f"{label}: Baseline {baseline:,.2f}{unit} → Optimized {optimized:,.2f}{unit} "
        f"({direction_arrow} {diff:+,.2f}{unit}{rel_str}) — {verdict}"
    )


def _generate_summary(
    baseline: EvaluationResult,
    optimized: EvaluationResult,
    comparisons: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate executive summary of the comparison."""

    # Count improvements vs regressions
    improvements = sum(1 for c in comparisons.values() if c["optimizer_better"])
    regressions = sum(1 for c in comparisons.values() if not c["optimizer_better"] and c["absolute_difference"] != 0)
    unchanged = sum(1 for c in comparisons.values() if c["absolute_difference"] == 0)

    revenue_diff = comparisons.get("net_revenue", {}).get("absolute_difference", 0)
    spoilage_diff = comparisons.get("spoilage_rate_pct", {}).get("absolute_difference", 0)
    fulfillment_diff = comparisons.get("fulfillment_pct", {}).get("absolute_difference", 0)

    # Determine overall verdict
    if revenue_diff > 0 and spoilage_diff <= 0 and fulfillment_diff >= 0:
        verdict = "OPTIMIZER_CLEARLY_BETTER"
        description = (
            f"The optimizer outperforms the baseline with higher net revenue "
            f"(+₹{revenue_diff:,.2f}), equal or lower spoilage, and equal or higher fulfillment."
        )
    elif revenue_diff < 0:
        verdict = "BASELINE_BETTER_ON_REVENUE"
        description = (
            f"The baseline achieves higher net revenue (₹{abs(revenue_diff):,.2f} more). "
            f"The optimizer's constraint-aware approach may be too conservative in this scenario."
        )
    elif spoilage_diff > 0:
        verdict = "MIXED_HIGHER_SPOILAGE"
        description = (
            f"Mixed results: optimizer has {'higher' if revenue_diff > 0 else 'lower'} revenue "
            f"but {'higher' if spoilage_diff > 0 else 'lower'} spoilage rate."
        )
    else:
        verdict = "COMPARABLE"
        description = "Both strategies produce comparable results in this scenario."

    return {
        "verdict": verdict,
        "description": description,
        "narrative": description,
        "improvements_count": improvements,
        "regressions_count": regressions,
        "unchanged_count": unchanged,
        "key_findings": {
            "net_revenue_change_inr": round(revenue_diff, 2),
            "spoilage_rate_change_pct_points": round(spoilage_diff, 2),
            "fulfillment_change_pct_points": round(fulfillment_diff, 2),
        },
        "baseline_execution_ms": baseline.execution_time_ms,
        "optimizer_execution_ms": optimized.execution_time_ms,
    }
