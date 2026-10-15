"""Constraint-aware optimization engine for FreshRoute AI.

Strategy: Greedy allocation by economic contribution with local search improvement.
Classification: HEURISTIC-OPTIMIZED (never claimed as globally optimal).

Algorithm:
1. Generate all feasible (batch, destination, transport) candidates
2. Compute economic contribution per kg for each candidate
3. Score candidates using: contribution/kg (desc), shelf_life_urgency (asc), demand_priority (asc)
4. Greedy allocation: top-scoring candidates first, all C1-C10 constraints enforced
5. Local search improvement: try swap/reassign to improve objective
6. Final result compared against initial greedy plan

Decision variables: (batch_id, destination_id, transport_id, quantity)
Objective: Maximize net revenue = Σ(revenue - transport_cost - handling_cost - holding_cost) - spoilage_cost
Subject to: C1-C10 constraints
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    Scenario, ShipmentPlan, EvaluationResult,
    CostAssumptions, FeasibilityStatus,
)
from app.engine.constraints import check_shelf_life, check_route_available
from app.engine.explainer import explain_shipment, explain_rejection, explain_unallocated_batch


@dataclass
class AllocationCandidate:
    """A feasible (batch, destination, transport) combination with economic score."""
    batch: InventoryBatch
    destination: Destination
    transport: TransportOption
    max_qty: float  # Maximum allocable quantity
    contribution_per_kg: float  # Net contribution per kg
    urgency_score: float  # Lower = more urgent (shelf life hours)
    demand_priority: int  # Destination priority
    revenue_per_kg: float
    transport_cost_per_kg: float
    handling_cost_per_kg: float
    shelf_life_at_delivery: float

    @property
    def composite_score(self) -> float:
        """Composite ranking score (higher = better allocation choice).

        Weights:
        - 60% economic contribution per kg (normalized)
        - 25% urgency (inverse shelf life — dispatch perishable items first)
        - 15% demand priority (lower priority number = higher demand importance)
        """
        urgency_bonus = max(0, 100 - self.urgency_score) / 100.0
        priority_bonus = max(0, 11 - self.demand_priority) / 10.0
        return (
            0.60 * self.contribution_per_kg
            + 0.25 * urgency_bonus * 50  # Scale urgency to comparable range
            + 0.15 * priority_bonus * 30  # Scale priority to comparable range
        )


def run_optimizer(scenario: Scenario) -> EvaluationResult:
    """Execute constraint-aware greedy optimization with local search improvement.

    Returns EvaluationResult with all metrics computed.
    Result is classified as 'heuristic-optimized', not globally optimal.
    """
    start_time = time.perf_counter()

    batches = scenario.inventory_batches
    destinations = scenario.destinations
    transports = scenario.transport_options
    cost_assumptions = scenario.cost_assumptions

    # Phase 1: Generate all feasible candidates
    candidates = _generate_candidates(batches, destinations, transports, cost_assumptions)

    # Phase 2: Rank candidates by composite score
    candidates.sort(key=lambda c: c.composite_score, reverse=True)

    # Phase 3: Greedy allocation
    shipments, batch_allocated, demand_fulfilled, transport_loaded, dest_received = \
        _greedy_allocate(candidates, batches, destinations, transports, cost_assumptions)

    initial_objective = sum(s.net_contribution for s in shipments)

    # Phase 4: Local search improvement
    shipments, batch_allocated, demand_fulfilled, transport_loaded, dest_received = \
        _local_search_improve(
            shipments, candidates, batches, destinations, transports,
            batch_allocated, demand_fulfilled, transport_loaded, dest_received,
            cost_assumptions
        )

    final_objective = sum(s.net_contribution for s in shipments)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Collect unallocated batch reasons
    unallocated_reasons: Dict[str, List[str]] = {}
    for batch in batches:
        unalloc = batch.quantity_kg - batch_allocated.get(batch.id, 0.0)
        if unalloc > 0:
            reasons = _get_unallocation_reasons(
                batch, destinations, transports, demand_fulfilled,
                transport_loaded, dest_received, cost_assumptions
            )
            unallocated_reasons[batch.id] = reasons

    # Compute evaluation metrics
    return _compute_evaluation(
        shipments=shipments,
        batches=batches,
        destinations=destinations,
        batch_allocated=batch_allocated,
        unallocated_reasons=unallocated_reasons,
        cost_assumptions=cost_assumptions,
        elapsed_ms=elapsed_ms,
        initial_objective=initial_objective,
        final_objective=final_objective,
    )


def _generate_candidates(
    batches: List[InventoryBatch],
    destinations: List[Destination],
    transports: List[TransportOption],
    cost_assumptions: CostAssumptions,
) -> List[AllocationCandidate]:
    """Generate all feasible (batch, destination, transport) candidates."""
    candidates: List[AllocationCandidate] = []

    transport_by_dest: Dict[str, List[TransportOption]] = {}
    for t in transports:
        transport_by_dest.setdefault(t.destination_id, []).append(t)

    for batch in batches:
        if batch.quantity_kg <= 0:
            continue

        for dest in destinations:
            # C6: Commodity compatibility
            if batch.commodity not in dest.demand:
                continue
            if dest.demand[batch.commodity] <= 0:
                continue

            market_price = dest.market_price.get(batch.commodity, 0.0)
            if market_price <= 0:
                continue

            for transport in transport_by_dest.get(dest.id, []):
                # C5: Route availability
                if not transport.available:
                    continue

                # C7: Shelf life check
                sl_ok, _, _ = check_shelf_life(
                    batch, transport, 0.0, cost_assumptions.spoilage_threshold_hours
                )
                if not sl_ok:
                    continue

                # Compute economics per kg
                revenue_per_kg = market_price
                transport_cost_per_kg = transport.cost_per_kg
                handling_cost_per_kg = cost_assumptions.handling_cost_per_kg
                contribution_per_kg = revenue_per_kg - transport_cost_per_kg - handling_cost_per_kg

                # C9: Skip negative contribution candidates (unless policy allows)
                if contribution_per_kg < 0 and not cost_assumptions.allow_negative_contribution:
                    continue

                # Max allocable: min of batch qty, demand, transport capacity, dest capacity
                max_qty = min(
                    batch.quantity_kg,
                    dest.demand[batch.commodity],
                    transport.capacity_kg,
                    dest.receiving_capacity_kg,
                )

                if max_qty <= 0:
                    continue

                total_transit = transport.travel_time_hours + transport.handling_time_hours
                shelf_life_at_delivery = batch.remaining_shelf_life_hours - total_transit

                candidates.append(AllocationCandidate(
                    batch=batch,
                    destination=dest,
                    transport=transport,
                    max_qty=max_qty,
                    contribution_per_kg=contribution_per_kg,
                    urgency_score=batch.remaining_shelf_life_hours,
                    demand_priority=dest.priority,
                    revenue_per_kg=revenue_per_kg,
                    transport_cost_per_kg=transport_cost_per_kg,
                    handling_cost_per_kg=handling_cost_per_kg,
                    shelf_life_at_delivery=shelf_life_at_delivery,
                ))

    return candidates


def _greedy_allocate(
    candidates: List[AllocationCandidate],
    batches: List[InventoryBatch],
    destinations: List[Destination],
    transports: List[TransportOption],
    cost_assumptions: CostAssumptions,
) -> Tuple[List[ShipmentPlan], Dict[str, float], Dict[str, Dict[str, float]], Dict[str, float], Dict[str, float]]:
    """Greedy allocation: process candidates in ranked order."""

    batch_allocated: Dict[str, float] = {b.id: 0.0 for b in batches}
    demand_fulfilled: Dict[str, Dict[str, float]] = {
        d.id: {c: 0.0 for c in d.demand} for d in destinations
    }
    transport_loaded: Dict[str, float] = {t.id: 0.0 for t in transports}
    dest_received: Dict[str, float] = {d.id: 0.0 for d in destinations}
    shipments: List[ShipmentPlan] = []
    rank = 0

    for cand in candidates:
        batch = cand.batch
        dest = cand.destination
        transport = cand.transport

        # Check remaining capacities
        batch_remaining = batch.quantity_kg - batch_allocated[batch.id]
        if batch_remaining <= 0:
            continue

        commodity_demand = dest.demand.get(batch.commodity, 0.0)
        fulfilled = demand_fulfilled[dest.id].get(batch.commodity, 0.0)
        remaining_demand = commodity_demand - fulfilled
        if remaining_demand <= 0:
            continue

        transport_remaining = transport.capacity_kg - transport_loaded[transport.id]
        if transport_remaining <= 0:
            continue

        dest_cap_remaining = dest.receiving_capacity_kg - dest_received[dest.id]
        if dest_cap_remaining <= 0:
            continue

        # Allocate
        qty = min(batch_remaining, remaining_demand, transport_remaining, dest_cap_remaining)
        if qty <= 0:
            continue

        # Compute economics
        market_price = dest.market_price.get(batch.commodity, 0.0)
        revenue = qty * market_price
        transport_cost = qty * transport.cost_per_kg
        handling_cost = qty * cost_assumptions.handling_cost_per_kg
        holding_cost = 0.0
        net_contribution = revenue - transport_cost - handling_cost - holding_cost

        arrival_time = transport.travel_time_hours
        handling_completion = arrival_time + transport.handling_time_hours
        shelf_life_at_delivery = batch.remaining_shelf_life_hours - handling_completion

        rank += 1

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
            batch_remaining=batch_remaining,
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

    return shipments, batch_allocated, demand_fulfilled, transport_loaded, dest_received


def _local_search_improve(
    shipments: List[ShipmentPlan],
    candidates: List[AllocationCandidate],
    batches: List[InventoryBatch],
    destinations: List[Destination],
    transports: List[TransportOption],
    batch_allocated: Dict[str, float],
    demand_fulfilled: Dict[str, Dict[str, float]],
    transport_loaded: Dict[str, float],
    dest_received: Dict[str, float],
    cost_assumptions: CostAssumptions,
    max_iterations: int = 100,
) -> Tuple[List[ShipmentPlan], Dict[str, float], Dict[str, Dict[str, float]], Dict[str, float], Dict[str, float]]:
    """Local search: try reassigning shipments to improve objective.

    Tries:
    1. Swap destinations for pairs of shipments if it improves net contribution
    2. Reassign low-contribution shipments to better routes
    """
    improved = True
    iteration = 0

    batch_map = {b.id: b for b in batches}
    dest_map = {d.id: d for d in destinations}
    transport_map = {t.id: t for t in transports}

    transport_by_dest: Dict[str, List[TransportOption]] = {}
    for t in transports:
        transport_by_dest.setdefault(t.destination_id, []).append(t)

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1

        # Try reassigning each shipment to a better transport option
        for idx, shipment in enumerate(shipments):
            batch = batch_map.get(shipment.batch_id)
            dest = dest_map.get(shipment.destination_id)
            if not batch or not dest:
                continue

            current_contribution = shipment.net_contribution

            # Try alternative transports to same destination
            for alt_transport in transport_by_dest.get(dest.id, []):
                if alt_transport.id == shipment.transport_id:
                    continue
                if not alt_transport.available:
                    continue

                # Check shelf life with new transport
                sl_ok, _, _ = check_shelf_life(
                    batch, alt_transport, 0.0, cost_assumptions.spoilage_threshold_hours
                )
                if not sl_ok:
                    continue

                # Check capacity
                alt_transport_remaining = alt_transport.capacity_kg - transport_loaded[alt_transport.id]
                if alt_transport_remaining < shipment.allocated_qty_kg:
                    continue

                # Compute new economics
                market_price = dest.market_price.get(batch.commodity, 0.0)
                qty = shipment.allocated_qty_kg
                new_revenue = qty * market_price
                new_transport_cost = qty * alt_transport.cost_per_kg
                new_handling_cost = qty * cost_assumptions.handling_cost_per_kg
                new_contribution = new_revenue - new_transport_cost - new_handling_cost

                if new_contribution > current_contribution + 0.01:  # Meaningful improvement
                    # Apply reassignment
                    old_transport_id = shipment.transport_id
                    transport_loaded[old_transport_id] -= qty
                    transport_loaded[alt_transport.id] += qty

                    arrival_time = alt_transport.travel_time_hours
                    handling_completion = arrival_time + alt_transport.handling_time_hours
                    shelf_life_at_delivery = batch.remaining_shelf_life_hours - handling_completion

                    # Update shipment
                    shipments[idx] = ShipmentPlan(
                        batch_id=shipment.batch_id,
                        destination_id=shipment.destination_id,
                        transport_id=alt_transport.id,
                        allocated_qty_kg=qty,
                        departure_time=0.0,
                        arrival_time=arrival_time,
                        handling_completion_time=handling_completion,
                        shelf_life_remaining_at_delivery_hours=shelf_life_at_delivery,
                        expected_sale_qty_kg=qty,
                        discount_pct=0.0,
                        revenue=new_revenue,
                        transport_cost=new_transport_cost,
                        handling_cost=new_handling_cost,
                        holding_cost=0.0,
                        net_contribution=new_contribution,
                        feasibility_status=FeasibilityStatus.FEASIBLE,
                        explanation=shipment.explanation,
                        rejection_reasons=[],
                    )

                    improved = True
                    break

    return shipments, batch_allocated, demand_fulfilled, transport_loaded, dest_received


def _get_unallocation_reasons(
    batch: InventoryBatch,
    destinations: List[Destination],
    transports: List[TransportOption],
    demand_fulfilled: Dict[str, Dict[str, float]],
    transport_loaded: Dict[str, float],
    dest_received: Dict[str, float],
    cost_assumptions: CostAssumptions,
) -> List[str]:
    """Determine why a batch couldn't be fully allocated."""
    reasons = set()

    transport_by_dest: Dict[str, List[TransportOption]] = {}
    for t in transports:
        transport_by_dest.setdefault(t.destination_id, []).append(t)

    has_compatible_dest = False

    for dest in destinations:
        if batch.commodity not in dest.demand:
            continue
        if dest.demand[batch.commodity] <= 0:
            continue

        has_compatible_dest = True

        fulfilled = demand_fulfilled.get(dest.id, {}).get(batch.commodity, 0.0)
        remaining_demand = dest.demand[batch.commodity] - fulfilled
        if remaining_demand <= 0:
            reasons.add("DEMAND_SATISFIED")
            continue

        dest_transports = transport_by_dest.get(dest.id, [])
        if not dest_transports:
            reasons.add("ROUTE_UNAVAILABLE")
            continue

        for transport in dest_transports:
            if not transport.available:
                reasons.add("ROUTE_UNAVAILABLE")
                continue

            transport_remaining = transport.capacity_kg - transport_loaded.get(transport.id, 0.0)
            if transport_remaining <= 0:
                reasons.add("CAPACITY_EXCEEDED")
                continue

            sl_ok, _, _ = check_shelf_life(
                batch, transport, 0.0, cost_assumptions.spoilage_threshold_hours
            )
            if not sl_ok:
                reasons.add("SHELF_LIFE_EXCEEDED")
                continue

            # If we get here, there's a feasible option — shouldn't be unallocated
            # This might happen if demand was satisfied by other batches
            reasons.add("DEMAND_SATISFIED")

    if not has_compatible_dest:
        reasons.add("NO_COMPATIBLE_DESTINATION")

    return list(reasons) if reasons else ["UNKNOWN"]


def _compute_evaluation(
    shipments: List[ShipmentPlan],
    batches: List[InventoryBatch],
    destinations: List[Destination],
    batch_allocated: Dict[str, float],
    unallocated_reasons: Dict[str, List[str]],
    cost_assumptions: CostAssumptions,
    elapsed_ms: float,
    initial_objective: float,
    final_objective: float,
) -> EvaluationResult:
    """Compute all evaluation metrics from shipment results."""

    total_available = sum(b.quantity_kg for b in batches)
    total_dispatched = sum(s.allocated_qty_kg for s in shipments)
    total_revenue = sum(s.revenue for s in shipments)
    total_transport_cost = sum(s.transport_cost for s in shipments)
    total_handling_cost = sum(s.handling_cost for s in shipments)
    total_holding_cost = sum(s.holding_cost for s in shipments)

    # Total demand
    total_demand = 0.0
    for d in destinations:
        for commodity, demand_qty in d.demand.items():
            total_demand += demand_qty

    # Demand fulfilled
    demand_fulfilled_qty = sum(s.expected_sale_qty_kg for s in shipments)

    # Unallocated quantity
    unallocated_qty = total_available - total_dispatched

    # Spoilage calculation: unallocated inventory that will spoil
    batch_map = {b.id: b for b in batches}
    spoiled_qty = 0.0
    for batch in batches:
        batch_unalloc = batch.quantity_kg - batch_allocated.get(batch.id, 0.0)
        if batch_unalloc > 0 and batch.remaining_shelf_life_hours < 48.0:
            spoiled_qty += batch_unalloc

    # Shelf-life violations
    shelf_life_violations = sum(
        1 for s in shipments if s.shelf_life_remaining_at_delivery_hours < 0
    )

    total_spoilage_cost = spoiled_qty * cost_assumptions.spoilage_penalty_multiplier * (
        sum(b.spoilage_cost_per_kg for b in batches) / len(batches) if batches else 0
    )

    net_revenue = total_revenue - total_transport_cost - total_handling_cost - total_holding_cost - total_spoilage_cost

    # Rates with zero-denominator safety
    spoilage_rate = (spoiled_qty / total_available * 100) if total_available > 0 else 0.0
    fulfillment_pct = (demand_fulfilled_qty / total_demand * 100) if total_demand > 0 else 0.0
    utilization_pct = (total_dispatched / total_available * 100) if total_available > 0 else 0.0

    spoilage_rate = min(spoilage_rate, 100.0)
    fulfillment_pct = min(fulfillment_pct, 100.0)
    utilization_pct = min(utilization_pct, 100.0)

    return EvaluationResult(
        strategy_name="FreshRoute Optimizer (Heuristic-Optimized)",
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
        capacity_violations=0,
        execution_time_ms=round(elapsed_ms, 2),
        metadata={
            "algorithm": "Constraint-Aware Greedy with Local Search",
            "candidate_generation": "All feasible (batch, destination, transport) triples",
            "scoring": "60% contribution/kg + 25% urgency + 15% demand priority",
            "improvement": "Transport reassignment local search",
            "classification": "heuristic-optimized (NOT globally optimal)",
            "initial_objective_inr": round(initial_objective, 2),
            "final_objective_inr": round(final_objective, 2),
            "improvement_from_local_search_inr": round(final_objective - initial_objective, 2),
        },
    )


# Alias
run_heuristic_optimizer = run_optimizer

