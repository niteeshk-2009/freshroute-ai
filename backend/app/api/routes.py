"""FastAPI REST API routes for FreshRoute AI.

Exposes endpoints for scenario management, baseline & heuristic optimization,
what-if simulation, strategy evaluation, executive reporting, CSV inventory import,
and data templates.
"""

from __future__ import annotations

import copy
import csv
import io
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.models.domain import (
    Scenario,
    InventoryBatch,
    Destination,
    TransportOption,
    EvaluationResult,
    CostAssumptions,
    DiscountConfig,
)
from app.models.schemas import (
    ScenarioSummary,
    ScenarioCreate,
    SimulationRequest,
    SimulationModifications,
    ScenarioReportResponse,
    CSVValidationResult,
    InventoryImportResponse,
)
from app.data.scenarios import (
    get_all_scenarios,
    get_scenario_by_id,
    register_scenario,
)
from app.data.seed import generate_seed_inventory
from app.engine.baseline import run_baseline_eef
from app.engine.optimizer import run_heuristic_optimizer
from app.engine.evaluator import compare_strategies
from app.engine.discount import generate_discount_recommendations
from app.engine.constraints import validate_shipment_plan
from app.database import (
    save_scenario_to_db,
    load_scenario_from_db,
    list_saved_scenarios,
    save_custom_batches,
    load_custom_batches,
)

router = APIRouter()


@router.get("/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/scenarios", response_model=List[ScenarioSummary], tags=["Scenarios"])
def list_scenarios() -> List[ScenarioSummary]:
    """Lists all available benchmark and custom scenarios."""
    all_sc = get_all_scenarios()
    # Add any saved scenarios from DB that might not be in memory
    saved = list_saved_scenarios()
    existing_ids = {s.id for s in all_sc}
    for s in saved:
        if s.id not in existing_ids:
            all_sc.append(s)
            existing_ids.add(s.id)

    summaries: List[ScenarioSummary] = []
    for sc in all_sc:
        total_inv = sum(b.quantity_kg for b in sc.inventory_batches)
        total_dem = sum(sum(d.demand.values()) for d in sc.destinations)
        summaries.append(
            ScenarioSummary(
                id=sc.id,
                name=sc.name,
                description=sc.description or "",
                batch_count=len(sc.inventory_batches),
                destination_count=len(sc.destinations),
                transport_count=len(sc.transport_options),
                total_inventory_kg=round(total_inv, 2),
                total_demand_kg=round(total_dem, 2),
                seed=sc.seed,
                created_at=sc.created_at,
            )
        )
    return summaries


@router.post("/scenarios", response_model=Scenario, status_code=status.HTTP_201_CREATED, tags=["Scenarios"])
def create_scenario(payload: ScenarioCreate) -> Scenario:
    """Creates and persists a new custom distribution scenario."""
    sc_id = payload.id or f"SCENARIO-CUSTOM-{int(time.time())}"
    scenario = Scenario(
        id=sc_id,
        name=payload.name,
        description=payload.description or "",
        inventory_batches=payload.inventory_batches,
        destinations=payload.destinations,
        transport_options=payload.transport_options,
        cost_assumptions=payload.cost_assumptions or CostAssumptions(),
        discount_config=payload.discount_config or DiscountConfig(),
        seed=payload.seed or settings.DEFAULT_SEED,
    )
    register_scenario(scenario)
    save_scenario_to_db(scenario)
    return scenario


@router.get("/scenarios/{scenario_id}", response_model=Scenario, tags=["Scenarios"])
def get_scenario(scenario_id: str) -> Scenario:
    """Retrieves full details of a specific scenario."""
    sc = get_scenario_by_id(scenario_id)
    if not sc:
        sc = load_scenario_from_db(scenario_id)
    if not sc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario with ID '{scenario_id}' not found.",
        )
    return sc


@router.post("/scenarios/{scenario_id}/baseline", response_model=EvaluationResult, tags=["Engine"])
def run_baseline_endpoint(scenario_id: str) -> EvaluationResult:
    """Executes the Earliest-Expiry-First (EEF) baseline strategy."""
    scenario = get_scenario(scenario_id)
    return run_baseline_eef(scenario)


@router.post("/scenarios/{scenario_id}/optimize", response_model=EvaluationResult, tags=["Engine"])
def run_optimizer_endpoint(scenario_id: str) -> EvaluationResult:
    """Executes constraint-aware heuristic optimization."""
    scenario = get_scenario(scenario_id)
    return run_heuristic_optimizer(scenario)


def apply_modifications(scenario: Scenario, mods: SimulationModifications) -> Scenario:
    """Applies what-if scenario modifications to a deepcopy of the scenario."""
    sc = copy.deepcopy(scenario)

    # Price multipliers
    if mods.price_multipliers:
        for d in sc.destinations:
            for comm, mult in mods.price_multipliers.items():
                if comm in d.market_price:
                    d.market_price[comm] = round(d.market_price[comm] * mult, 2)

    # Destination price overrides
    if mods.destination_price_overrides:
        for dest_id, comm_map in mods.destination_price_overrides.items():
            for d in sc.destinations:
                if d.id == dest_id:
                    for comm, p in comm_map.items():
                        d.market_price[comm] = round(p, 2)

    # Demand multipliers
    if mods.demand_multipliers:
        for d in sc.destinations:
            for comm, mult in mods.demand_multipliers.items():
                if comm in d.demand:
                    d.demand[comm] = round(d.demand[comm] * mult, 2)

    # Destination demand overrides
    if mods.destination_demand_overrides:
        for dest_id, comm_map in mods.destination_demand_overrides.items():
            for d in sc.destinations:
                if d.id == dest_id:
                    for comm, dem in comm_map.items():
                        d.demand[comm] = round(dem, 2)

    # Transport delays
    if mods.transport_delays_hours:
        for t in sc.transport_options:
            if t.id in mods.transport_delays_hours:
                t.travel_time_hours = round(t.travel_time_hours + mods.transport_delays_hours[t.id], 1)

    # Transport availability
    if mods.transport_availability:
        for t in sc.transport_options:
            if t.id in mods.transport_availability:
                t.available = mods.transport_availability[t.id]

    # Capacity multipliers
    if mods.capacity_multipliers:
        for t in sc.transport_options:
            if t.id in mods.capacity_multipliers:
                t.capacity_kg = round(t.capacity_kg * mods.capacity_multipliers[t.id], 1)

    # Policy overrides
    if mods.allow_negative_contribution is not None:
        sc.cost_assumptions.allow_negative_contribution = mods.allow_negative_contribution

    if mods.spoilage_threshold_hours is not None:
        sc.cost_assumptions.spoilage_threshold_hours = mods.spoilage_threshold_hours

    return sc


@router.post("/scenarios/{scenario_id}/simulate", response_model=EvaluationResult, tags=["Engine"])
def run_simulation(scenario_id: str, request: SimulationRequest) -> EvaluationResult:
    """Simulates operational what-if scenarios with custom overrides."""
    base_scenario = get_scenario(scenario_id)

    scenario = base_scenario
    if request.modifications:
        scenario = apply_modifications(base_scenario, request.modifications)

    if request.strategy.lower() in ["baseline", "baseline_eef", "eef"]:
        return run_baseline_eef(scenario)
    else:
        return run_heuristic_optimizer(scenario)


@router.get("/scenarios/{scenario_id}/evaluation", tags=["Analysis"])
def evaluate_scenario_strategies(scenario_id: str) -> Dict[str, Any]:
    """Executes both Baseline and Optimizer and produces side-by-side comparison."""
    scenario = get_scenario(scenario_id)
    base_result = run_baseline_eef(scenario)
    opt_result = run_heuristic_optimizer(scenario)
    return compare_strategies(base_result, opt_result)


@router.get("/scenarios/{scenario_id}/report", tags=["Analysis"])
def generate_scenario_report(scenario_id: str) -> Dict[str, Any]:
    """Generates an executive decision audit report."""
    scenario = get_scenario(scenario_id)

    base_eval = run_baseline_eef(scenario)
    opt_eval = run_heuristic_optimizer(scenario)
    comparison = compare_strategies(base_eval, opt_eval)
    discount_res = generate_discount_recommendations(scenario, opt_eval.shipments)
    val_report = validate_shipment_plan(scenario, opt_eval.shipments)

    net_diff = opt_eval.net_revenue - base_eval.net_revenue
    spoilage_diff = base_eval.spoiled_qty_kg - opt_eval.spoiled_qty_kg

    exec_summary = {
        "status": "VALID" if val_report.is_valid else "INVALID",
        "net_revenue_difference_inr": round(net_diff, 2),
        "spoilage_reduction_kg": round(spoilage_diff, 2),
        "discount_recommendations_count": len(discount_res),
        "key_takeaway": (
            f"Heuristic optimization yields ₹{abs(net_diff):.2f} {'more' if net_diff >= 0 else 'less'} net profit "
            f"and curtails spoilage by {abs(spoilage_diff):.1f} kg compared to Earliest-Expiry-First."
        ),
    }

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_evaluation": base_eval.model_dump(),
        "optimized_evaluation": opt_eval.model_dump(),
        "comparison": comparison,
        "discount_recommendations": discount_res,
        "validation_report": val_report.model_dump(),
        "executive_summary": exec_summary,
    }


@router.get("/scenarios/{scenario_id}/discounts", tags=["Engine"])
def get_scenario_discounts(scenario_id: str) -> List[Dict[str, Any]]:
    """Calculates dynamic discount recommendations for at-risk batches."""
    scenario = get_scenario(scenario_id)
    opt_eval = run_heuristic_optimizer(scenario)
    return generate_discount_recommendations(scenario, opt_eval.shipments)


@router.get("/inventory", response_model=List[InventoryBatch], tags=["Inventory"])
def get_inventory() -> List[InventoryBatch]:
    """Returns the current active warehouse inventory batches."""
    custom = load_custom_batches()
    if custom:
        return custom
    return generate_seed_inventory(seed=settings.DEFAULT_SEED)


@router.post("/inventory/import", response_model=InventoryImportResponse, tags=["Inventory"])
async def import_inventory_csv(file: UploadFile = File(...)) -> InventoryImportResponse:
    """Parses and validates a CSV upload of inventory batches.

    Required columns:
    id, commodity, quantity_kg, unit, remaining_shelf_life_hours, holding_cost_per_kg_hr, spoilage_cost_per_kg
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV with .csv extension.",
        )

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    required_cols = {"id", "commodity", "quantity_kg", "unit", "remaining_shelf_life_hours"}

    if not required_cols.issubset(set(reader.fieldnames or [])):
        missing = required_cols - set(reader.fieldnames or [])
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV missing mandatory headers: {list(missing)}",
        )

    valid_batches: List[InventoryBatch] = []
    errors: List[str] = []
    total_rows = 0

    for idx, row in enumerate(reader, start=2):  # 1-indexed header is row 1
        total_rows += 1
        try:
            batch_id = row.get("id", "").strip()
            commodity = row.get("commodity", "").strip()
            unit = row.get("unit", "").strip().lower()
            qty = float(row.get("quantity_kg", 0.0))
            shelf_life = float(row.get("remaining_shelf_life_hours", 0.0))
            holding_cost = float(row.get("holding_cost_per_kg_hr") or 0.08)
            spoilage_cost = float(row.get("spoilage_cost_per_kg") or 15.0)

            if not batch_id or not commodity:
                errors.append(f"Row {idx}: Batch ID or commodity name is empty.")
                continue

            if unit != "kg":
                errors.append(f"Row {idx}: Constraint C8 violation - unit must be 'kg', got '{unit}'.")
                continue

            if qty < 0.0:
                errors.append(f"Row {idx}: Constraint C1 violation - quantity must be non-negative, got {qty}.")
                continue

            if shelf_life < 0.0:
                errors.append(f"Row {idx}: Shelf life must be non-negative, got {shelf_life}.")
                continue

            batch = InventoryBatch(
                id=batch_id,
                commodity=commodity,
                quantity_kg=qty,
                unit="kg",
                remaining_shelf_life_hours=shelf_life,
                holding_cost_per_kg_hr=holding_cost,
                spoilage_cost_per_kg=spoilage_cost,
            )
            valid_batches.append(batch)
        except Exception as e:
            errors.append(f"Row {idx}: Failed parsing with error - {str(e)}")

    if valid_batches:
        save_custom_batches(valid_batches)

    val_result = CSVValidationResult(
        is_valid=(len(errors) == 0 and len(valid_batches) > 0),
        total_rows=total_rows,
        valid_count=len(valid_batches),
        invalid_count=len(errors),
        errors=errors,
        imported_batches=valid_batches,
    )

    return InventoryImportResponse(
        status="SUCCESS" if val_result.is_valid else "PARTIAL_SUCCESS" if valid_batches else "FAILED",
        message=f"Processed {total_rows} rows: {len(valid_batches)} valid, {len(errors)} invalid.",
        validation=val_result,
    )


@router.get("/templates/{dataset}", tags=["Templates"])
def get_template(dataset: str) -> Response:
    """Returns downloadable CSV template for specified dataset type (inventory, destinations, transports)."""
    dataset_lower = dataset.lower()

    if dataset_lower == "inventory":
        csv_text = (
            "id,commodity,quantity_kg,unit,remaining_shelf_life_hours,holding_cost_per_kg_hr,spoilage_cost_per_kg\n"
            "BATCH-TOM-01,Tomatoes,2500,kg,48.0,0.08,22.0\n"
            "BATCH-BAN-01,Bananas,3000,kg,72.0,0.06,18.0\n"
            "BATCH-MAN-01,Mangoes,1500,kg,60.0,0.12,65.0\n"
            "BATCH-GRN-01,Leafy Greens,1000,kg,18.0,0.15,20.0\n"
            "BATCH-ONI-01,Onions,4000,kg,120.0,0.04,16.0\n"
        )
        media_type = "text/csv"
        filename = "inventory_template.csv"
    elif dataset_lower == "destinations":
        csv_text = (
            "id,name,commodity,demand_kg,market_price_inr_per_kg,receiving_capacity_kg,priority,demand_window_hours\n"
            "DEST-DELHI,Delhi Azadpur Mandi,Tomatoes,4000,42.0,25000,1,48.0\n"
            "DEST-MUMBAI,Mumbai Vashi APMC,Tomatoes,4500,40.0,28000,1,42.0\n"
        )
        media_type = "text/csv"
        filename = "destinations_template.csv"
    elif dataset_lower == "transports":
        csv_text = (
            "id,origin,destination_id,travel_time_hours,cost_per_kg,capacity_kg,handling_time_hours,available\n"
            "TR-DEL-EXP-01,Central Hub,DEST-DELHI,10.0,4.5,6000,2.0,True\n"
            "TR-MUM-REEFER-01,Central Hub,DEST-MUMBAI,7.0,5.2,5500,1.5,True\n"
        )
        media_type = "text/csv"
        filename = "transports_template.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template type '{dataset}'. Valid options are: inventory, destinations, transports.",
        )

    return Response(
        content=csv_text,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
