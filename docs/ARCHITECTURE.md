# FreshRoute AI — Architecture Document

## System Overview

FreshRoute AI is a full-stack decision-support platform for perishable produce distribution. It uses constraint-aware optimization to generate explainable allocation plans and compares them against a documented baseline strategy.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Overview  │ │Inventory │ │ Planner  │ │Simulator │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │Evaluation│ │ Reports  │ │ Settings │                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
│                         │                                        │
│                    REST API Calls                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + Python)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer (routes.py)                    │  │
│  │  /health  /scenarios  /inventory  /templates  /reports    │  │
│  └──────────────────────────┬───────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────┴──────────────────────────────┐   │
│  │                   Engine Layer                             │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐    │  │
│  │  │ Baseline   │ │ Optimizer  │ │ Discount Engine    │    │  │
│  │  │ (EEF)      │ │ (Greedy+   │ │ (Rule-based)       │    │  │
│  │  │            │ │  Local     │ │                    │    │  │
│  │  │            │ │  Search)   │ │                    │    │  │
│  │  └────────────┘ └────────────┘ └────────────────────┘    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐    │  │
│  │  │Constraints │ │ Evaluator  │ │ Explainer          │    │  │
│  │  │ (C1-C10)   │ │ (Metrics)  │ │ (Decision Reasons) │    │  │
│  │  └────────────┘ └────────────┘ └────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────┴──────────────────────────────┐   │
│  │                   Data Layer                               │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐    │  │
│  │  │ Seed Data  │ │ Scenarios  │ │ SQLite Database    │    │  │
│  │  │ Generator  │ │ (10 held-  │ │ (Persistence)      │    │  │
│  │  │ (seed=42)  │ │  out)      │ │                    │    │  │
│  │  └────────────┘ └────────────┘ └────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 19 + TypeScript + Vite | Modern, fast build, type safety |
| Styling | Tailwind CSS | Utility-first, rapid prototyping |
| Charts | Recharts | React-native charting, good defaults |
| Icons | Lucide React | Consistent, lightweight icon system |
| Backend | Python 3.13 + FastAPI | Fast async API, Pydantic validation |
| Models | Pydantic v2 | Runtime validation, serialization |
| Database | SQLite | Zero-config, file-based persistence |
| Testing | Pytest + TypeScript checks | Comprehensive backend testing |

## Data Flow

1. **Seed/Import** → Inventory, destinations, transport options loaded
2. **Scenario Creation** → Snapshot of all inputs saved
3. **Baseline Execution** → EEF algorithm allocates with constraints
4. **Optimization** → Greedy + improvement pass maximizes net revenue
5. **Discount Engine** → Identifies at-risk batches, recommends discounts
6. **Evaluation** → Metrics computed for both strategies
7. **Comparison** → Side-by-side results with explanations
8. **Export/Report** → Downloadable results in CSV/JSON

## Optimization Methodology

### Baseline: Earliest-Expiry-First (EEF)
- Sort batches by remaining shelf life (ascending)
- For each batch, assign to highest-demand feasible destination
- Respect all C1-C10 constraints
- Deterministic tie-breaking by batch ID

### Optimizer: Constraint-Aware Greedy with Local Search
1. **Candidate Generation**: All feasible (batch, destination, transport) triples
2. **Scoring**: Economic contribution per kg, adjusted for urgency
3. **Greedy Allocation**: Top-scoring candidates first, constraints checked
4. **Local Search**: Try swapping allocations to improve objective
5. **Result Classification**: "heuristic-optimized" (never claimed as globally optimal)

### Discount Engine: Rule-Based with Conservative Elasticity
- Evaluates batches with remaining shelf life < threshold
- Tests discount levels: 0%, 5%, 10%, 15%, 20%
- Uses illustrative demand response: `discount% × 1.5 = additional demand%`
- Recommends only when discounted net contribution > undiscounted
- All assumptions disclosed and configurable

## Key Design Decisions

1. **Deterministic algorithms**: All operations use fixed seeds and deterministic ordering
2. **Constraint-first**: Infeasible allocations are rejected, never silently allowed
3. **Honest comparison**: Both strategies use identical inputs and metric calculations
4. **Explainability**: Every decision has a structured reason, not generated prose
5. **Reproducibility**: Same inputs always produce same outputs
