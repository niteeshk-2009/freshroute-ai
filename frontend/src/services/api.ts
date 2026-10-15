import {
  Scenario,
  ScenarioSummary,
  InventoryBatch,
  EvaluationResult,
  ComparisonResponse,
  SimulationModifications,
} from '../types';

const rawApiUrl = (import.meta as any).env?.VITE_API_URL;
const API_BASE = rawApiUrl ? `${rawApiUrl.replace(/\/+$/, '')}/api` : '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch health check');
  return res.json();
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios list');
  return res.json();
}

export async function fetchScenario(id: string): Promise<Scenario> {
  const res = await fetch(`${API_BASE}/scenarios/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch scenario ${id}`);
  return res.json();
}

export async function runBaseline(scenarioId: string): Promise<EvaluationResult> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/baseline`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to run baseline allocation');
  return res.json();
}

export async function runOptimizer(scenarioId: string): Promise<EvaluationResult> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/optimize`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to run optimizer allocation');
  return res.json();
}

export async function fetchDiscounts(scenarioId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/discounts`);
  if (!res.ok) {
    // Graceful fallback to report if discount endpoint fails
    const report = await fetchReport(scenarioId);
    return report.discount_recommendations || [];
  }
  return res.json();
}

export async function runEvaluation(scenarioId: string): Promise<ComparisonResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/evaluation`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation for ${scenarioId}`);
  return res.json();
}

export async function runSimulation(
  scenarioId: string,
  modifications: SimulationModifications,
  strategy = 'heuristic_optimized'
): Promise<{
  scenario_id: string;
  original_comparison: ComparisonResponse;
  modified_comparison: ComparisonResponse;
  modifications_applied: any;
  affected_shipments: any[];
  changes_explanation: string;
}> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy, modifications }),
  });
  if (!res.ok) throw new Error('Failed to run simulation');
  return res.json();
}

export async function fetchReport(scenarioId: string) {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/report`);
  if (!res.ok) throw new Error('Failed to fetch scenario audit report');
  return res.json();
}

export async function fetchInventory(): Promise<InventoryBatch[]> {
  const res = await fetch(`${API_BASE}/inventory`);
  if (!res.ok) throw new Error('Failed to fetch inventory');
  return res.json();
}

export async function importInventoryCSV(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/inventory/import`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(err.detail || 'CSV Import failed');
  }
  return res.json();
}

export function getTemplateDownloadUrl(dataset: 'inventory' | 'destinations' | 'transports') {
  return `${API_BASE}/templates/${dataset}`;
}
