"""Decision explanation generator for FreshRoute AI.

Produces structured, inspectable explanations for every allocation decision.
Explanations are generated from actual inputs and constraint checks — not post-hoc AI prose.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    CostAssumptions, ShipmentPlan, RejectionReasonCode,
)


def explain_shipment(
    batch: InventoryBatch,
    destination: Destination,
    transport: TransportOption,
    qty: float,
    revenue: float,
    transport_cost: float,
    handling_cost: float,
    holding_cost: float,
    net_contribution: float,
    shelf_life_at_delivery: float,
    demand_remaining: float,
    batch_remaining: float,
    discount_pct: float = 0.0,
    rank: int = 0,
) -> Dict[str, Any]:
    """Generate a structured explanation for a shipment allocation.

    Returns a dictionary with human-readable reasons for each decision dimension.
    """
    market_price = destination.market_price.get(batch.commodity, 0.0)
    contribution_per_kg = net_contribution / qty if qty > 0 else 0.0

    explanation = {
        "why_this_batch": (
            f"Batch {batch.id} contains {batch.quantity_kg:.0f} kg of {batch.commodity} "
            f"with {batch.remaining_shelf_life_hours:.1f}h remaining shelf life. "
            f"{'URGENT: shelf life is critically low. ' if batch.remaining_shelf_life_hours < 24 else ''}"
            f"Allocated {qty:.0f} kg ({qty/batch.quantity_kg*100:.0f}% of batch)."
        ),
        "why_this_destination": (
            f"{destination.name} has {demand_remaining:.0f} kg remaining demand for {batch.commodity} "
            f"at ₹{market_price:.2f}/kg (priority {destination.priority}). "
            f"This destination offers the {'highest' if rank <= 3 else 'a competitive'} "
            f"net contribution among feasible options."
        ),
        "why_this_route": (
            f"Transport via {transport.id} ({transport.origin} → {destination.name}): "
            f"travel {transport.travel_time_hours:.1f}h + handling {transport.handling_time_hours:.1f}h = "
            f"{transport.travel_time_hours + transport.handling_time_hours:.1f}h total transit. "
            f"Cost: ₹{transport.cost_per_kg:.2f}/kg. "
            f"Capacity: {transport.capacity_kg:.0f} kg."
        ),
        "why_this_quantity": (
            f"Quantity {qty:.0f} kg is the minimum of: "
            f"batch remaining ({batch_remaining:.0f} kg), "
            f"destination demand ({demand_remaining:.0f} kg), "
            f"transport capacity ({transport.capacity_kg:.0f} kg)."
        ),
        "dispatch_priority": (
            f"Priority rank #{rank}. "
            f"{'High urgency due to short shelf life. ' if batch.remaining_shelf_life_hours < 36 else ''}"
            f"Net contribution: ₹{net_contribution:.2f} (₹{contribution_per_kg:.2f}/kg)."
        ),
        "economic_tradeoff": (
            f"Revenue: ₹{revenue:.2f}"
            f"{f' (after {discount_pct*100:.0f}% discount)' if discount_pct > 0 else ''}"
            f" | Transport: ₹{transport_cost:.2f}"
            f" | Handling: ₹{handling_cost:.2f}"
            f" | Holding: ₹{holding_cost:.2f}"
            f" | Net: ₹{net_contribution:.2f}"
        ),
        "shelf_life_analysis": (
            f"Shelf life at delivery: {shelf_life_at_delivery:.1f}h "
            f"(original {batch.remaining_shelf_life_hours:.1f}h - "
            f"transit {transport.travel_time_hours + transport.handling_time_hours:.1f}h). "
            f"{'Adequate margin.' if shelf_life_at_delivery > 12 else 'Tight margin — monitor closely.'}"
        ),
        "what_makes_infeasible": (
            f"This allocation would become infeasible if: "
            f"travel time exceeds {batch.remaining_shelf_life_hours - transport.handling_time_hours:.1f}h, "
            f"or transport cost rises above ₹{market_price:.2f}/kg (breakeven), "
            f"or remaining demand drops below {qty:.0f} kg."
        ),
    }

    return explanation


def explain_rejection(
    batch: InventoryBatch,
    destination: Optional[Destination],
    transport: Optional[TransportOption],
    reason_codes: List[str],
    details: List[str],
) -> Dict[str, Any]:
    """Generate a structured explanation for a rejected allocation candidate."""
    dest_name = destination.name if destination else "N/A"
    transport_id = transport.id if transport else "N/A"

    explanation = {
        "batch_id": batch.id,
        "commodity": batch.commodity,
        "quantity_kg": batch.quantity_kg,
        "remaining_shelf_life_hours": batch.remaining_shelf_life_hours,
        "destination": dest_name,
        "transport": transport_id,
        "reason_codes": reason_codes,
        "details": details,
        "summary": _summarize_rejection(reason_codes, batch, destination, transport),
    }

    return explanation


def _summarize_rejection(
    reason_codes: List[str],
    batch: InventoryBatch,
    destination: Optional[Destination],
    transport: Optional[TransportOption],
) -> str:
    """Generate a human-readable rejection summary."""
    parts = []

    if RejectionReasonCode.SHELF_LIFE_EXCEEDED.value in reason_codes:
        if transport:
            total_transit = transport.travel_time_hours + transport.handling_time_hours
            parts.append(
                f"Shelf life ({batch.remaining_shelf_life_hours:.1f}h) insufficient "
                f"for transit ({total_transit:.1f}h)"
            )

    if RejectionReasonCode.CAPACITY_EXCEEDED.value in reason_codes:
        parts.append("Transport capacity fully utilized")

    if RejectionReasonCode.DEMAND_SATISFIED.value in reason_codes:
        dest_name = destination.name if destination else "destination"
        parts.append(f"Demand at {dest_name} already satisfied")

    if RejectionReasonCode.ROUTE_UNAVAILABLE.value in reason_codes:
        parts.append("Route/transport currently unavailable")

    if RejectionReasonCode.NEGATIVE_CONTRIBUTION.value in reason_codes:
        parts.append("Expected net contribution is negative")

    if RejectionReasonCode.NO_COMPATIBLE_DESTINATION.value in reason_codes:
        parts.append(f"No destination has demand for {batch.commodity}")

    if RejectionReasonCode.BATCH_EXHAUSTED.value in reason_codes:
        parts.append("Entire batch quantity already allocated")

    if RejectionReasonCode.DESTINATION_CAPACITY_EXCEEDED.value in reason_codes:
        parts.append("Destination receiving capacity exceeded")

    if RejectionReasonCode.COMMODITY_INCOMPATIBLE.value in reason_codes:
        parts.append(f"Destination does not accept {batch.commodity}")

    return "; ".join(parts) if parts else "Rejected for undetermined reason"


def explain_unallocated_batch(
    batch: InventoryBatch,
    all_reason_codes: List[str],
) -> Dict[str, Any]:
    """Explain why a batch has no allocation."""
    unique_reasons = list(set(all_reason_codes))
    return {
        "batch_id": batch.id,
        "commodity": batch.commodity,
        "quantity_kg": batch.quantity_kg,
        "remaining_shelf_life_hours": batch.remaining_shelf_life_hours,
        "status": "UNALLOCATED",
        "reason_codes": unique_reasons,
        "summary": (
            f"Batch {batch.id} ({batch.quantity_kg:.0f} kg {batch.commodity}, "
            f"{batch.remaining_shelf_life_hours:.1f}h shelf life) could not be allocated. "
            f"Reasons: {', '.join(unique_reasons)}"
        ),
    }


def explain_discount(
    batch: InventoryBatch,
    destination: Optional[Destination],
    discount_pct: float,
    original_price: float,
    discounted_price: float,
    expected_additional_demand_pct: float,
    revenue_change: float,
    net_contribution_change: float,
    reason: str,
    assumptions: str,
) -> Dict[str, Any]:
    """Generate explanation for a discount recommendation."""
    return {
        "batch_id": batch.id,
        "commodity": batch.commodity,
        "destination": destination.name if destination else "General",
        "risk_reason": reason,
        "recommended_discount_pct": round(discount_pct * 100, 1),
        "original_price_inr": round(original_price, 2),
        "discounted_price_inr": round(discounted_price, 2),
        "assumed_additional_demand_pct": round(expected_additional_demand_pct * 100, 1),
        "expected_revenue_change_inr": round(revenue_change, 2),
        "expected_net_contribution_change_inr": round(net_contribution_change, 2),
        "recommendation": (
            f"Apply {discount_pct*100:.0f}% discount on {batch.commodity} "
            f"(₹{original_price:.2f} → ₹{discounted_price:.2f}/kg). "
            f"Expected net contribution change: ₹{net_contribution_change:+.2f}"
        ),
        "assumptions": assumptions,
    }
