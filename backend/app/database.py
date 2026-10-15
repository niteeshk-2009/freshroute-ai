"""SQLite database setup for FreshRoute AI.

Stores saved scenario results and evaluation history.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
from app.models.domain import Scenario, InventoryBatch


DB_PATH = os.getenv("DB_PATH", "freshroute.db")
_db_initialized = False


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    global _db_initialized
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    if not _db_initialized:
        _db_initialized = True
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS evaluation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scenario_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scenarios (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                data_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS custom_inventory (
                id TEXT PRIMARY KEY,
                commodity TEXT NOT NULL,
                quantity_kg REAL NOT NULL,
                unit TEXT NOT NULL,
                remaining_shelf_life_hours REAL NOT NULL,
                holding_cost_per_kg_hr REAL,
                spoilage_cost_per_kg REAL
            );

            CREATE INDEX IF NOT EXISTS idx_eval_scenario ON evaluation_results(scenario_id);
            CREATE INDEX IF NOT EXISTS idx_history_scenario ON scenario_history(scenario_id);
        """)
        conn.commit()
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scenario_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS custom_inventory (
            id TEXT PRIMARY KEY,
            commodity TEXT NOT NULL,
            quantity_kg REAL NOT NULL,
            unit TEXT NOT NULL,
            remaining_shelf_life_hours REAL NOT NULL,
            holding_cost_per_kg_hr REAL,
            spoilage_cost_per_kg REAL
        );

        CREATE INDEX IF NOT EXISTS idx_eval_scenario ON evaluation_results(scenario_id);
        CREATE INDEX IF NOT EXISTS idx_history_scenario ON scenario_history(scenario_id);
    """)
    conn.commit()
    conn.close()


def save_scenario_to_db(scenario: Scenario) -> None:
    """Persists a Scenario model into SQLite."""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO scenarios (id, name, description, data_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            data_json=excluded.data_json
        """,
        (scenario.id, scenario.name, scenario.description, scenario.model_dump_json())
    )
    conn.commit()
    conn.close()


def load_scenario_from_db(scenario_id: str) -> Optional[Scenario]:
    """Loads a Scenario by ID from SQLite."""
    conn = get_db()
    row = conn.execute("SELECT data_json FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    conn.close()
    if row:
        return Scenario.model_validate_json(row["data_json"])
    return None


def list_saved_scenarios() -> List[Scenario]:
    """Retrieves all scenarios persisted in SQLite."""
    conn = get_db()
    rows = conn.execute("SELECT data_json FROM scenarios ORDER BY created_at DESC").fetchall()
    conn.close()
    scenarios: List[Scenario] = []
    for r in rows:
        try:
            scenarios.append(Scenario.model_validate_json(r["data_json"]))
        except Exception:
            pass
    return scenarios


def save_custom_batches(batches: List[InventoryBatch]) -> None:
    """Saves custom imported inventory batches."""
    conn = get_db()
    for b in batches:
        conn.execute(
            """
            INSERT INTO custom_inventory (id, commodity, quantity_kg, unit, remaining_shelf_life_hours,
                                          holding_cost_per_kg_hr, spoilage_cost_per_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                commodity=excluded.commodity,
                quantity_kg=excluded.quantity_kg,
                unit=excluded.unit,
                remaining_shelf_life_hours=excluded.remaining_shelf_life_hours,
                holding_cost_per_kg_hr=excluded.holding_cost_per_kg_hr,
                spoilage_cost_per_kg=excluded.spoilage_cost_per_kg
            """,
            (b.id, b.commodity, b.quantity_kg, b.unit, b.remaining_shelf_life_hours,
             b.holding_cost_per_kg_hr, b.spoilage_cost_per_kg)
        )
    conn.commit()
    conn.close()


def load_custom_batches() -> List[InventoryBatch]:
    """Loads all custom imported inventory batches."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM custom_inventory").fetchall()
    conn.close()
    batches: List[InventoryBatch] = []
    for r in rows:
        batches.append(
            InventoryBatch(
                id=r["id"],
                commodity=r["commodity"],
                quantity_kg=r["quantity_kg"],
                unit=r["unit"],
                remaining_shelf_life_hours=r["remaining_shelf_life_hours"],
                holding_cost_per_kg_hr=r["holding_cost_per_kg_hr"] or 0.08,
                spoilage_cost_per_kg=r["spoilage_cost_per_kg"] or 15.0,
            )
        )
    return batches



def save_evaluation(scenario_id: str, strategy_name: str, result: Dict[str, Any]):
    """Save an evaluation result to the database."""
    conn = get_db()
    conn.execute(
        "INSERT INTO evaluation_results (scenario_id, strategy_name, result_json) VALUES (?, ?, ?)",
        (scenario_id, strategy_name, json.dumps(result))
    )
    conn.commit()
    conn.close()


def get_evaluations(scenario_id: str) -> List[Dict[str, Any]]:
    """Get all evaluation results for a scenario."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM evaluation_results WHERE scenario_id = ? ORDER BY created_at DESC",
        (scenario_id,)
    ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "scenario_id": row["scenario_id"],
            "strategy_name": row["strategy_name"],
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def log_action(scenario_id: str, action: str, details: Optional[Dict] = None):
    """Log a scenario action to history."""
    conn = get_db()
    conn.execute(
        "INSERT INTO scenario_history (scenario_id, action, details_json) VALUES (?, ?, ?)",
        (scenario_id, action, json.dumps(details) if details else None)
    )
    conn.commit()
    conn.close()


def get_history(scenario_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get scenario action history."""
    conn = get_db()
    if scenario_id:
        rows = conn.execute(
            "SELECT * FROM scenario_history WHERE scenario_id = ? ORDER BY created_at DESC LIMIT ?",
            (scenario_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM scenario_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "scenario_id": row["scenario_id"],
            "action": row["action"],
            "details": json.loads(row["details_json"]) if row["details_json"] else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# Auto-initialize database schema on import
init_db()

