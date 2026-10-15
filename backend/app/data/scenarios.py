"""Scenario management and held-out evaluation scenarios for FreshRoute AI.

Contains 10 distinct evaluation scenarios with fixed seeds.
Scenarios are generated deterministically for reproducibility.
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional

from app.models.domain import (
    Scenario, InventoryBatch, Destination, TransportOption,
    CostAssumptions, DiscountConfig,
)
from app.data.seed import generate_default_scenario, COMMODITIES


# In-memory scenario store
_scenario_store: Dict[str, Scenario] = {}


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    """Retrieve a scenario by ID."""
    return _scenario_store.get(scenario_id)


def list_scenarios() -> List[Scenario]:
    """List all saved scenarios."""
    return list(_scenario_store.values())


def save_scenario(scenario: Scenario) -> Scenario:
    """Save or update a scenario."""
    _scenario_store[scenario.id] = scenario
    return scenario


def delete_scenario(scenario_id: str) -> bool:
    """Delete a scenario."""
    return _scenario_store.pop(scenario_id, None) is not None


def reset_scenarios() -> None:
    """Clear all scenarios and reinitialize with defaults."""
    _scenario_store.clear()
    init_default_scenarios()


def init_default_scenarios() -> None:
    """Initialize the default scenario and held-out evaluation scenarios."""
    # Default demonstration scenario
    default = generate_default_scenario(seed=42)
    save_scenario(default)

    # Generate held-out evaluation scenarios
    for scenario in generate_held_out_scenarios():
        save_scenario(scenario)


def apply_modifications(
    scenario: Scenario,
    modifications: Dict[str, Any],
) -> Scenario:
    """Apply simulation modifications to a scenario and return a new scenario.

    Supported modifications:
    - demand_multiplier: Scale all demands
    - travel_time_multiplier: Scale all travel times
    - capacity_multiplier: Scale all transport capacities
    - shelf_life_multiplier: Scale all shelf lives
    - disable_routes: List of transport IDs to disable
    - new_batches: List of new inventory batch dicts to add
    - transport_cost_multiplier: Scale all transport costs
    - destination_demand_overrides: Dict of dest_id -> commodity -> new demand
    """
    # Deep copy to avoid mutating original
    modified = Scenario(
        id=f"{scenario.id}-SIM",
        name=f"{scenario.name} (Simulation)",
        description=f"Simulated version of {scenario.name}",
        inventory_batches=[b.model_copy() for b in scenario.inventory_batches],
        destinations=[d.model_copy(deep=True) for d in scenario.destinations],
        transport_options=[t.model_copy() for t in scenario.transport_options],
        cost_assumptions=scenario.cost_assumptions.model_copy(),
        discount_config=scenario.discount_config.model_copy(),
        seed=scenario.seed,
    )

    # Apply demand multiplier
    if "demand_multiplier" in modifications:
        mult = float(modifications["demand_multiplier"])
        for dest in modified.destinations:
            dest.demand = {c: round(v * mult, 0) for c, v in dest.demand.items()}

    # Apply travel time multiplier
    if "travel_time_multiplier" in modifications:
        mult = float(modifications["travel_time_multiplier"])
        for t in modified.transport_options:
            t.travel_time_hours = round(t.travel_time_hours * mult, 1)

    # Apply capacity multiplier
    if "capacity_multiplier" in modifications:
        mult = float(modifications["capacity_multiplier"])
        for t in modified.transport_options:
            t.capacity_kg = round(t.capacity_kg * mult, 0)

    # Apply shelf life multiplier
    if "shelf_life_multiplier" in modifications:
        mult = float(modifications["shelf_life_multiplier"])
        for b in modified.inventory_batches:
            b.remaining_shelf_life_hours = round(b.remaining_shelf_life_hours * mult, 1)

    # Disable specific routes
    if "disable_routes" in modifications:
        disable_ids = set(modifications["disable_routes"])
        for t in modified.transport_options:
            if t.id in disable_ids:
                t.available = False

    # Add new batches
    if "new_batches" in modifications:
        for batch_dict in modifications["new_batches"]:
            modified.inventory_batches.append(InventoryBatch(**batch_dict))

    # Apply transport cost multiplier
    if "transport_cost_multiplier" in modifications:
        mult = float(modifications["transport_cost_multiplier"])
        for t in modified.transport_options:
            t.cost_per_kg = round(t.cost_per_kg * mult, 2)

    # Override specific destination demands
    if "destination_demand_overrides" in modifications:
        overrides = modifications["destination_demand_overrides"]
        for dest in modified.destinations:
            if dest.id in overrides:
                for commodity, new_demand in overrides[dest.id].items():
                    dest.demand[commodity] = float(new_demand)

    return modified


def generate_held_out_scenarios() -> List[Scenario]:
    """Generate 10 distinct held-out evaluation scenarios.

    These test different conditions and edge cases.
    Fixed seeds ensure reproducibility.
    The optimizer is NOT tuned against these scenarios.
    """
    scenarios: List[Scenario] = []

    # Scenario 1: Normal distribution (baseline reference)
    s1 = generate_default_scenario(seed=101)
    s1.id = "EVAL-01-NORMAL"
    s1.name = "Evaluation: Normal Distribution"
    s1.description = "Standard distribution conditions. Baseline reference scenario."
    scenarios.append(s1)

    # Scenario 2: Extremely short shelf life
    s2 = generate_default_scenario(seed=102)
    s2.id = "EVAL-02-SHORT-SHELF"
    s2.name = "Evaluation: Extremely Short Shelf Life"
    s2.description = "All batches have shelf life under 24 hours. Tests urgency handling."
    for batch in s2.inventory_batches:
        batch.remaining_shelf_life_hours = min(batch.remaining_shelf_life_hours, 20.0)
        batch.remaining_shelf_life_hours = max(batch.remaining_shelf_life_hours * 0.3, 6.0)
    scenarios.append(s2)

    # Scenario 3: Demand spikes (3x normal)
    s3 = generate_default_scenario(seed=103)
    s3.id = "EVAL-03-DEMAND-SPIKE"
    s3.name = "Evaluation: Demand Spikes (3x)"
    s3.description = "All destination demand tripled. Tests capacity under stress."
    for dest in s3.destinations:
        dest.demand = {c: round(v * 3.0, 0) for c, v in dest.demand.items()}
    scenarios.append(s3)

    # Scenario 4: Route delays (+50% travel time)
    s4 = generate_default_scenario(seed=104)
    s4.id = "EVAL-04-ROUTE-DELAYS"
    s4.name = "Evaluation: Route Delays (+50%)"
    s4.description = "All travel times increased by 50%. Tests feasibility changes."
    for t in s4.transport_options:
        t.travel_time_hours = round(t.travel_time_hours * 1.5, 1)
    scenarios.append(s4)

    # Scenario 5: Capacity reductions (50%)
    s5 = generate_default_scenario(seed=105)
    s5.id = "EVAL-05-CAPACITY-REDUCED"
    s5.name = "Evaluation: Capacity Reductions (50%)"
    s5.description = "All transport capacities halved. Tests constraint tightening."
    for t in s5.transport_options:
        t.capacity_kg = round(t.capacity_kg * 0.5, 0)
    scenarios.append(s5)

    # Scenario 6: Low-margin destinations
    s6 = generate_default_scenario(seed=106)
    s6.id = "EVAL-06-LOW-MARGIN"
    s6.name = "Evaluation: Low-Margin Destinations"
    s6.description = "Market prices reduced significantly. Tests economic optimization."
    for dest in s6.destinations:
        dest.market_price = {c: round(v * 0.5, 2) for c, v in dest.market_price.items()}
    # Increase transport costs too
    for t in s6.transport_options:
        t.cost_per_kg = round(t.cost_per_kg * 1.5, 2)
    scenarios.append(s6)

    # Scenario 7: Missing/malformed records (valid but challenging data)
    s7 = generate_default_scenario(seed=107)
    s7.id = "EVAL-07-EDGE-DATA"
    s7.name = "Evaluation: Edge Case Data"
    s7.description = "Includes zero-quantity batches, zero-demand destinations, and extreme values."
    # Add zero-quantity batch
    s7.inventory_batches.append(InventoryBatch(
        id="BATCH-EDGE-01",
        commodity="Tomatoes",
        quantity_kg=0.0,
        remaining_shelf_life_hours=48.0,
    ))
    # Add destination with zero demand for some commodities
    for dest in s7.destinations[:2]:
        first_commodity = list(dest.demand.keys())[0]
        dest.demand[first_commodity] = 0.0
    scenarios.append(s7)

    # Scenario 8: No feasible shipment
    s8 = generate_default_scenario(seed=108)
    s8.id = "EVAL-08-NO-FEASIBLE"
    s8.name = "Evaluation: No Feasible Shipment"
    s8.description = "All shelf lives are extremely short and all routes are very long. No feasible allocation exists."
    for batch in s8.inventory_batches:
        batch.remaining_shelf_life_hours = 2.0  # Very short
    for t in s8.transport_options:
        t.travel_time_hours = 20.0  # Very long
        t.handling_time_hours = 5.0  # Long handling
    scenarios.append(s8)

    # Scenario 9: Zero demand
    s9 = generate_default_scenario(seed=109)
    s9.id = "EVAL-09-ZERO-DEMAND"
    s9.name = "Evaluation: Zero Demand"
    s9.description = "All destinations have zero demand. Tests graceful degradation."
    for dest in s9.destinations:
        dest.demand = {c: 0.0 for c in dest.demand}
    scenarios.append(s9)

    # Scenario 10: Baseline-wins scenario
    # In this scenario, the EEF baseline's simple urgency-first approach
    # happens to align well with the optimal solution because all batches
    # have similar economics and the main differentiator is shelf life.
    s10 = generate_default_scenario(seed=110)
    s10.id = "EVAL-10-BASELINE-WINS"
    s10.name = "Evaluation: Baseline Competitive"
    s10.description = (
        "Scenario designed where baseline's earliest-expiry-first approach "
        "is competitive or better. All batches have similar prices and costs, "
        "so shelf-life ordering is near-optimal."
    )
    # Normalize prices to be very similar across destinations
    avg_price = 35.0
    for dest in s10.destinations:
        dest.market_price = {c: avg_price for c in dest.market_price}
    # Normalize transport costs
    for t in s10.transport_options:
        t.cost_per_kg = 3.0
    scenarios.append(s10)

    return scenarios


# Auto-initialize default scenarios on import
init_default_scenarios()

# Compatibility aliases
get_all_scenarios = list_scenarios
get_scenario_by_id = get_scenario
register_scenario = save_scenario

