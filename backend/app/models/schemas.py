"""API request/response schemas for FreshRoute AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.domain import (
    InventoryBatch, Destination, TransportOption,
    Scenario, ShipmentPlan, EvaluationResult,
    CostAssumptions, DiscountConfig,
)


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "FreshRoute AI"
    version: str = "1.0.0"
    scenarios_loaded: int = 0


class ScenarioListResponse(BaseModel):
    scenarios: List[Dict[str, Any]]
    count: int


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    batch_count: int
    destination_count: int
    transport_count: int
    total_inventory_kg: float
    total_demand_kg: float
    seed: int = 42
    created_at: str = ""


class ScenarioCreateRequest(BaseModel):
    name: str = Field(..., description="Scenario name")
    description: str = Field(default="", description="Scenario description")
    inventory_batches: Optional[List[InventoryBatch]] = None
    destinations: Optional[List[Destination]] = None
    transport_options: Optional[List[TransportOption]] = None
    cost_assumptions: Optional[CostAssumptions] = None
    discount_config: Optional[DiscountConfig] = None
    seed: int = Field(default=42)


# Alias
ScenarioCreate = ScenarioCreateRequest


class SimulationModifications(BaseModel):
    demand_multipliers: Optional[Dict[str, float]] = None
    price_multipliers: Optional[Dict[str, float]] = None
    destination_price_overrides: Optional[Dict[str, Dict[str, float]]] = None
    destination_demand_overrides: Optional[Dict[str, Dict[str, float]]] = None
    transport_delays_hours: Optional[Dict[str, float]] = None
    transport_availability: Optional[Dict[str, bool]] = None
    capacity_multipliers: Optional[Dict[str, float]] = None
    allow_negative_contribution: Optional[bool] = None
    spoilage_threshold_hours: Optional[float] = None


class SimulationRequest(BaseModel):
    strategy: str = Field(default="heuristic_optimized")
    modifications: Optional[SimulationModifications] = None


class OptimizationResponse(BaseModel):
    scenario_id: str
    strategy: str
    result: Dict[str, Any]
    discount_recommendations: List[Dict[str, Any]] = []
    shipments: List[Dict[str, Any]] = []
    rejected_candidates: List[Dict[str, Any]] = []


class ComparisonResponse(BaseModel):
    scenario_id: str
    baseline: Dict[str, Any]
    optimized: Dict[str, Any]
    comparison: Dict[str, Any]
    summary: Dict[str, Any]
    discount_recommendations: List[Dict[str, Any]] = []


class SimulationResponse(BaseModel):
    scenario_id: str
    original_comparison: Dict[str, Any]
    modified_comparison: Dict[str, Any]
    modifications_applied: Dict[str, Any]
    affected_shipments: List[Dict[str, Any]] = []
    changes_explanation: str = ""


class ReportResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    report: Dict[str, Any]
    generated_at: str


class CSVValidationResult(BaseModel):
    is_valid: bool
    total_rows: int
    valid_count: int
    invalid_count: int
    errors: List[str] = Field(default_factory=list)
    imported_batches: List[InventoryBatch] = Field(default_factory=list)


class InventoryImportResponse(BaseModel):
    status: str
    message: str = ""
    imported_count: int = 0
    errors: List[str] = []
    warnings: List[str] = []
    validation: Optional[CSVValidationResult] = None


class ScenarioReportResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    created_at: str
    baseline_evaluation: Dict[str, Any]
    optimized_evaluation: Dict[str, Any]
    comparison: Dict[str, Any]
    discount_recommendations: List[Dict[str, Any]]
    validation_report: Dict[str, Any]
    executive_summary: Dict[str, Any]


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    status_code: int = 400

