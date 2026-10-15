# FreshRoute AI — Requirements Traceability Matrix

## Official Problem: PS 07 — FreshRoute: Intelligent Decision Support for Perishable Produce Distribution

---

## Mandatory MVP Requirements

| Req ID | Official Requirement | Data Model | Algorithm | API Endpoint | UI Component | Test |
|--------|---------------------|------------|-----------|-------------|-------------|------|
| **M1** | Represent inventory batches by commodity, quantity, and estimated remaining shelf life | `InventoryBatch` (commodity, quantity_kg, remaining_shelf_life_hours) | Seed data generator | `GET /api/inventory`, `POST /api/inventory/import` | Inventory page with search, filter, sort | `test_inventory_model`, `test_csv_import` |
| **M2** | Allocate stock across destinations using demand, prices, transport time/cost, capacity constraints | `Destination`, `TransportOption`, `ShipmentPlan` | Constraint-aware optimizer with economic objective | `POST /api/scenarios/{id}/optimize` | Distribution Planner with allocation table | `test_optimizer`, `test_constraints` |
| **M3** | Prioritize dispatches based on perishability and feasibility (arrival + handling ≤ shelf life) | `ShipmentPlan.shelf_life_remaining_at_delivery_hours` | EEF baseline + optimizer urgency ranking + C7 constraint | `POST /api/scenarios/{id}/baseline`, `/optimize` | Dispatch priority view, feasibility indicators | `test_shelf_life_feasibility`, `test_dispatch_priority` |
| **M4** | Recommend discounts for at-risk batches using disclosed assumptions | `DiscountRecommendation` | Rule-based discount engine with configurable levels | Included in optimize/evaluate response | Discount recommendations panel | `test_discount_engine` |
| **M5** | Compare plan against baseline; report spoilage, demand fulfillment, net revenue | `EvaluationResult`, `ComparisonResult` | Evaluator with consistent metric calculations | `GET /api/scenarios/{id}/evaluation` | Performance Evaluation page, comparison charts | `test_evaluator`, `test_fair_comparison` |

## Feasibility Constraints (C1–C10)

| ID | Constraint | Implementation | Test |
|----|-----------|----------------|------|
| C1 | Non-negative allocation quantities | `constraints.check_non_negative()` | `test_non_negative` |
| C2 | Dispatch ≤ available quantity per batch | `constraints.check_batch_capacity()` | `test_batch_capacity` |
| C3 | Allocation ≤ remaining demand per destination | `constraints.check_demand_limit()` | `test_demand_limit` |
| C4 | Transport capacity not exceeded | `constraints.check_transport_capacity()` | `test_transport_capacity` |
| C5 | No unavailable routes | `constraints.check_route_available()` | `test_route_availability` |
| C6 | Commodity-destination compatibility | `constraints.check_compatibility()` | `test_compatibility` |
| C7 | Arrival + handling ≤ remaining shelf life | `constraints.check_shelf_life()` | `test_shelf_life_constraint` |
| C8 | Consistent units (kg, hours, INR) | Domain models with explicit units | `test_unit_consistency` |
| C9 | No negative-contribution unless policy allows | `constraints.check_contribution()` | `test_negative_contribution` |
| C10 | Allocations reconcile with inventory/demand | `constraints.check_reconciliation()` | `test_reconciliation` |

## Economic Model

| Term | Sign | Description |
|------|------|-------------|
| Sales Revenue | + | `allocated_qty × market_price × (1 - discount_pct)` |
| Transport Cost | − | `allocated_qty × transport_cost_per_kg` |
| Handling Cost | − | `allocated_qty × handling_cost_per_kg` |
| Holding Cost | − | `unsold_qty × holding_cost_per_kg_hr × holding_hours` |
| Spoilage/Disposal Cost | − | `spoiled_qty × spoilage_cost_per_kg` |
| **Net Revenue** | = | `Sales Revenue − Transport Cost − Handling Cost − Holding Cost − Spoilage Cost` |

## Outcome Metrics

| Metric | Formula | Direction |
|--------|---------|-----------|
| Spoilage Rate | `spoiled_qty / total_available_qty × 100` | Lower is better |
| Demand Fulfillment | `fulfilled_demand / total_demand × 100` | Higher is better |
| Net Revenue | Sum of net contributions | Higher is better |
| Inventory Utilization | `dispatched_qty / total_available_qty × 100` | Higher is better |

## Held-Out Evaluation Scenarios

| # | Scenario | Purpose |
|---|----------|---------|
| 1 | Normal distribution | Baseline performance |
| 2 | Extremely short shelf life | Urgency handling |
| 3 | Demand spikes | Capacity stress |
| 4 | Route delays | Feasibility changes |
| 5 | Capacity reductions | Constraint tightening |
| 6 | Low-margin destinations | Economic optimization |
| 7 | Missing/malformed records | Data validation |
| 8 | No feasible shipment | Edge case handling |
| 9 | Zero demand | Graceful degradation |
| 10 | Baseline wins | Honest reporting |
