"""Comprehensive REST API test suite for FreshRoute AI."""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.scenarios import list_scenarios

client = TestClient(app)


def test_api_health_check():
    """GET /api/health returns 200 with service metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_api_list_scenarios():
    """GET /api/scenarios lists all available benchmark scenarios."""
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "total_inventory_kg" in first
    assert "total_demand_kg" in first


def test_api_get_scenario_by_id_valid():
    """GET /api/scenarios/{id} retrieves full scenario detail."""
    response = client.get("/api/scenarios/EVAL-01-NORMAL")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "EVAL-01-NORMAL"
    assert len(data["inventory_batches"]) > 0
    assert len(data["destinations"]) > 0
    assert len(data["transport_options"]) > 0


def test_api_get_scenario_by_id_not_found():
    """GET /api/scenarios/{id} returns 404 for non-existent scenario."""
    response = client.get("/api/scenarios/NON-EXISTENT-ID-999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_api_run_baseline_endpoint():
    """POST /api/scenarios/{id}/baseline executes EEF baseline."""
    response = client.post("/api/scenarios/EVAL-01-NORMAL/baseline")
    assert response.status_code == 200
    data = response.json()
    assert "Earliest-Expiry-First" in data["strategy_name"]
    assert "net_revenue" in data
    assert "spoilage_rate_pct" in data
    assert "shipments" in data
    assert len(data["shipments"]) > 0


def test_api_run_optimizer_endpoint():
    """POST /api/scenarios/{id}/optimize executes heuristic optimizer."""
    response = client.post("/api/scenarios/EVAL-01-NORMAL/optimize")
    assert response.status_code == 200
    data = response.json()
    assert "optimizer" in data["strategy_name"].lower() or "heuristic" in data["strategy_name"].lower()
    assert "net_revenue" in data
    assert len(data["shipments"]) > 0


def test_api_simulate_endpoint():
    """POST /api/scenarios/{id}/simulate executes what-if scenario with modifications."""
    payload = {
        "strategy": "heuristic_optimized",
        "modifications": {
            "demand_multipliers": {"Tomatoes": 2.0},
            "allow_negative_contribution": False,
        },
    }
    response = client.post("/api/scenarios/EVAL-01-NORMAL/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "net_revenue" in data
    assert len(data["shipments"]) > 0


def test_api_strategy_evaluation():
    """GET /api/scenarios/{id}/evaluation returns side-by-side strategy comparison."""
    response = client.get("/api/scenarios/EVAL-01-NORMAL/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "baseline" in data
    assert "optimized" in data
    assert "comparison" in data
    assert "summary" in data


def test_api_scenario_report():
    """GET /api/scenarios/{id}/report returns executive audit report."""
    response = client.get("/api/scenarios/EVAL-01-NORMAL/report")
    assert response.status_code == 200
    data = response.json()
    assert "scenario_id" in data
    assert "baseline_evaluation" in data
    assert "optimized_evaluation" in data
    assert "comparison" in data
    assert "discount_recommendations" in data
    assert "validation_report" in data
    assert data["validation_report"]["is_valid"] is True


def test_api_get_inventory():
    """GET /api/inventory retrieves current inventory batches."""
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "commodity" in data[0]
    assert "quantity_kg" in data[0]


def test_api_inventory_import_valid_csv():
    """POST /api/inventory/import processes and validates CSV upload."""
    csv_content = (
        "id,commodity,quantity_kg,unit,remaining_shelf_life_hours,holding_cost_per_kg_hr,spoilage_cost_per_kg\n"
        "BATCH-TEST-01,Tomatoes,3000,kg,48.0,0.08,20.0\n"
        "BATCH-TEST-02,Bananas,2500,kg,72.0,0.06,15.0\n"
    )
    files = {"file": ("test_inventory.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/inventory/import", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["validation"]["valid_count"] == 2
    assert data["validation"]["invalid_count"] == 0


def test_api_inventory_import_invalid_file_extension():
    """POST /api/inventory/import rejects non-csv files with 400 Bad Request."""
    files = {"file": ("test.txt", io.BytesIO(b"some,data"), "text/plain")}
    response = client.post("/api/inventory/import", files=files)
    assert response.status_code == 400


def test_api_inventory_import_missing_columns():
    """POST /api/inventory/import rejects missing mandatory columns with 422."""
    csv_content = "id,commodity\nBATCH-01,Tomatoes\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/inventory/import", files=files)
    assert response.status_code == 422


def test_api_templates_download():
    """GET /api/templates/{dataset} downloads valid CSV templates."""
    for dataset in ["inventory", "destinations", "transports"]:
        response = client.get(f"/api/templates/{dataset}")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert len(response.text) > 0


def test_api_get_scenario_discounts():
    """GET /api/scenarios/{id}/discounts returns discount recommendations."""
    response = client.get("/api/scenarios/EVAL-01-NORMAL/discounts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_planner_shipments_contract_always_present():
    """Regression test: verifies optimizer and baseline always include 'shipments' as a list.
    Even on scenarios with zero feasible dispatches, shipments must never be missing or undefined.
    """
    for sc_id in ["EVAL-01-NORMAL", "EVAL-08-NO-FEASIBLE", "EVAL-09-ZERO-DEMAND"]:
        res_opt = client.post(f"/api/scenarios/{sc_id}/optimize")
        assert res_opt.status_code == 200
        data_opt = res_opt.json()
        assert "shipments" in data_opt, f"Optimizer response missing 'shipments' for {sc_id}"
        assert isinstance(data_opt["shipments"], list)

        res_base = client.post(f"/api/scenarios/{sc_id}/baseline")
        assert res_base.status_code == 200
        data_base = res_base.json()
        assert "shipments" in data_base, f"Baseline response missing 'shipments' for {sc_id}"
        assert isinstance(data_base["shipments"], list)


def test_api_metric_definitions_consistency():
    """Verifies that net profit strictly satisfies the audited formula across strategies:
    net_revenue == total_revenue - (transport + handling + holding + spoilage costs)
    """
    for endpoint in ["baseline", "optimize"]:
        res = client.post(f"/api/scenarios/EVAL-01-NORMAL/{endpoint}")
        assert res.status_code == 200
        d = res.json()
        calculated_net = d["total_revenue"] - (
            d["total_transport_cost"] + d["total_handling_cost"] + d["total_holding_cost"] + d["total_spoilage_cost"]
        )
        assert abs(d["net_revenue"] - calculated_net) < 0.05, f"Net revenue formula mismatch in {endpoint}"


