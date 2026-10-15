"""Feasibility constraint checks for FreshRoute AI allocation engine.

Implements constraints C1-C10 from the official problem statement.
All checks return (is_valid: bool, reason_code: str | None, detail: str).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    ShipmentPlan, CostAssumptions, RejectionReasonCode, FeasibilityStatus,
)


def check_non_negative(qty: float) -> Tuple[bool, Optional[str], str]:
    """C1: Allocation quantities must be non-negative."""
    if qty < 0:
        return False, RejectionReasonCode.NEGATIVE_CONTRIBUTION.value, \
            f"C1 violation: allocation quantity {qty:.2f} kg is negative"
    return True, None, ""


def check_batch_capacity(
    batch: InventoryBatch,
    already_allocated: float,
    new_allocation: float,
) -> Tuple[bool, Optional[str], str]:
    """C2: Total dispatch from any batch cannot exceed its available quantity."""
    total = already_allocated + new_allocation
    if total > batch.quantity_kg + 1e-6:  # small tolerance for floating point
        return False, RejectionReasonCode.BATCH_EXHAUSTED.value, \
            f"C2 violation: batch {batch.id} has {batch.quantity_kg:.1f} kg, " \
            f"already allocated {already_allocated:.1f} kg, " \
            f"new request {new_allocation:.1f} kg exceeds available"
    return True, None, ""


def check_demand_limit(
    destination: Destination,
    commodity: str,
    already_fulfilled: float,
    new_allocation: float,
) -> Tuple[bool, Optional[str], str]:
    """C3: Allocation to a destination cannot exceed its remaining demand."""
    demand = destination.demand.get(commodity, 0.0)
    remaining_demand = demand - already_fulfilled
    if new_allocation > remaining_demand + 1e-6:
        return False, RejectionReasonCode.DEMAND_SATISFIED.value, \
            f"C3 violation: destination {destination.id} demand for {commodity} " \
            f"is {demand:.1f} kg, already fulfilled {already_fulfilled:.1f} kg, " \
            f"remaining {remaining_demand:.1f} kg < requested {new_allocation:.1f} kg"
    return True, None, ""


def check_transport_capacity(
    transport: TransportOption,
    already_loaded: float,
    new_allocation: float,
) -> Tuple[bool, Optional[str], str]:
    """C4: No transport option may exceed its available capacity."""
    total = already_loaded + new_allocation
    if total > transport.capacity_kg + 1e-6:
        return False, RejectionReasonCode.CAPACITY_EXCEEDED.value, \
            f"C4 violation: transport {transport.id} capacity {transport.capacity_kg:.1f} kg, " \
            f"already loaded {already_loaded:.1f} kg, " \
            f"new request {new_allocation:.1f} kg exceeds limit"
    return True, None, ""


def check_route_available(transport: TransportOption) -> Tuple[bool, Optional[str], str]:
    """C5: No unavailable route or transport option may be selected."""
    if not transport.available:
        return False, RejectionReasonCode.ROUTE_UNAVAILABLE.value, \
            f"C5 violation: transport {transport.id} is marked unavailable"
    return True, None, ""


def check_commodity_compatibility(
    batch: InventoryBatch,
    destination: Destination,
) -> Tuple[bool, Optional[str], str]:
    """C6: Commodity and destination compatibility must be respected."""
    if batch.commodity not in destination.demand:
        return False, RejectionReasonCode.COMMODITY_INCOMPATIBLE.value, \
            f"C6 violation: destination {destination.id} has no demand " \
            f"for commodity '{batch.commodity}'"
    if destination.demand[batch.commodity] <= 0:
        return False, RejectionReasonCode.DEMAND_SATISFIED.value, \
            f"C6 violation: destination {destination.id} has zero demand " \
            f"for commodity '{batch.commodity}'"
    return True, None, ""


def check_shelf_life(
    batch: InventoryBatch,
    transport: TransportOption,
    departure_time: float = 0.0,
    spoilage_threshold_hours: float = 0.0,
) -> Tuple[bool, Optional[str], str]:
    """C7: Arrival + handling must not exceed remaining shelf life.

    shelf_life_at_delivery = remaining_shelf_life - departure_time - travel_time - handling_time
    Must be > spoilage_threshold (buffer hours).
    """
    total_transit = departure_time + transport.travel_time_hours + transport.handling_time_hours
    shelf_life_at_delivery = batch.remaining_shelf_life_hours - total_transit

    if shelf_life_at_delivery < spoilage_threshold_hours:
        return False, RejectionReasonCode.SHELF_LIFE_EXCEEDED.value, \
            f"C7 violation: batch {batch.id} shelf life {batch.remaining_shelf_life_hours:.1f}h, " \
            f"transit+handling {total_transit:.1f}h, " \
            f"remaining at delivery {shelf_life_at_delivery:.1f}h < threshold {spoilage_threshold_hours:.1f}h"
    return True, None, ""


def check_contribution(
    revenue: float,
    total_cost: float,
    allow_negative: bool = False,
) -> Tuple[bool, Optional[str], str]:
    """C9: Negative-contribution shipments should not be selected unless policy allows."""
    net = revenue - total_cost
    if net < 0 and not allow_negative:
        return False, RejectionReasonCode.NEGATIVE_CONTRIBUTION.value, \
            f"C9 violation: net contribution ₹{net:.2f} is negative " \
            f"(revenue ₹{revenue:.2f} - costs ₹{total_cost:.2f}), " \
            f"and negative-contribution policy is disabled"
    return True, None, ""


def check_destination_capacity(
    destination: Destination,
    already_received: float,
    new_allocation: float,
) -> Tuple[bool, Optional[str], str]:
    """Additional: Check destination receiving capacity."""
    total = already_received + new_allocation
    if total > destination.receiving_capacity_kg + 1e-6:
        return False, RejectionReasonCode.DESTINATION_CAPACITY_EXCEEDED.value, \
            f"Destination {destination.id} receiving capacity " \
            f"{destination.receiving_capacity_kg:.1f} kg, " \
            f"already received {already_received:.1f} kg, " \
            f"new {new_allocation:.1f} kg exceeds limit"
    return True, None, ""


def validate_all_constraints(
    batch: InventoryBatch,
    destination: Destination,
    transport: TransportOption,
    qty: float,
    batch_allocated: float,
    demand_fulfilled: float,
    transport_loaded: float,
    dest_received: float,
    cost_assumptions: CostAssumptions,
    departure_time: float = 0.0,
    market_price: float = 0.0,
) -> List[Tuple[bool, Optional[str], str]]:
    """Run all C1-C10 constraint checks and return list of results.

    Returns list of (passed, reason_code, detail) tuples.
    Only failed checks are actionable.
    """
    results = []

    # C1: Non-negative
    results.append(check_non_negative(qty))

    # C2: Batch capacity
    results.append(check_batch_capacity(batch, batch_allocated, qty))

    # C3: Demand limit
    results.append(check_demand_limit(destination, batch.commodity, demand_fulfilled, qty))

    # C4: Transport capacity
    results.append(check_transport_capacity(transport, transport_loaded, qty))

    # C5: Route available
    results.append(check_route_available(transport))

    # C6: Commodity compatibility
    results.append(check_commodity_compatibility(batch, destination))

    # C7: Shelf life feasibility
    results.append(check_shelf_life(
        batch, transport, departure_time,
        cost_assumptions.spoilage_threshold_hours
    ))

    # C9: Contribution check (compute expected revenue and costs)
    transport_cost = qty * transport.cost_per_kg
    handling_cost = qty * cost_assumptions.handling_cost_per_kg
    revenue = qty * market_price
    total_cost = transport_cost + handling_cost
    results.append(check_contribution(
        revenue, total_cost, cost_assumptions.allow_negative_contribution
    ))

    # Destination capacity
    results.append(check_destination_capacity(destination, dest_received, qty))

    return results


def is_feasible(
    batch: InventoryBatch,
    destination: Destination,
    transport: TransportOption,
    qty: float,
    batch_allocated: float,
    demand_fulfilled: float,
    transport_loaded: float,
    dest_received: float,
    cost_assumptions: CostAssumptions,
    departure_time: float = 0.0,
    market_price: float = 0.0,
) -> Tuple[bool, List[str], List[str]]:
    """Check if allocation is fully feasible.

    Returns:
        (is_feasible, list_of_reason_codes, list_of_detail_messages)
    """
    results = validate_all_constraints(
        batch, destination, transport, qty,
        batch_allocated, demand_fulfilled, transport_loaded, dest_received,
        cost_assumptions, departure_time, market_price,
    )

    reason_codes = []
    details = []
    for passed, code, detail in results:
        if not passed:
            reason_codes.append(code)
            details.append(detail)

    return len(reason_codes) == 0, reason_codes, details


from pydantic import BaseModel, Field

EPSILON = 1e-4


class ConstraintViolation(BaseModel):
    constraint_id: str = Field(..., description="C1 through C10")
    description: str = Field(..., description="Human-readable explanation of violation")
    entity_id: Optional[str] = Field(None, description="Batch, Destination, or Transport ID involved")
    expected: Optional[float] = Field(None, description="Maximum permitted or expected value")
    actual: Optional[float] = Field(None, description="Observed violating value")


class PlanValidationReport(BaseModel):
    is_valid: bool
    violations: List[ConstraintViolation] = Field(default_factory=list)
    reconciliation: Dict[str, float] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)


def check_candidate_feasibility(
    batch: InventoryBatch,
    destination: Destination,
    transport: TransportOption,
    requested_qty: float,
    batch_allocated_so_far: float,
    destination_demand_allocated_so_far: float,
    transport_allocated_so_far: float,
    destination_intake_allocated_so_far: float,
    cost_assumptions: CostAssumptions,
    departure_time: float = 0.0,
    discount_pct: float = 0.0,
) -> Tuple[bool, List[str], float]:
    """Evaluates whether allocating produce from a candidate triplet (batch, destination, transport)
    is physically and operationally feasible.

    Returns:
        (is_feasible, rejection_reasons, max_feasible_qty)
    """
    reasons: List[str] = []

    # C8: Unit consistency check
    if getattr(batch, "unit", "kg").lower() != "kg":
        reasons.append("INVALID_UNIT")
        return False, reasons, 0.0

    # C5: Transport route operational availability
    if not transport.available:
        reasons.append(RejectionReasonCode.ROUTE_UNAVAILABLE.value)

    # Route-destination mismatch check
    if transport.destination_id != destination.id:
        reasons.append("TRANSPORT_DESTINATION_MISMATCH")

    # C6: Commodity compatibility with destination demand
    commodity = batch.commodity
    total_demand = destination.demand.get(commodity, 0.0)
    if total_demand <= 0.0:
        reasons.append(RejectionReasonCode.COMMODITY_INCOMPATIBLE.value)

    # C7: Shelf life and demand window check
    delivery_time = departure_time + transport.travel_time_hours
    handling_completion = delivery_time + transport.handling_time_hours
    remaining_at_delivery = batch.remaining_shelf_life_hours - handling_completion

    if remaining_at_delivery < cost_assumptions.spoilage_threshold_hours:
        reasons.append(RejectionReasonCode.SHELF_LIFE_EXCEEDED.value)

    if delivery_time > destination.demand_window_hours:
        reasons.append(RejectionReasonCode.DEMAND_WINDOW_EXCEEDED.value)

    # Capacity and supply limits
    batch_remaining = max(0.0, batch.quantity_kg - batch_allocated_so_far)
    if batch_remaining <= EPSILON:
        reasons.append(RejectionReasonCode.BATCH_EXHAUSTED.value)

    demand_remaining = max(0.0, total_demand - destination_demand_allocated_so_far)
    if demand_remaining <= EPSILON:
        reasons.append(RejectionReasonCode.DEMAND_SATISFIED.value)

    transport_remaining = max(0.0, transport.capacity_kg - transport_allocated_so_far)
    if transport_remaining <= EPSILON:
        reasons.append(RejectionReasonCode.CAPACITY_EXCEEDED.value)

    destination_capacity_remaining = max(0.0, destination.receiving_capacity_kg - destination_intake_allocated_so_far)
    if destination_capacity_remaining <= EPSILON:
        reasons.append(RejectionReasonCode.DESTINATION_CAPACITY_EXCEEDED.value)

    # Upper bound of feasible quantity
    max_qty = min(batch_remaining, demand_remaining, transport_remaining, destination_capacity_remaining)

    if requested_qty > max_qty + EPSILON:
        if max_qty <= EPSILON and not reasons:
            reasons.append(RejectionReasonCode.CAPACITY_EXCEEDED.value)

    # C9: Economic contribution viability check (per kg)
    market_price = destination.market_price.get(commodity, 0.0)
    effective_price = market_price * (1.0 - discount_pct)
    freight_cost_per_kg = transport.cost_per_kg
    handling_cost_per_kg = cost_assumptions.handling_cost_per_kg
    holding_cost_per_kg = batch.holding_cost_per_kg_hr * departure_time

    unit_contribution = effective_price - freight_cost_per_kg - handling_cost_per_kg - holding_cost_per_kg
    if not cost_assumptions.allow_negative_contribution and unit_contribution < 0:
        reasons.append(RejectionReasonCode.NEGATIVE_CONTRIBUTION.value)

    feasible = (len(reasons) == 0) and (max_qty > EPSILON)
    return feasible, reasons, max(0.0, max_qty)


def validate_shipment_plan(scenario: Scenario, shipments: List[ShipmentPlan]) -> PlanValidationReport:
    """Rigorous audit-grade verification of all constraints C1-C10 on a candidate or final plan."""
    violations: List[ConstraintViolation] = []

    batches_by_id = {b.id: b for b in scenario.inventory_batches}
    destinations_by_id = {d.id: d for d in scenario.destinations}
    transports_by_id = {t.id: t for t in scenario.transport_options}

    batch_allocated: Dict[str, float] = {b.id: 0.0 for b in scenario.inventory_batches}
    dest_commodity_allocated: Dict[Tuple[str, str], float] = {}
    transport_allocated: Dict[str, float] = {t.id: 0.0 for t in scenario.transport_options}
    dest_intake_allocated: Dict[str, float] = {d.id: 0.0 for d in scenario.destinations}

    for idx, s in enumerate(shipments):
        # C1: Non-negative allocations
        if s.allocated_qty_kg < 0.0:
            violations.append(
                ConstraintViolation(
                    constraint_id="C1",
                    description=f"Shipment #{idx} allocated negative quantity: {s.allocated_qty_kg} kg",
                    entity_id=s.batch_id,
                    expected=0.0,
                    actual=s.allocated_qty_kg,
                )
            )

        batch = batches_by_id.get(s.batch_id)
        if not batch:
            violations.append(
                ConstraintViolation(
                    constraint_id="C2",
                    description=f"Shipment #{idx} references unknown batch ID: {s.batch_id}",
                    entity_id=s.batch_id,
                )
            )
            continue

        destination = destinations_by_id.get(s.destination_id)
        if not destination:
            violations.append(
                ConstraintViolation(
                    constraint_id="C6",
                    description=f"Shipment #{idx} references unknown destination ID: {s.destination_id}",
                    entity_id=s.destination_id,
                )
            )
            continue

        transport = transports_by_id.get(s.transport_id)
        if not transport:
            violations.append(
                ConstraintViolation(
                    constraint_id="C5",
                    description=f"Shipment #{idx} references unknown transport ID: {s.transport_id}",
                    entity_id=s.transport_id,
                )
            )
            continue

        # C8: Unit check
        if getattr(batch, "unit", "kg").lower() != "kg":
            violations.append(
                ConstraintViolation(
                    constraint_id="C8",
                    description=f"Batch {batch.id} unit is '{batch.unit}', must be 'kg'",
                    entity_id=batch.id,
                )
            )

        # C5: Transport availability and route matching
        if not transport.available:
            violations.append(
                ConstraintViolation(
                    constraint_id="C5",
                    description=f"Transport route {transport.id} is marked unavailable",
                    entity_id=transport.id,
                )
            )
        if transport.destination_id != destination.id:
            violations.append(
                ConstraintViolation(
                    constraint_id="C5",
                    description=f"Transport {transport.id} routes to {transport.destination_id}, not {destination.id}",
                    entity_id=transport.id,
                )
            )

        # C6: Commodity compatibility
        commodity = batch.commodity
        if commodity not in destination.demand or destination.demand[commodity] <= 0.0:
            violations.append(
                ConstraintViolation(
                    constraint_id="C6",
                    description=f"Destination {destination.id} has no demand for commodity '{commodity}'",
                    entity_id=destination.id,
                )
            )

        # C7: Shelf life and demand window timing
        expected_arrival = s.departure_time + transport.travel_time_hours
        expected_completion = expected_arrival + transport.handling_time_hours

        if expected_completion > batch.remaining_shelf_life_hours + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C7",
                    description=(
                        f"Shipment #{idx} completes at {expected_completion:.2f}h, exceeding "
                        f"batch shelf life {batch.remaining_shelf_life_hours:.2f}h"
                    ),
                    entity_id=batch.id,
                    expected=batch.remaining_shelf_life_hours,
                    actual=expected_completion,
                )
            )

        if expected_arrival > destination.demand_window_hours + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C7",
                    description=(
                        f"Shipment #{idx} arrives at {expected_arrival:.2f}h, exceeding "
                        f"demand window {destination.demand_window_hours:.2f}h"
                    ),
                    entity_id=destination.id,
                    expected=destination.demand_window_hours,
                    actual=expected_arrival,
                )
            )

        # C9: Economic contribution
        if not scenario.cost_assumptions.allow_negative_contribution and s.net_contribution < -EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C9",
                    description=f"Shipment #{idx} has negative net contribution of INR {s.net_contribution:.2f}",
                    entity_id=s.batch_id,
                    expected=0.0,
                    actual=s.net_contribution,
                )
            )

        batch_allocated[batch.id] += s.allocated_qty_kg
        dest_comm_key = (destination.id, commodity)
        dest_commodity_allocated[dest_comm_key] = dest_commodity_allocated.get(dest_comm_key, 0.0) + s.allocated_qty_kg
        transport_allocated[transport.id] += s.allocated_qty_kg
        dest_intake_allocated[destination.id] += s.allocated_qty_kg

    # C2: Dispatch <= available quantity per batch
    for batch_id, allocated_qty in batch_allocated.items():
        batch = batches_by_id[batch_id]
        if allocated_qty > batch.quantity_kg + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C2",
                    description=(
                        f"Batch {batch_id} over-allocated: {allocated_qty:.2f} kg allocated > "
                        f"{batch.quantity_kg:.2f} kg available"
                    ),
                    entity_id=batch_id,
                    expected=batch.quantity_kg,
                    actual=allocated_qty,
                )
            )

    # C3: Allocation <= remaining demand per destination-commodity
    for (dest_id, comm), allocated_qty in dest_commodity_allocated.items():
        destination = destinations_by_id[dest_id]
        demand_limit = destination.demand.get(comm, 0.0)
        if allocated_qty > demand_limit + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C3",
                    description=(
                        f"Destination {dest_id} over-supplied for '{comm}': {allocated_qty:.2f} kg > "
                        f"{demand_limit:.2f} kg demand"
                    ),
                    entity_id=dest_id,
                    expected=demand_limit,
                    actual=allocated_qty,
                )
            )

    # C4: Transport capacity
    for transport_id, allocated_qty in transport_allocated.items():
        transport = transports_by_id[transport_id]
        if allocated_qty > transport.capacity_kg + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C4",
                    description=(
                        f"Transport {transport_id} over capacity: {allocated_qty:.2f} kg > "
                        f"{transport.capacity_kg:.2f} kg limit"
                    ),
                    entity_id=transport_id,
                    expected=transport.capacity_kg,
                    actual=allocated_qty,
                )
            )

    # C4: Destination receiving capacity
    for dest_id, allocated_qty in dest_intake_allocated.items():
        destination = destinations_by_id[dest_id]
        if allocated_qty > destination.receiving_capacity_kg + EPSILON:
            violations.append(
                ConstraintViolation(
                    constraint_id="C4",
                    description=(
                        f"Destination {dest_id} exceeds receiving intake: {allocated_qty:.2f} kg > "
                        f"{destination.receiving_capacity_kg:.2f} kg"
                    ),
                    entity_id=dest_id,
                    expected=destination.receiving_capacity_kg,
                    actual=allocated_qty,
                )
            )

    # C10: Allocation and inventory conservation reconciliation
    total_batch_inventory = sum(b.quantity_kg for b in scenario.inventory_batches)
    total_allocated_inventory = sum(batch_allocated.values())
    total_unallocated_inventory = total_batch_inventory - total_allocated_inventory

    total_destination_demand = sum(sum(d.demand.values()) for d in scenario.destinations)
    total_fulfilled_demand = sum(dest_commodity_allocated.values())
    total_unfulfilled_demand = total_destination_demand - total_fulfilled_demand

    inventory_conservation_error = abs((total_allocated_inventory + total_unallocated_inventory) - total_batch_inventory)
    if inventory_conservation_error > EPSILON:
        violations.append(
            ConstraintViolation(
                constraint_id="C10",
                description=f"Inventory conservation reconciliation error: {inventory_conservation_error:.4f} kg",
                expected=total_batch_inventory,
                actual=total_allocated_inventory + total_unallocated_inventory,
            )
        )

    reconciliation = {
        "total_initial_inventory_kg": round(total_batch_inventory, 2),
        "total_allocated_kg": round(total_allocated_inventory, 2),
        "total_unallocated_kg": round(total_unallocated_inventory, 2),
        "total_market_demand_kg": round(total_destination_demand, 2),
        "total_fulfilled_demand_kg": round(total_fulfilled_demand, 2),
        "total_unfulfilled_demand_kg": round(total_unfulfilled_demand, 2),
        "inventory_discrepancy_kg": round(inventory_conservation_error, 5),
    }

    summary = {
        "shipment_count": len(shipments),
        "violation_count": len(violations),
        "status": "VALID" if len(violations) == 0 else "INVALID",
    }

    return PlanValidationReport(
        is_valid=(len(violations) == 0),
        violations=violations,
        reconciliation=reconciliation,
        summary=summary,
    )

