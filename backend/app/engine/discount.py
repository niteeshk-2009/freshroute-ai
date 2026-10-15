"""Discount recommendation engine for FreshRoute AI.

Recommends discounts for batches at risk of remaining unsold or spoiling.
Uses a configurable rule-based approach with conservative, illustrative demand elasticity.
All assumptions are disclosed and configurable.

Discount levels: 0%, 5%, 10%, 15%, 20% (configurable)
Demand elasticity: discount_pct × elasticity_multiplier = assumed additional demand percentage
    Default elasticity_multiplier = 1.5
    This is an ILLUSTRATIVE response curve, NOT an empirically validated demand forecast.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    Scenario, ShipmentPlan, DiscountConfig, CostAssumptions,
)
from app.engine.explainer import explain_discount


def generate_discount_recommendations(
    scenario: Scenario,
    shipments: List[ShipmentPlan],
    batch_allocated: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Generate discount recommendations for at-risk batches.

    A batch is "at risk" if:
    1. It has remaining shelf life below the configured threshold
    2. It has significant unallocated quantity after optimization
    3. Its market conditions suggest discounting could improve outcomes

    For each at-risk batch, test each discount level and recommend
    the one that maximizes expected net contribution improvement.

    Args:
        scenario: The current scenario with config
        shipments: Current allocation plan
        batch_allocated: Dict of batch_id -> allocated quantity

    Returns:
        List of discount recommendation dicts with full explanations
    """
    config = scenario.discount_config
    if not config.enabled:
        return []

    # Compute batch allocation if not provided
    if batch_allocated is None:
        batch_allocated = {}
        for s in shipments:
            batch_allocated[s.batch_id] = batch_allocated.get(s.batch_id, 0.0) + s.allocated_qty_kg

    recommendations: List[Dict[str, Any]] = []
    dest_map = {d.id: d for d in scenario.destinations}

    for batch in scenario.inventory_batches:
        allocated = batch_allocated.get(batch.id, 0.0)
        unallocated = batch.quantity_kg - allocated

        # Check if batch is at risk
        is_short_shelf_life = batch.remaining_shelf_life_hours < config.shelf_life_threshold_hours
        has_unallocated = unallocated > batch.quantity_kg * 0.1  # >10% unallocated

        if not (is_short_shelf_life or has_unallocated):
            continue

        # Determine risk reason
        if is_short_shelf_life and has_unallocated:
            risk_reason = (
                f"Short shelf life ({batch.remaining_shelf_life_hours:.1f}h remaining) "
                f"AND significant unallocated inventory ({unallocated:.0f} kg, "
                f"{unallocated/batch.quantity_kg*100:.0f}% of batch)"
            )
        elif is_short_shelf_life:
            risk_reason = (
                f"Short shelf life ({batch.remaining_shelf_life_hours:.1f}h remaining, "
                f"threshold: {config.shelf_life_threshold_hours:.0f}h)"
            )
        else:
            risk_reason = (
                f"Significant unallocated inventory ({unallocated:.0f} kg, "
                f"{unallocated/batch.quantity_kg*100:.0f}% of batch)"
            )

        # Find the best destination for this commodity (highest remaining demand)
        best_dest = _find_best_destination(batch, scenario.destinations, shipments)

        if best_dest is None:
            # No compatible destination — recommend no discount
            recommendations.append({
                "batch_id": batch.id,
                "commodity": batch.commodity,
                "destination": "N/A",
                "risk_reason": risk_reason,
                "recommended_discount_pct": 0.0,
                "original_price_inr": 0.0,
                "discounted_price_inr": 0.0,
                "assumed_additional_demand_pct": 0.0,
                "expected_revenue_change_inr": 0.0,
                "expected_net_contribution_change_inr": 0.0,
                "recommendation": "No compatible destination found for discounting",
                "assumptions": "N/A — no viable market",
            })
            continue

        market_price = best_dest.market_price.get(batch.commodity, 0.0)
        if market_price <= 0:
            continue

        # Test each discount level
        best_discount = _evaluate_discount_levels(
            batch=batch,
            destination=best_dest,
            unallocated_qty=unallocated,
            market_price=market_price,
            config=config,
            cost_assumptions=scenario.cost_assumptions,
            transport_cost_per_kg=_avg_transport_cost(batch, best_dest, scenario.transport_options),
        )

        if best_discount is not None:
            recommendations.append(
                explain_discount(
                    batch=batch,
                    destination=best_dest,
                    discount_pct=best_discount["discount_pct"],
                    original_price=best_discount["original_price"],
                    discounted_price=best_discount["discounted_price"],
                    expected_additional_demand_pct=best_discount["additional_demand_pct"],
                    revenue_change=best_discount["revenue_change"],
                    net_contribution_change=best_discount["net_contribution_change"],
                    reason=risk_reason,
                    assumptions=best_discount["assumptions"],
                )
            )
        else:
            # System recommends no discount
            recommendations.append({
                "batch_id": batch.id,
                "commodity": batch.commodity,
                "destination": best_dest.name,
                "risk_reason": risk_reason,
                "recommended_discount_pct": 0.0,
                "original_price_inr": market_price,
                "discounted_price_inr": market_price,
                "assumed_additional_demand_pct": 0.0,
                "expected_revenue_change_inr": 0.0,
                "expected_net_contribution_change_inr": 0.0,
                "recommendation": (
                    f"No discount recommended — none of the tested discount levels "
                    f"({', '.join(f'{d*100:.0f}%' for d in config.steps if d > 0)}) "
                    f"improves expected net contribution for {batch.commodity}"
                ),
                "assumptions": (
                    f"Demand elasticity: {config.elasticity_multiplier}x. "
                    f"Market price: ₹{market_price:.2f}/kg. "
                    f"All discount levels tested but none beneficial."
                ),
            })

    return recommendations


def _find_best_destination(
    batch: InventoryBatch,
    destinations: List[Destination],
    shipments: List[ShipmentPlan],
) -> Optional[Destination]:
    """Find the best destination for discounting a batch."""
    # Compute remaining demand per destination
    fulfilled: Dict[str, Dict[str, float]] = {}
    for s in shipments:
        if s.destination_id not in fulfilled:
            fulfilled[s.destination_id] = {}
        commodity_key = None
        # Find commodity from batch_id
        for d in destinations:
            if s.destination_id == d.id:
                for c in d.demand:
                    if s.batch_id and c == batch.commodity:
                        commodity_key = c
                        break
        if commodity_key:
            fulfilled[s.destination_id][commodity_key] = \
                fulfilled[s.destination_id].get(commodity_key, 0.0) + s.allocated_qty_kg

    best_dest = None
    best_remaining = 0.0

    for dest in destinations:
        if batch.commodity not in dest.demand:
            continue
        demand = dest.demand[batch.commodity]
        fulf = fulfilled.get(dest.id, {}).get(batch.commodity, 0.0)
        remaining = demand - fulf
        if remaining > best_remaining:
            best_remaining = remaining
            best_dest = dest

    return best_dest


def _avg_transport_cost(
    batch: InventoryBatch,
    destination: Destination,
    transports: List[TransportOption],
) -> float:
    """Get average transport cost per kg to destination."""
    relevant = [t for t in transports if t.destination_id == destination.id and t.available]
    if not relevant:
        return 5.0  # Default fallback
    return sum(t.cost_per_kg for t in relevant) / len(relevant)


def _evaluate_discount_levels(
    batch: InventoryBatch,
    destination: Destination,
    unallocated_qty: float,
    market_price: float,
    config: DiscountConfig,
    cost_assumptions: CostAssumptions,
    transport_cost_per_kg: float,
) -> Optional[Dict[str, Any]]:
    """Evaluate each discount level and return the best one.

    Returns None if no discount improves expected net contribution
    (i.e., system recommends no discount).
    """
    # Baseline: no discount
    # If unallocated produce spoils, we incur spoilage cost
    no_discount_spoilage_cost = unallocated_qty * batch.spoilage_cost_per_kg
    no_discount_contribution = -no_discount_spoilage_cost  # Negative (loss from spoilage)

    best_result = None
    best_improvement = 0.0

    for discount_pct in config.steps:
        if discount_pct <= 0:
            continue

        discounted_price = market_price * (1 - discount_pct)

        # Illustrative demand response
        additional_demand_pct = discount_pct * config.elasticity_multiplier
        # Assumed additional quantity that could be sold with discount
        additional_sellable = min(
            unallocated_qty * additional_demand_pct,
            unallocated_qty  # Can't sell more than we have
        )

        # Revenue from discounted sales
        discount_revenue = additional_sellable * discounted_price

        # Costs for shipping the additional quantity
        discount_transport_cost = additional_sellable * transport_cost_per_kg
        discount_handling_cost = additional_sellable * cost_assumptions.handling_cost_per_kg

        # Remaining unsold after discount
        remaining_unsold = unallocated_qty - additional_sellable
        remaining_spoilage_cost = remaining_unsold * batch.spoilage_cost_per_kg

        # Net contribution from discounting
        discount_contribution = (
            discount_revenue
            - discount_transport_cost
            - discount_handling_cost
            - remaining_spoilage_cost
        )

        improvement = discount_contribution - no_discount_contribution

        if improvement > best_improvement:
            best_improvement = improvement
            best_result = {
                "discount_pct": discount_pct,
                "original_price": market_price,
                "discounted_price": discounted_price,
                "additional_demand_pct": additional_demand_pct,
                "additional_sellable_qty": additional_sellable,
                "revenue_change": discount_revenue,
                "net_contribution_change": improvement,
                "assumptions": (
                    f"Illustrative demand elasticity: {config.elasticity_multiplier}x "
                    f"(NOT empirically validated). "
                    f"Assumed additional demand: {additional_demand_pct*100:.1f}% at "
                    f"{discount_pct*100:.0f}% discount. "
                    f"Transport cost: ₹{transport_cost_per_kg:.2f}/kg. "
                    f"Handling cost: ₹{cost_assumptions.handling_cost_per_kg:.2f}/kg. "
                    f"Spoilage cost: ₹{batch.spoilage_cost_per_kg:.2f}/kg."
                ),
            }

    return best_result
