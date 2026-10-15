"""Deterministic synthetic dataset generator for FreshRoute AI.

Generates realistic Indian agricultural distribution data using fixed seeds
for reproducibility. All data is synthetic and clearly labeled as such.

Units: kg for quantities, hours for time, INR (₹) for currency.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    Scenario, CostAssumptions, DiscountConfig,
)


# ──────────────────────────────────────────────────
# Commodity Definitions (Indian produce context)
# ──────────────────────────────────────────────────

COMMODITIES = {
    "Tomatoes": {
        "base_price_range": (25.0, 45.0),     # INR/kg
        "shelf_life_range": (48, 96),           # hours
        "spoilage_cost": 12.0,                  # INR/kg
        "holding_cost": 0.10,                   # INR/kg-hr
    },
    "Bananas": {
        "base_price_range": (30.0, 55.0),
        "shelf_life_range": (72, 168),
        "spoilage_cost": 10.0,
        "holding_cost": 0.06,
    },
    "Mangoes": {
        "base_price_range": (60.0, 120.0),
        "shelf_life_range": (48, 120),
        "spoilage_cost": 25.0,
        "holding_cost": 0.12,
    },
    "Leafy Greens": {
        "base_price_range": (20.0, 40.0),
        "shelf_life_range": (12, 48),
        "spoilage_cost": 8.0,
        "holding_cost": 0.15,
    },
    "Onions": {
        "base_price_range": (18.0, 35.0),
        "shelf_life_range": (120, 360),
        "spoilage_cost": 5.0,
        "holding_cost": 0.03,
    },
}

# ──────────────────────────────────────────────────
# Destination Definitions (Major Indian markets)
# ──────────────────────────────────────────────────

DESTINATION_CONFIGS = [
    {
        "id": "DEST-DELHI",
        "name": "Delhi — Azadpur Mandi",
        "priority": 1,
        "capacity_kg": 50000.0,
        "demand_window_hours": 48.0,
        "demand_scale": 1.2,   # relative demand multiplier
        "price_premium": 1.15, # Delhi premium
    },
    {
        "id": "DEST-MUMBAI",
        "name": "Mumbai — Vashi APMC Market",
        "priority": 1,
        "capacity_kg": 45000.0,
        "demand_window_hours": 48.0,
        "demand_scale": 1.1,
        "price_premium": 1.20,
    },
    {
        "id": "DEST-PUNE",
        "name": "Pune — Market Yard",
        "priority": 2,
        "capacity_kg": 25000.0,
        "demand_window_hours": 36.0,
        "demand_scale": 0.7,
        "price_premium": 1.05,
    },
    {
        "id": "DEST-JAIPUR",
        "name": "Jaipur — Muhana Mandi",
        "priority": 2,
        "capacity_kg": 20000.0,
        "demand_window_hours": 36.0,
        "demand_scale": 0.6,
        "price_premium": 0.95,
    },
    {
        "id": "DEST-LUCKNOW",
        "name": "Lucknow — Alambagh Mandi",
        "priority": 3,
        "capacity_kg": 18000.0,
        "demand_window_hours": 42.0,
        "demand_scale": 0.5,
        "price_premium": 0.90,
    },
    {
        "id": "DEST-NAGPUR",
        "name": "Nagpur — Kalamna Market",
        "priority": 3,
        "capacity_kg": 15000.0,
        "demand_window_hours": 40.0,
        "demand_scale": 0.4,
        "price_premium": 0.88,
    },
]

# ──────────────────────────────────────────────────
# Transport Route Definitions (from Central Hub)
# ──────────────────────────────────────────────────

TRANSPORT_CONFIGS = [
    # Delhi routes
    {"dest": "DEST-DELHI",   "type": "Reefer Truck",   "time": 6.0,   "cost": 3.5, "capacity": 8000,  "handling": 2.0},
    {"dest": "DEST-DELHI",   "type": "Standard Truck",  "time": 7.0,   "cost": 2.5, "capacity": 10000, "handling": 2.5},
    {"dest": "DEST-DELHI",   "type": "Express Van",      "time": 4.5,   "cost": 5.0, "capacity": 3000,  "handling": 1.5},
    # Mumbai routes
    {"dest": "DEST-MUMBAI",  "type": "Reefer Truck",    "time": 14.0,  "cost": 5.0, "capacity": 8000,  "handling": 2.5},
    {"dest": "DEST-MUMBAI",  "type": "Standard Truck",   "time": 16.0,  "cost": 3.5, "capacity": 10000, "handling": 3.0},
    # Pune routes
    {"dest": "DEST-PUNE",    "type": "Reefer Truck",    "time": 16.0,  "cost": 5.5, "capacity": 6000,  "handling": 2.0},
    {"dest": "DEST-PUNE",    "type": "Standard Truck",   "time": 18.0,  "cost": 4.0, "capacity": 8000,  "handling": 2.5},
    # Jaipur routes
    {"dest": "DEST-JAIPUR",  "type": "Reefer Truck",    "time": 5.0,   "cost": 3.0, "capacity": 6000,  "handling": 2.0},
    {"dest": "DEST-JAIPUR",  "type": "Standard Truck",   "time": 6.5,   "cost": 2.0, "capacity": 8000,  "handling": 2.5},
    # Lucknow routes
    {"dest": "DEST-LUCKNOW", "type": "Reefer Truck",    "time": 8.0,   "cost": 4.0, "capacity": 5000,  "handling": 2.0},
    {"dest": "DEST-LUCKNOW", "type": "Standard Truck",   "time": 10.0,  "cost": 2.8, "capacity": 7000,  "handling": 2.5},
    # Nagpur routes
    {"dest": "DEST-NAGPUR",  "type": "Reefer Truck",    "time": 10.0,  "cost": 4.5, "capacity": 5000,  "handling": 2.0},
    {"dest": "DEST-NAGPUR",  "type": "Standard Truck",   "time": 12.0,  "cost": 3.2, "capacity": 7000,  "handling": 3.0},
    # Unavailable route (C5 test case)
    {"dest": "DEST-NAGPUR",  "type": "Express Van",      "time": 8.0,   "cost": 6.0, "capacity": 2000,  "handling": 1.5, "available": False},
]


def generate_inventory_batches(rng: random.Random) -> List[InventoryBatch]:
    """Generate 18 inventory batches with varying shelf lives and quantities."""
    batches: List[InventoryBatch] = []
    batch_idx = 0
    base_time = datetime.now(timezone.utc)

    for commodity, config in COMMODITIES.items():
        # Generate 3-4 batches per commodity
        n_batches = rng.randint(3, 4)
        for i in range(n_batches):
            batch_idx += 1
            abbrev = commodity[:3].upper()

            # Vary quantities
            qty = round(rng.uniform(500, 5000), 0)

            # Vary shelf lives - include some urgent ones
            min_sl, max_sl = config["shelf_life_range"]
            if i == 0 and commodity in ("Leafy Greens", "Tomatoes"):
                # Create urgent batches (very short shelf life)
                shelf_life = round(rng.uniform(min_sl * 0.5, min_sl * 0.8), 1)
            elif i == n_batches - 1:
                # Create comfortable batches
                shelf_life = round(rng.uniform(max_sl * 0.7, max_sl), 1)
            else:
                shelf_life = round(rng.uniform(min_sl, max_sl), 1)

            harvest_delta = timedelta(hours=rng.uniform(2, 24))
            harvest_time = (base_time - harvest_delta).isoformat()

            batches.append(InventoryBatch(
                id=f"BATCH-{abbrev}-{batch_idx:02d}",
                commodity=commodity,
                quantity_kg=qty,
                unit="kg",
                remaining_shelf_life_hours=shelf_life,
                harvest_timestamp=harvest_time,
                holding_cost_per_kg_hr=config["holding_cost"],
                spoilage_cost_per_kg=config["spoilage_cost"],
            ))

    return batches


def generate_destinations(rng: random.Random) -> List[Destination]:
    """Generate 6 destinations with varying demand and price profiles."""
    destinations: List[Destination] = []
    base_demands = {
        "Tomatoes": 3000.0,
        "Bananas": 2500.0,
        "Mangoes": 1500.0,
        "Leafy Greens": 2000.0,
        "Onions": 4000.0,
    }

    for dconf in DESTINATION_CONFIGS:
        demand = {}
        market_price = {}
        for commodity, config in COMMODITIES.items():
            base_d = base_demands[commodity] * dconf["demand_scale"]
            # Add some randomness
            demand[commodity] = round(base_d * rng.uniform(0.7, 1.3), 0)

            base_p = rng.uniform(*config["base_price_range"])
            market_price[commodity] = round(base_p * dconf["price_premium"], 2)

        destinations.append(Destination(
            id=dconf["id"],
            name=dconf["name"],
            demand=demand,
            market_price=market_price,
            receiving_capacity_kg=dconf["capacity_kg"],
            priority=dconf["priority"],
            demand_window_hours=dconf["demand_window_hours"],
        ))

    return destinations


def generate_transport_options(rng: random.Random) -> List[TransportOption]:
    """Generate transport options between central hub and destinations."""
    options: List[TransportOption] = []

    for idx, tconf in enumerate(TRANSPORT_CONFIGS, 1):
        # Add small random variation to make data more realistic
        time_var = rng.uniform(0.9, 1.1)
        cost_var = rng.uniform(0.95, 1.05)

        options.append(TransportOption(
            id=f"TR-{tconf['dest'].split('-')[1]}-{idx:02d}",
            origin="Central Hub — Nashik Region",
            destination_id=tconf["dest"],
            travel_time_hours=round(tconf["time"] * time_var, 1),
            cost_per_kg=round(tconf["cost"] * cost_var, 2),
            capacity_kg=float(tconf["capacity"]),
            handling_time_hours=tconf["handling"],
            available=tconf.get("available", True),
        ))

    return options


def generate_default_scenario(seed: int = 42) -> Scenario:
    """Generate the default demonstration scenario with seed=42.

    This is a SYNTHETIC dataset for demonstration purposes.
    It does not represent actual Indian market data.
    """
    rng = random.Random(seed)

    inventory = generate_inventory_batches(rng)
    destinations = generate_destinations(rng)
    transport = generate_transport_options(rng)

    return Scenario(
        id="SCENARIO-DEFAULT",
        name="Default Demonstration Scenario (Synthetic)",
        description=(
            "Synthetic dataset representing a central distribution hub in the Nashik region "
            "dispatching perishable produce to 6 major Indian markets. "
            "All data is synthetic and generated with seed=42 for reproducibility. "
            "This does not represent actual market prices, demand, or transport conditions."
        ),
        inventory_batches=inventory,
        destinations=destinations,
        transport_options=transport,
        cost_assumptions=CostAssumptions(
            handling_cost_per_kg=1.5,
            holding_cost_default_per_kg_hr=0.08,
            spoilage_penalty_multiplier=1.0,
            allow_negative_contribution=False,
            spoilage_threshold_hours=4.0,
        ),
        discount_config=DiscountConfig(
            enabled=True,
            steps=[0.0, 0.05, 0.10, 0.15, 0.20],
            elasticity_multiplier=1.5,
            shelf_life_threshold_hours=36.0,
        ),
        seed=seed,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def generate_csv_inventory(scenario: Scenario) -> str:
    """Export inventory batches to CSV format."""
    lines = ["batch_id,commodity,quantity_kg,remaining_shelf_life_hours,holding_cost_per_kg_hr,spoilage_cost_per_kg"]
    for b in scenario.inventory_batches:
        lines.append(f"{b.id},{b.commodity},{b.quantity_kg},{b.remaining_shelf_life_hours},{b.holding_cost_per_kg_hr},{b.spoilage_cost_per_kg}")
    return "\n".join(lines)


def generate_csv_destinations(scenario: Scenario) -> str:
    """Export destinations to CSV format."""
    commodities = list(COMMODITIES.keys())
    demand_cols = [f"demand_{c.lower().replace(' ', '_')}_kg" for c in commodities]
    price_cols = [f"price_{c.lower().replace(' ', '_')}_inr" for c in commodities]

    header = "destination_id,name,receiving_capacity_kg,priority,demand_window_hours"
    for dc in demand_cols:
        header += f",{dc}"
    for pc in price_cols:
        header += f",{pc}"

    lines = [header]
    for d in scenario.destinations:
        row = f"{d.id},{d.name},{d.receiving_capacity_kg},{d.priority},{d.demand_window_hours}"
        for c in commodities:
            row += f",{d.demand.get(c, 0.0)}"
        for c in commodities:
            row += f",{d.market_price.get(c, 0.0)}"
        lines.append(row)
    return "\n".join(lines)


def generate_csv_transport(scenario: Scenario) -> str:
    """Export transport options to CSV format."""
    lines = ["transport_id,origin,destination_id,travel_time_hours,cost_per_kg_inr,capacity_kg,handling_time_hours,available"]
    for t in scenario.transport_options:
        lines.append(f"{t.id},{t.origin},{t.destination_id},{t.travel_time_hours},{t.cost_per_kg},{t.capacity_kg},{t.handling_time_hours},{t.available}")
    return "\n".join(lines)


def generate_seed_inventory(seed: int = 42) -> List[InventoryBatch]:
    """Generates seed inventory batches."""
    return generate_default_scenario(seed=seed).inventory_batches

