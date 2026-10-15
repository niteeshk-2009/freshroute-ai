"""Tests for Constraints C1-C10 in FreshRoute AI."""

import pytest
from app.models.domain import (
    InventoryBatch,
    Destination,
    TransportOption,
    CostAssumptions,
    ShipmentPlan,
    Scenario,
    FeasibilityStatus,
)
from app.engine.constraints import (
    check_candidate_feasibility,
    validate_shipment_plan,
)


@pytest.fixture
def base_scenario():
    batches = [
        InventoryBatch(
            id="B1",
            commodity="Tomatoes",
            quantity_kg=1000.0,
            unit="kg",
            remaining_shelf_life_hours=24.0,
            holding_cost_per_kg_hr=0.1,
            spoilage_cost_per_kg=20.0,
        )
    ]
    destinations = [
        Destination(
            id="D1",
            name="Delhi Mandi",
            demand={"Tomatoes": 800.0},
            market_price={"Tomatoes": 40.0},
            receiving_capacity_kg=2000.0,
            priority=1,
            demand_window_hours=48.0,
        )
    ]
    transports = [
        TransportOption(
            id="T1",
            origin="Hub",
            destination_id="D1",
            travel_time_hours=8.0,
            cost_per_kg=4.0,
            capacity_kg=1500.0,
            handling_time_hours=2.0,
            available=True,
        )
    ]
    return Scenario(
        id="TEST-SCENARIO",
        name="Test Scenario",
        inventory_batches=batches,
        destinations=destinations,
        transport_options=transports,
        cost_assumptions=CostAssumptions(handling_cost_per_kg=1.5, allow_negative_contribution=False),
    )


def test_c1_non_negative_allocation(base_scenario):
    """C1: Rejects negative allocations at model and function level."""
    from pydantic import ValidationError
    from app.engine.constraints import check_non_negative

    # Function check
    passed, code, msg = check_non_negative(-50.0)
    assert not passed
    assert "negative" in msg.lower()

    # Pydantic model level enforcement
    with pytest.raises(ValidationError):
        ShipmentPlan(
            batch_id="B1",
            destination_id="D1",
            transport_id="T1",
            allocated_qty_kg=-50.0,
            departure_time=0.0,
            arrival_time=8.0,
            handling_completion_time=10.0,
            shelf_life_remaining_at_delivery_hours=14.0,
            expected_sale_qty_kg=-50.0,
            revenue=-2000.0,
            transport_cost=200.0,
            handling_cost=75.0,
            holding_cost=0.0,
            net_contribution=-2275.0,
            feasibility_status=FeasibilityStatus.FEASIBLE,
        )


def test_c2_batch_quantity_limit(base_scenario):
    """C2: Total allocated from a batch cannot exceed batch available quantity."""
    shipments = [
        ShipmentPlan(
            batch_id="B1",
            destination_id="D1",
            transport_id="T1",
            allocated_qty_kg=1200.0,  # exceeds 1000 kg batch
            departure_time=0.0,
            arrival_time=8.0,
            handling_completion_time=10.0,
            shelf_life_remaining_at_delivery_hours=14.0,
            expected_sale_qty_kg=1200.0,
            revenue=48000.0,
            transport_cost=4800.0,
            handling_cost=1800.0,
            holding_cost=0.0,
            net_contribution=41400.0,
            feasibility_status=FeasibilityStatus.FEASIBLE,
        )
    ]
    report = validate_shipment_plan(base_scenario, shipments)
    assert not report.is_valid
    assert any(v.constraint_id == "C2" for v in report.violations)


def test_c3_demand_limit(base_scenario):
    """C3: Total allocated cannot exceed destination commodity demand."""
    shipments = [
        ShipmentPlan(
            batch_id="B1",
            destination_id="D1",
            transport_id="T1",
            allocated_qty_kg=950.0,  # exceeds 800 kg demand
            departure_time=0.0,
            arrival_time=8.0,
            handling_completion_time=10.0,
            shelf_life_remaining_at_delivery_hours=14.0,
            expected_sale_qty_kg=950.0,
            revenue=38000.0,
            transport_cost=3800.0,
            handling_cost=1425.0,
            holding_cost=0.0,
            net_contribution=32775.0,
            feasibility_status=FeasibilityStatus.FEASIBLE,
        )
    ]
    report = validate_shipment_plan(base_scenario, shipments)
    assert not report.is_valid
    assert any(v.constraint_id == "C3" for v in report.violations)


def test_c4_transport_capacity_limit(base_scenario):
    """C4: Transport capacity cannot be exceeded."""
    base_scenario.destinations[0].demand["Tomatoes"] = 2000.0
    base_scenario.inventory_batches[0].quantity_kg = 2000.0
    base_scenario.transport_options[0].capacity_kg = 500.0  # capacity is only 500 kg

    shipments = [
        ShipmentPlan(
            batch_id="B1",
            destination_id="D1",
            transport_id="T1",
            allocated_qty_kg=600.0,  # exceeds 500 kg capacity
            departure_time=0.0,
            arrival_time=8.0,
            handling_completion_time=10.0,
            shelf_life_remaining_at_delivery_hours=14.0,
            expected_sale_qty_kg=600.0,
            revenue=24000.0,
            transport_cost=2400.0,
            handling_cost=900.0,
            holding_cost=0.0,
            net_contribution=20700.0,
            feasibility_status=FeasibilityStatus.FEASIBLE,
        )
    ]
    report = validate_shipment_plan(base_scenario, shipments)
    assert not report.is_valid
    assert any(v.constraint_id == "C4" for v in report.violations)


def test_c5_unavailable_route(base_scenario):
    """C5: Unavailable transport option is rejected."""
    base_scenario.transport_options[0].available = False
    is_feas, reasons, _ = check_candidate_feasibility(
        batch=base_scenario.inventory_batches[0],
        destination=base_scenario.destinations[0],
        transport=base_scenario.transport_options[0],
        requested_qty=500.0,
        batch_allocated_so_far=0.0,
        destination_demand_allocated_so_far=0.0,
        transport_allocated_so_far=0.0,
        destination_intake_allocated_so_far=0.0,
        cost_assumptions=base_scenario.cost_assumptions,
    )
    assert not is_feas
    assert "ROUTE_UNAVAILABLE" in reasons


def test_c6_commodity_incompatibility(base_scenario):
    """C6: Commodity not demanded at destination is rejected."""
    base_scenario.inventory_batches[0].commodity = "Mangoes"  # destination only demands Tomatoes
    is_feas, reasons, _ = check_candidate_feasibility(
        batch=base_scenario.inventory_batches[0],
        destination=base_scenario.destinations[0],
        transport=base_scenario.transport_options[0],
        requested_qty=500.0,
        batch_allocated_so_far=0.0,
        destination_demand_allocated_so_far=0.0,
        transport_allocated_so_far=0.0,
        destination_intake_allocated_so_far=0.0,
        cost_assumptions=base_scenario.cost_assumptions,
    )
    assert not is_feas
    assert "COMMODITY_INCOMPATIBLE" in reasons


def test_c7_shelf_life_timing(base_scenario):
    """C7: Arrival + handling must not exceed shelf life."""
    # Travel time 20h + handling 6h = 26h > 24h shelf life
    base_scenario.transport_options[0].travel_time_hours = 20.0
    base_scenario.transport_options[0].handling_time_hours = 6.0

    is_feas, reasons, _ = check_candidate_feasibility(
        batch=base_scenario.inventory_batches[0],
        destination=base_scenario.destinations[0],
        transport=base_scenario.transport_options[0],
        requested_qty=500.0,
        batch_allocated_so_far=0.0,
        destination_demand_allocated_so_far=0.0,
        transport_allocated_so_far=0.0,
        destination_intake_allocated_so_far=0.0,
        cost_assumptions=base_scenario.cost_assumptions,
    )
    assert not is_feas
    assert "SHELF_LIFE_EXCEEDED" in reasons


def test_c8_unit_consistency():
    """C8: Unit must be kg."""
    with pytest.raises(ValueError):
        InventoryBatch(
            id="B_BAD",
            commodity="Tomatoes",
            quantity_kg=100.0,
            unit="tons",  # Must raise ValueError
            remaining_shelf_life_hours=24.0,
        )


def test_c9_negative_contribution(base_scenario):
    """C9: Disallows negative-margin shipments unless explicitly allowed."""
    base_scenario.cost_assumptions.allow_negative_contribution = False
    # Market price ₹5, transport cost ₹8, handling ₹1.5 => negative margin!
    base_scenario.destinations[0].market_price["Tomatoes"] = 5.0
    base_scenario.transport_options[0].cost_per_kg = 8.0

    is_feas, reasons, _ = check_candidate_feasibility(
        batch=base_scenario.inventory_batches[0],
        destination=base_scenario.destinations[0],
        transport=base_scenario.transport_options[0],
        requested_qty=500.0,
        batch_allocated_so_far=0.0,
        destination_demand_allocated_so_far=0.0,
        transport_allocated_so_far=0.0,
        destination_intake_allocated_so_far=0.0,
        cost_assumptions=base_scenario.cost_assumptions,
    )
    assert not is_feas
    assert "NEGATIVE_CONTRIBUTION" in reasons


def test_c10_reconciliation(base_scenario):
    """C10: Dispatches and unallocated stock strictly reconcile with initial inventory."""
    shipments = [
        ShipmentPlan(
            batch_id="B1",
            destination_id="D1",
            transport_id="T1",
            allocated_qty_kg=600.0,
            departure_time=0.0,
            arrival_time=8.0,
            handling_completion_time=10.0,
            shelf_life_remaining_at_delivery_hours=14.0,
            expected_sale_qty_kg=600.0,
            revenue=24000.0,
            transport_cost=2400.0,
            handling_cost=900.0,
            holding_cost=0.0,
            net_contribution=20700.0,
            feasibility_status=FeasibilityStatus.FEASIBLE,
        )
    ]
    report = validate_shipment_plan(base_scenario, shipments)
    assert report.is_valid
    assert report.reconciliation["total_initial_inventory_kg"] == 1000.0
    assert report.reconciliation["total_allocated_kg"] == 600.0
    assert report.reconciliation["total_unallocated_kg"] == 400.0
    assert report.reconciliation["inventory_discrepancy_kg"] == 0.0
