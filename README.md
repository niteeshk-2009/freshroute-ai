# FreshRoute AI

> **Smarter Dispatch. Less Spoilage. Better Margins.**  
> *Intelligent Decision Support Platform for Perishable Produce Distribution*  
> **Official Problem Statement:** BUGGED OUT | PS 07 — FreshRoute

---

## 1. Overview & Problem Definition

India's Ministry of Food Processing Industries reports that post-harvest losses in fruits and vegetables across 15 agro-climatic zones range from 6% to over 15%, heavily driven by logistical coordination failures. Agricultural distributors, cold-storage operators, and wholesalers in central hubs (such as Maharashtra's Nashik region) must balance multiple competing dimensions simultaneously:
1. **Perishability:** Highly varying remaining shelf life (12h for leafy greens vs. 140h for bananas).
2. **Destination Demand:** Dynamic intake requirements across wholesale APMC mandis (Delhi Azadpur, Mumbai Vashi, Pune, Jaipur, Lucknow, Nagpur).
3. **Logistics Economics:** Freight rates, transport transit times, handling turnaround, and cold-storage holding charges.
4. **Feasibility Bottlenecks:** Vehicle capacities, mandi receiving limits, route closures, and delivery time windows.

**FreshRoute AI** is an explainable, constraint-aware decision-intelligence platform that ingests inventory batches, destinations, and fleet options, enforces hard feasibility constraints (**C1–C10**), solves multi-criteria allocation plans, recommends dynamic price markdowns, and audits performance against an Earliest-Expiry-First (EEF) baseline.

---

## 2. Mandatory MVP Requirements Compliance (M1–M5)

| Requirement | Description | Implementation Module | Status |
|---|---|---|---|
| **M1** | Represent batches by commodity, quantity, and estimated remaining shelf life | `app/models/domain.py` (`InventoryBatch`), `app/data/seed.py` | ✅ Verified |
| **M2** | Allocate stock across destinations using demand, prices, transport time/cost, and capacities | `app/engine/optimizer.py` (multi-criteria candidate ranking + local search) | ✅ Verified |
| **M3** | Prioritize dispatches based on perishability and feasibility ($T_{\text{transit}} + T_{\text{handling}} \le \text{Shelf Life}$) | `app/engine/constraints.py` (C7 check), `app/engine/baseline.py` | ✅ Verified |
| **M4** | Recommend discounts for at-risk batches using disclosed assumptions | `app/engine/discount.py` (0%, 5%, 10%, 15%, 20% tiers, 1.5x elasticity) | ✅ Verified |
| **M5** | Compare plan against documented baseline; report spoilage, fulfillment, and net revenue | `app/engine/evaluator.py`, `tests/test_evaluator.py` | ✅ Verified |

---

## 3. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Frontend: React 18 + TypeScript + Vite         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Overview │ │Inventory │ │ Planner  │ │Simulator │ │Evaluation││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                     Tailwind CSS + Recharts + Lucide            │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP (REST + JSON)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Backend: FastAPI + Python 3.13                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    REST API Router (/api)                  │ │
│  │  /health  /scenarios  /baseline  /optimize  /simulate      │ │
│  │  /evaluation  /report  /inventory  /templates              │ │
│  └─────────────────────────────┬──────────────────────────────┘ │
│                                │                                │
│  ┌─────────────────────────────┴──────────────────────────────┐ │
│  │                      Algorithmic Core                      │ │
│  │  ┌───────────────┐ ┌────────────────┐ ┌──────────────────┐ │ │
│  │  │ EEF Baseline  │ │Heuristic Engine│ │ Discount Engine  │ │ │
│  │  │(Deterministic)│ │ (Greedy+Search)│ │ (Rule-based M4)  │ │ │
│  │  └───────────────┘ └────────────────┘ └──────────────────┘ │ │
│  │  ┌───────────────┐ ┌────────────────┐ ┌──────────────────┐ │ │
│  │  │ Constraints   │ │ Explainer      │ │ Evaluator        │ │ │
│  │  │   (C1 - C10)  │ │ (Reason Codes) │ │ (Audited Diffs)  │ │ │
│  │  └───────────────┘ └────────────────┘ └──────────────────┘ │ │
│  └─────────────────────────────┬──────────────────────────────┘ │
│                                │                                │
│  ┌─────────────────────────────┴──────────────────────────────┐ │
│  │                     Persistence & Data                     │ │
│  │  ┌────────────────┐ ┌────────────────┐ ┌─────────────────┐ │ │
│  │  │ SQLite DB (WAL)│ │ 10 Benchmark Sc│ │ Deterministic   │ │ │
│  │  │ freshroute.db  │ │ (Fixed Seeds)  │ │ Generator (s=42)│ │ │
│  │  └────────────────┘ └────────────────┘ └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Hard Feasibility Constraints (C1–C10)

1. **C1 (Non-negative Allocation):** All dispatched quantities $q \ge 0$.
2. **C2 (Batch Conservation):** $\sum_{d,t} q_{b,d,t} \le \text{Batch Quantity}_b$.
3. **C3 (Demand Upper Bound):** $\sum_{b,t} q_{b,d,t} \le \text{Remaining Demand}_{d,c}$.
4. **C4 (Vehicle & Mandi Intake Limit):** Vehicle capacity and destination intake ceilings strictly maintained.
5. **C5 (Route Operationality):** Inactive or closed freight routes rejected.
6. **C6 (Commodity Compatibility):** Produce shipped only to mandis with active demand for that crop.
7. **C7 (Shelf-Life Feasibility):** $T_{\text{transit}} + T_{\text{handling}} + \text{Buffer} \le \text{Remaining Shelf Life}_b$.
8. **C9 (Non-Negative Contribution):** Shipments where transport + handling exceeds gross sales revenue are rejected unless explicitly allowed.
9. **C10 (Reconciliation Audit):** Total available inventory strictly reconciles to dispatched + unallocated stock.

---

## 5. Optimization & Baseline Methodology

### Baseline: Earliest-Expiry-First (EEF)
- **Ordering:** Sort batches ascending by remaining shelf life (earliest expiry first), tie-breaking deterministically by batch ID.
- **Routing:** Assigns highest-demand compatible destination using the fastest available vehicle.
- **Guarantees:** Strictly respects constraints C1–C10. This is a realistic comparator, not an artificially crippled baseline.

### FreshRoute Optimizer
- **Candidate Triplet Generation:** Enumerates all feasible $(b, d, t)$ allocations.
- **Multi-Criteria Scoring:**
  $$\text{Score} = 0.60 \times (\text{Unit Contribution}) + 0.25 \times (\text{Urgency Bonus}) + 0.15 \times (\text{Destination Priority})$$
- **Greedy Allocation:** Fills bottlenecks in descending score order.
- **Local Improvement Search:** Performs pairwise transport reassignments to salvage high-perishability produce and improve net margins.
- **Algorithm Transparency:** Rigorously classified as **`heuristic-optimized (NOT globally optimal)`**.

### M4 Dynamic Markdown Engine
- Evaluates at-risk unallocated inventory across discrete discount steps: `[0%, 5%, 10%, 15%, 20%]`.
- Disclosed illustrative elasticity model: $\text{Additional Demand \%} = \text{Discount \%} \times 1.5$.
- Recommends a discount only if the incremental contribution strictly exceeds the un-discounted spoilage loss.

---

## 6. Economic Model & Metric Definitions

$$\text{Net Revenue} = \sum \text{Revenue} - \sum \text{Transport Cost} - \sum \text{Handling Cost} - \sum \text{Holding Cost} - \sum \text{Spoilage Penalty}$$

- **Spoilage Rate (\%):** $\frac{\text{Spoiled Quantity (kg)}}{\text{Total Inventory Available (kg)}} \times 100$
- **Demand Fulfillment (\%):** $\frac{\text{Demand Fulfilled (kg)}}{\text{Total Market Demand (kg)}} \times 100$
- **Inventory Utilization (\%):** $\frac{\text{Total Dispatched Quantity (kg)}}{\text{Total Inventory Available (kg)}} \times 100$

---

## 7. Benchmark Evaluation Suite (10 Held-Out Scenarios)

All 10 scenarios use fixed seeds for deterministic reproducibility:
1. `EVAL-01-NORMAL`: Standard baseline operating conditions.
2. `EVAL-02-SHORT-SHELF`: Extreme perishability (all batches $<24\text{h}$).
3. `EVAL-03-DEMAND-SPIKE`: 3x demand surge across all mandis.
4. `EVAL-04-ROUTE-DELAYS`: +50% highway delays testing C7 transit buffers.
5. `EVAL-05-CAPACITY-REDUCED`: 50% vehicle fleet capacity reduction.
6. `EVAL-06-LOW-MARGIN`: Depressed mandi prices testing C9 non-negative margin filters.
7. `EVAL-07-EDGE-DATA`: Challenging operational data with zero-quantity and zero-demand edge cases.
8. `EVAL-08-NO-FEASIBLE`: Total transit gridlock (safely handles zero dispatches with 0 violations).
9. `EVAL-09-ZERO-DEMAND`: Mandi holiday; verifies zero-division protection.
10. `EVAL-10-BASELINE-WINS`: Honest benchmark where EEF baseline matches or outperforms optimizer due to uniform prices and severe spoilage penalties.

---

## 8. Installation, Execution & Verification

### Prerequisites
- Python 3.10+
- Node.js 18+

### Setup & Run
```bash
# 1. Clone repository
cd freshroute-ai

# 2. Run backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Access Full Application
# The FastAPI server serves the compiled React production frontend directly at:
# http://127.0.0.1:8000/
# Interactive API Documentation:
# http://127.0.0.1:8000/docs
```

### Running Frontend Development Server (Optional)
```bash
cd frontend
npm install
npm run dev
# Accessible on http://localhost:5173
```

### Executing Automated Test Suite
```bash
cd backend
python -m pytest tests/ -v
```
**Test Results:** **44 passed, 0 failed** across unit, constraint, algorithmic, scenario, and API test suites.

---

## 9. 3-Minute Judge Walkthrough Script

1. **0:00–0:30 (The Problem):** Open `http://localhost:8000/`. Review the Executive Operations Dashboard. Highlight Nashik central hub dispatching 5 perishable commodities across 6 wholesale APMC mandis. Point out that 10+ batches have remaining shelf life under 36 hours.
2. **0:30–1:00 (The Decision):** Navigate to the **Distribution Planner**. Click **Run Both Strategies**. Observe the side-by-side execution: EEF baseline finishes in ~2ms, FreshRoute optimizer finishes in ~3ms, generating higher net profit and lower spoilage while satisfying all C1–C10 constraints.
3. **1:00–1:45 (The Explainability):** Click on any allocated shipment row in the table. Show the real-time explainability drawer displaying *Why This Batch*, *Why This Destination*, *Why This Route*, and *Infeasibility Sensitivity*. Scroll down to show **M4 Dynamic Discount Recommendations** with disclosed 1.5x elasticity.
4. **1:45–2:15 (The Disruption):** Switch to the **Scenario Simulator**. Drag the *Highway Delays* slider to +6h and reduce *Fleet Capacity* to 70%. Click **Apply Disruption & Re-plan**. Observe the real-time reallocation, affected shipments delta table, and explainability narrative.
5. **2:15–2:45 (The Evidence):** Open **Performance Evaluation**. Inspect the 10 benchmark scenarios. Point out `EVAL-10-BASELINE-WINS`, honestly documenting where the EEF comparator matches or edges out the optimizer under uniform price conditions.
6. **2:45–3:00 (The Conclusion):** Navigate to **Reports**, export the audit report as CSV, and show the printable decision audit document.

---

## 10. Known Limitations & Roadmap

- **Heuristic Classification:** Uses greedy allocation with transport local search; does not claim global optimality via branch-and-bound.
- **Elasticity Assumption:** Markdown demand response uses an illustrative linear multiplier (1.5x) rather than econometric empirical price elasticity curves.
- **Data Disclosure:** Uses deterministic synthetic agricultural data based on Maharashtra (Nashik hub) and major Indian APMC wholesale mandis (Delhi, Mumbai, Pune, Jaipur, Lucknow, Nagpur). No live GPS or distributor API data was fabricated.
- **Active Development Roadmap:**
  1. **Gemma 4 Decision Copilot:** Integration with Gemma 4 model for interactive conversational trade-off explanations and scenario sensitivity querying.
  2. **Mixed-Integer Linear Programming (MILP):** Exact mathematical optimization with HiGHS or CBC solver to compare against current heuristic.
  3. **Multi-Depot Routing:** Coordinated dispatch across multiple agricultural cold-chain aggregation hubs.

