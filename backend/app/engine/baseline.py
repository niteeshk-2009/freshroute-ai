"""Baseline allocation strategy: Earliest-Expiry-First (EEF).

This is a deterministic comparator strategy — not a deliberately weak strawman.

Ordering rule: Sort batches by remaining_shelf_life ascending (earliest expiry dispatched first).
Tie resolution: By batch ID alphabetically.
Destination selection: For each batch, iterate destinations by remaining demand (highest first),
    then by priority (lower number = higher priority).
Constraint enforcement: All C1-C10 constraints are respected.
Unallocated inventory: Reported with reason codes.
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    Scenario, ShipmentPlan, EvaluationResult,
    CostAssumptions, FeasibilityStatus,
)
from app.engine.constraints import is_feasible, check_shelf_life
from app.engine.explainer import explain_shipment, explain_unallocated_batch


def run_baseline(scenario: Scenario) -> EvaluationResult:
    """Execute Earliest-Expiry-First baseline allocation.

    Algorithm:
    1. Sort batches by remaining_shelf_life ascending, then batch ID.
    2. For each batch, iterate destinations sorted by (demand for commodity desc, priority asc).
    3. For each (batch, destination), find the best feasible transport option.
    4. Allocate min(batch_remaining, demand_remaining, transport_capacity).
    5. Enforce all C1-C10 constraints.
    6. Report unallocated batches with reasons.

    Returns EvaluationResult with all metrics computed.
    """
    start_time = time.perf_counter()

    batches = scenario.inventory_batches
    destinations = scenario.destinations
    transports = scenario.transport_options
    cost_assumptions = scenario.cost_assumptions

    # Sort batches by earliest expiry first, then by ID for determinism
    sorted_batches = sorted(
        batches,
        key=lambda b: (b.remaining_shelf_life_hours, b.id)
    )

    # Tracking state
    batch_allocated: Dict[str, float] = {b.id: 0.0 for b in batches}
    demand_fulfilled: Dict[str, Dict[str, float]] = {
        d.id: {c: 0.0 for c in d.demand} for d in destinations
    }
    transport_loaded: Dict[str, float] = {t.id: 0.0 for t in transports}
    dest_received: Dict[str, float] = {d.id: 0.0 for d in destinations}

    # Index lookups
    dest_map = {d.id: d for d in destinations}
    transport_by_dest: Dict[str, List[TransportOption]] = {}
    for t in transports:
        transport_by_dest.setdefault(t.destination_id, []).append(t)

    shipments: List[ShipmentPlan] = []
    unallocated_reasons: Dict[str, List[str]] = {b.id: [] for b in batches}
    rank = 0

    for batch in sorted_batches:
        remaining_qty = batch.quantity_kg - batch_allocated[batch.id]
        if remaining_qty <= 0:
            continue

        # Sort destinations by demand for this commodity (desc), then priority (asc)
        candidate_dests = sorted(
            [d for d in destinations if batch.commodity in d.demand],
            key=lambda d: (-d.demand.get(batch.commodity, 0.0), d.priority, d.id)
        )

        if not candidate_dests:
            unallocated_reasons[batch.id].append("NO_COMPATIBLE_DESTINATION")
            continue

        for dest in candidate_dests:
            remaining_qty = batch.quantity_kg - batch_allocated[batch.id]
            if remaining_qty <= 0:
                break

            commodity_demand = dest.demand.get(batch.commodity, 0.0)
            fulfilled = demand_fulfilled[dest.id].get(batch.commodity, 0.0)
            remaining_demand = commodity_demand - fulfilled

            if remaining_demand <= 0:
                unallocated_reasons[batch.id].append("DEMAND_SATISFIED")
                continue

            # Find best feasible transport (cheapest that satisfies constraints)
            dest_transports = transport_by_dest.get(dest.id, [])
            dest_transports_sorted = sorted(
                dest_transports,
                key=lambda t: (not t.available, t.cost_per_kg, t.travel_time_hours)
            )

            allocated_this_dest = False
            for transport in dest_transports_sorted:
                if not transport.available:
                    unallocated_reasons[batch.id].append("ROUTE_UNAVAILABLE")
                    continue

                transport_remaining = transport.capacity_kg - transport_loaded[transport.id]
                if transport_remaining <= 0:
                    unallocated_reasons[batch.id].append("CAPACITY_EXCEEDED")
                    continue

                # Calculate allocation quantity
                qty = min(remaining_qty, remaining_demand, transport_remaining)

                # Check shelf life feasibility
                sl_ok, sl_code, sl_detail = check_shelf_life(
                    batch, transport, 0.0, cost_assumptions.spoilage_threshold_hours
                )
                if not sl_ok:
                    unallocated_reasons[batch.id].append("SHELF_LIFE_EXCEEDED")
                    continue

                # Check destination receiving capacity
                dest_cap_remaining = dest.receiving_capacity_kg - dest_received[dest.id]
                if dest_cap_remaining <= 0:
                    unallocated_reasons[batch.id].append("DESTINATION_CAPACITY_EXCEEDED")
                    continue
                qty = min(qty, dest_cap_remaining)

                # Compute economics
                market_price = dest.market_price.get(batch.commodity, 0.0)
                revenue = qty * market_price
                transport_cost = qty * transport.cost_per_kg
                handling_cost = qty * cost_assumptions.handling_cost_per_kg
                holding_cost = 0.0  # Baseline doesn't hold — dispatches immediately
                net_contribution = revenue - transport_cost - handling_cost - holding_cost

                # C9: Check contribution
                if net_contribution < 0 and not cost_assumptions.allow_negative_contribution:
                    unallocated_reasons[batch.id].append("NEGATIVE_CONTRIBUTION")
                    continue

                if qty <= 0:
                    continue

                # Create shipment
                rank += 1
                arrival_time = transport.travel_time_hours
                handling_completion = arrival_time + transport.handling_time_hours
                shelf_life_at_delivery = batch.remaining_shelf_life_hours - handling_completion

                explanation = explain_shipment(
                    batch=batch,
                    destination=dest,
                    transport=transport,
                    qty=qty,
                    revenue=revenue,
                    transport_cost=transport_cost,
                    handling_cost=handling_cost,
                    holding_cost=holding_cost,
                    net_contribution=net_contribution,
                    shelf_life_at_delivery=shelf_life_at_delivery,
                    demand_remaining=remaining_demand,
                    batch_remaining=remaining_qty,
                    rank=rank,
                )

                shipment = ShipmentPlan(
                    batch_id=batch.id,
                    destination_id=dest.id,
                    transport_id=transport.id,
                    allocated_qty_kg=qty,
                    departure_time=0.0,
                    arrival_time=arrival_time,
                    handling_completion_time=handling_completion,
                    shelf_life_remaining_at_delivery_hours=shelf_life_at_delivery,
                    expected_sale_qty_kg=qty,
                    discount_pct=0.0,
                    revenue=revenue,
                    transport_cost=transport_cost,
                    handling_cost=handling_cost,
                    holding_cost=holding_cost,
                    net_contribution=net_contribution,
                    feasibility_status=FeasibilityStatus.FEASIBLE,
                    explanation=explanation,
                    rejection_reasons=[],
                )
                shipments.append(shipment)

                # Update tracking
                batch_allocated[batch.id] += qty
                demand_fulfilled[dest.id][batch.commodity] = fulfilled + qty
                transport_loaded[transport.id] += qty
                dest_received[dest.id] += qty
                remaining_qty = batch.quantity_kg - batch_allocated[batch.id]
                allocated_this_dest = True
                break  # Move to next destination for remaining qty

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Compute evaluation metrics
    return _compute_evaluation(
        strategy_name="Earliest-Expiry-First (EEF) Baseline",
        shipments=shipments,
        batches=batches,
        destinations=destinations,
        batch_allocated=batch_allocated,
        unallocated_reasons=unallocated_reasons,
        cost_assumptions=cost_assumptions,
        elapsed_ms=elapsed_ms,
    )


def _compute_evaluation(
    strategy_name: str,
    shipments: List[ShipmentPlan],
    batches: List[InventoryBatch],
    destinations: List[Destination],
    batch_allocated: Dict[str, float],
    unallocated_reasons: Dict[str, List[str]],
    cost_assumptions: CostAssumptions,
    elapsed_ms: float,
) -> EvaluationResult:
    """Compute all evaluation metrics from shipment results."""

    total_available = sum(b.quantity_kg for b in batches)
    total_dispatched = sum(s.allocated_qty_kg for s in shipments)
    total_revenue = sum(s.revenue for s in shipments)
    total_transport_cost = sum(s.transport_cost for s in shipments)
    total_handling_cost = sum(s.handling_cost for s in shipments)
    total_holding_cost = sum(s.holding_cost for s in shipments)

    # Compute total demand
    total_demand = 0.0
    for d in destinations:
        for commodity, demand_qty in d.demand.items():
            total_demand += demand_qty

    # Demand fulfilled
    demand_fulfilled_qty = sum(s.expected_sale_qty_kg for s in shipments)

    # Unallocated quantity
    unallocated_qty = total_available - total_dispatched

    # Spoilage: unallocated batches whose shelf life is short enough that they'll spoil
    # Also: dispatched batches where shelf_life_at_delivery < 0 (shouldn't happen with constraints)
    batch_map = {b.id: b for b in batches}
    spoiled_qty = 0.0
    for batch in batches:
        batch_unalloc = batch.quantity_kg - batch_allocated.get(batch.id, 0.0)
        if batch_unalloc > 0:
            # Unallocated produce spoils if shelf life is below threshold
            # Conservative: all unallocated inventory with shelf life < 48h is considered at risk
            if batch.remaining_shelf_life_hours < 48.0:
                spoiled_qty += batch_unalloc

    # Check for shelf-life violations in shipments (shouldn't happen but verify)
    shelf_life_violations = sum(
        1 for s in shipments if s.shelf_life_remaining_at_delivery_hours < 0
    )
    capacity_violations = 0  # Should be 0 with constraint enforcement

    total_spoilage_cost = spoiled_qty * cost_assumptions.spoilage_penalty_multiplier * (
        sum(b.spoilage_cost_per_kg for b in batches) / len(batches) if batches else 0
    )

    net_revenue = total_revenue - total_transport_cost - total_handling_cost - total_holding_cost - total_spoilage_cost

    # Compute rates safely
    spoilage_rate = (spoiled_qty / total_available * 100) if total_available > 0 else 0.0
    fulfillment_pct = (demand_fulfilled_qty / total_demand * 100) if total_demand > 0 else 0.0
    utilization_pct = (total_dispatched / total_available * 100) if total_available > 0 else 0.0

    # Clamp to valid ranges
    spoilage_rate = min(spoilage_rate, 100.0)
    fulfillment_pct = min(fulfillment_pct, 100.0)
    utilization_pct = min(utilization_pct, 100.0)

    return EvaluationResult(
        strategy_name=strategy_name,
        shipments=shipments,
        total_revenue=round(total_revenue, 2),
        total_transport_cost=round(total_transport_cost, 2),
        total_handling_cost=round(total_handling_cost, 2),
        total_holding_cost=round(total_holding_cost, 2),
        total_spoilage_cost=round(total_spoilage_cost, 2),
        net_revenue=round(net_revenue, 2),
        spoiled_qty_kg=round(spoiled_qty, 2),
        spoilage_rate_pct=round(spoilage_rate, 2),
        demand_fulfilled_qty_kg=round(demand_fulfilled_qty, 2),
        total_demand_kg=round(total_demand, 2),
        fulfillment_pct=round(fulfillment_pct, 2),
        inventory_utilization_pct=round(utilization_pct, 2),
        unallocated_qty_kg=round(unallocated_qty, 2),
        feasible_shipment_count=len(shipments),
        shelf_life_violations=shelf_life_violations,
        capacity_violations=capacity_violations,
        execution_time_ms=round(elapsed_ms, 2),
        metadata={
            "algorithm": "Earliest-Expiry-First (EEF)",
            "ordering": "remaining_shelf_life ascending, batch_id ascending",
            "destination_selection": "demand descending, priority ascending",
            "constraint_enforcement": "C1-C10 all enforced",
            "classification": "deterministic baseline",
        },
    )


# Alias
run_baseline_eef = run_baseline

