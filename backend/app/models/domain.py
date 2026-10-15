"""Domain models for FreshRoute AI perishable produce distribution platform.

All physical quantities in kilograms (kg), times in hours, and currency in Indian Rupees (INR - ₹).
Strict validation is applied to enforce domain consistency and physical feasibility.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class RejectionReasonCode(str, Enum):
    SHELF_LIFE_EXCEEDED = "SHELF_LIFE_EXCEEDED"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    DEMAND_SATISFIED = "DEMAND_SATISFIED"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    NEGATIVE_CONTRIBUTION = "NEGATIVE_CONTRIBUTION"
    NO_COMPATIBLE_DESTINATION = "NO_COMPATIBLE_DESTINATION"
    BATCH_EXHAUSTED = "BATCH_EXHAUSTED"
    DESTINATION_CAPACITY_EXCEEDED = "DESTINATION_CAPACITY_EXCEEDED"
    DEMAND_WINDOW_EXCEEDED = "DEMAND_WINDOW_EXCEEDED"
    COMMODITY_INCOMPATIBLE = "COMMODITY_INCOMPATIBLE"


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"


class InventoryBatch(BaseModel):
    id: str = Field(..., description="Unique batch identifier, e.g. BATCH-TOM-01")
    commodity: str = Field(..., description="Commodity name, e.g. Tomatoes, Bananas, Mangoes")
    quantity_kg: float = Field(..., ge=0.0, description="Available batch weight in kg")
    unit: str = Field(default="kg", description="Physical unit, strictly 'kg'")
    remaining_shelf_life_hours: float = Field(..., ge=0.0, description="Remaining shelf life in hours")
    harvest_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 harvest or intake timestamp"
    )
    holding_cost_per_kg_hr: float = Field(
        default=0.08, ge=0.0, description="Holding/cold storage cost in INR per kg-hour"
    )
    spoilage_cost_per_kg: float = Field(
        default=15.0, ge=0.0, description="Disposal or economic loss penalty in INR per kg if spoiled"
    )

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v.lower() != "kg":
            raise ValueError(f"Constraint C8 violation: unit must be 'kg', got '{v}'")
        return "kg"

    @field_validator("commodity")
    @classmethod
    def clean_commodity(cls, v: str) -> str:
        v_clean = v.strip().title()
        if not v_clean:
            raise ValueError("Commodity name cannot be empty")
        return v_clean


class Destination(BaseModel):
    id: str = Field(..., description="Unique destination identifier, e.g. DEST-DELHI")
    name: str = Field(..., description="Destination market or hub name, e.g. Delhi Azadpur Mandi")
    demand: Dict[str, float] = Field(
        default_factory=dict,
        description="Unfulfilled demand per commodity in kg, e.g. {'Tomatoes': 4000.0}"
    )
    market_price: Dict[str, float] = Field(
        default_factory=dict,
        description="Current market price per commodity in INR/kg, e.g. {'Tomatoes': 38.0}"
    )
    receiving_capacity_kg: float = Field(
        default=50000.0, ge=0.0, description="Maximum intake capacity at hub in kg"
    )
    priority: int = Field(
        default=1, ge=1, le=10, description="Destination priority (1 is highest priority)"
    )
    demand_window_hours: float = Field(
        default=48.0, ge=0.0, description="Maximum delivery window deadline in hours"
    )

    @field_validator("demand", "market_price")
    @classmethod
    def check_non_negative_values(cls, v: Dict[str, float]) -> Dict[str, float]:
        for k, val in v.items():
            if val < 0.0:
                raise ValueError(f"Value for commodity '{k}' must be non-negative, got {val}")
        return v


class TransportOption(BaseModel):
    id: str = Field(..., description="Unique transport identifier, e.g. TR-DEL-REEFER-01")
    origin: str = Field(default="Central Hub", description="Origin hub name")
    destination_id: str = Field(..., description="Target destination ID")
    travel_time_hours: float = Field(..., ge=0.0, description="Transit duration in hours")
    cost_per_kg: float = Field(..., ge=0.0, description="Freight cost in INR per kg")
    capacity_kg: float = Field(..., ge=0.0, description="Vehicle cargo weight limit in kg")
    handling_time_hours: float = Field(
        default=2.0, ge=0.0, description="Loading and unloading turnaround in hours"
    )
    available: bool = Field(default=True, description="Whether route/vehicle is operational")


class CostAssumptions(BaseModel):
    handling_cost_per_kg: float = Field(
        default=1.5, ge=0.0, description="Standard handling fee in INR per kg"
    )
    holding_cost_default_per_kg_hr: float = Field(
        default=0.08, ge=0.0, description="Default holding cost in INR per kg-hr"
    )
    spoilage_penalty_multiplier: float = Field(
        default=1.0, ge=0.0, description="Multiplier applied to batch spoilage cost"
    )
    allow_negative_contribution: bool = Field(
        default=False, description="Constraint C9: whether negative-margin shipments are accepted"
    )
    spoilage_threshold_hours: float = Field(
        default=6.0, ge=0.0, description="Margin hours below which produce is deemed spoiled if not unloaded"
    )


class DiscountConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether discount recommendation is active")
    steps: List[float] = Field(
        default=[0.0, 0.05, 0.10, 0.15, 0.20],
        description="Discount percentage options to test"
    )
    elasticity_multiplier: float = Field(
        default=1.5, ge=0.0, description="Assumed demand elasticity factor: additional_demand_pct = discount_pct * 1.5"
    )
    shelf_life_threshold_hours: float = Field(
        default=36.0, ge=0.0, description="Shelf life threshold below which discounting is evaluated"
    )


class ShipmentPlan(BaseModel):
    batch_id: str = Field(..., description="Allocated inventory batch ID")
    destination_id: str = Field(..., description="Target destination ID")
    transport_id: str = Field(..., description="Assigned transport option ID")
    allocated_qty_kg: float = Field(..., ge=0.0, description="Dispatched weight in kg")
    departure_time: float = Field(default=0.0, ge=0.0, description="Departure time in hours from t=0")
    arrival_time: float = Field(..., ge=0.0, description="Arrival time = departure + travel_time")
    handling_completion_time: float = Field(
        ..., ge=0.0, description="Completion time = arrival_time + handling_time"
    )
    shelf_life_remaining_at_delivery_hours: float = Field(
        ..., description="Remaining shelf life at destination unloading in hours"
    )
    expected_sale_qty_kg: float = Field(..., ge=0.0, description="Estimated saleable weight in kg")
    discount_pct: float = Field(default=0.0, ge=0.0, le=1.0, description="Applied discount percentage")
    revenue: float = Field(default=0.0, description="Expected gross sales revenue in INR (₹)")
    transport_cost: float = Field(default=0.0, ge=0.0, description="Freight cost in INR (₹)")
    handling_cost: float = Field(default=0.0, ge=0.0, description="Handling cost in INR (₹)")
    holding_cost: float = Field(default=0.0, ge=0.0, description="Pre-transit holding cost in INR (₹)")
    net_contribution: float = Field(
        default=0.0, description="Net margin = revenue - transport_cost - handling_cost - holding_cost (₹)"
    )
    feasibility_status: FeasibilityStatus = Field(
        default=FeasibilityStatus.FEASIBLE, description="FEASIBLE or INFEASIBLE"
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict, description="Structured human-interpretable rationale"
    )
    rejection_reasons: List[str] = Field(
        default_factory=list, description="Reason codes if infeasible or suboptimal"
    )


class EvaluationResult(BaseModel):
    strategy_name: str = Field(..., description="Name of strategy evaluated")
    shipments: List[ShipmentPlan] = Field(default_factory=list, description="All planned shipment allocations")
    total_revenue: float = Field(default=0.0, description="Total gross sales revenue in INR")
    total_transport_cost: float = Field(default=0.0, ge=0.0, description="Total transport expenditure in INR")
    total_handling_cost: float = Field(default=0.0, ge=0.0, description="Total handling expenditure in INR")
    total_holding_cost: float = Field(default=0.0, ge=0.0, description="Total holding cost incurred in INR")
    total_spoilage_cost: float = Field(default=0.0, ge=0.0, description="Economic penalty of spoiled batches in INR")
    net_revenue: float = Field(
        default=0.0,
        description="Net profit = total_revenue - (transport + handling + holding + spoilage costs)"
    )
    spoiled_qty_kg: float = Field(default=0.0, ge=0.0, description="Produce quantity spoiled in kg")
    spoilage_rate_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Spoilage as percentage of total available inventory"
    )
    demand_fulfilled_qty_kg: float = Field(
        default=0.0, ge=0.0, description="Fulfilled customer demand weight in kg"
    )
    total_demand_kg: float = Field(default=0.0, ge=0.0, description="Total aggregate demand across markets in kg")
    fulfillment_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Percentage of total demand satisfied"
    )
    inventory_utilization_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Percentage of inventory dispatched"
    )
    unallocated_qty_kg: float = Field(
        default=0.0, ge=0.0, description="Unallocated inventory remaining in warehouse in kg"
    )
    feasible_shipment_count: int = Field(default=0, ge=0, description="Number of fully feasible shipments")
    shelf_life_violations: int = Field(default=0, ge=0, description="Number of shelf-life constraint violations")
    capacity_violations: int = Field(default=0, ge=0, description="Number of vehicle/receiving capacity violations")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Algorithm compute time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and reconciliation metadata")


class Scenario(BaseModel):
    id: str = Field(..., description="Unique scenario identifier, e.g. SCENARIO-NORMAL-01")
    name: str = Field(..., description="Descriptive scenario name")
    description: Optional[str] = Field(default="", description="Detailed scenario context and assumptions")
    inventory_batches: List[InventoryBatch] = Field(default_factory=list)
    destinations: List[Destination] = Field(default_factory=list)
    transport_options: List[TransportOption] = Field(default_factory=list)
    cost_assumptions: CostAssumptions = Field(default_factory=CostAssumptions)
    discount_config: DiscountConfig = Field(default_factory=DiscountConfig)
    seed: int = Field(default=42, description="Random seed for deterministic reproducibility")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Scenario creation timestamp"
    )
