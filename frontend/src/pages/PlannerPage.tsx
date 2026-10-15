import React, { useState } from 'react';
import {
  Truck,
  Play,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  FileSpreadsheet,
  ArrowRight,
  TrendingUp,
  Percent,
  IndianRupee,
  Clock,
  ChevronRight,
  Tag,
} from 'lucide-react';
import { Scenario, EvaluationResult, ShipmentPlan, DiscountRecommendation } from '../types';
import { runBaseline, runOptimizer } from '../services/api';
import { Badge } from '../components/Badge';

interface PlannerPageProps {
  scenario: Scenario | null;
  onRefreshScenario: () => void;
}

export const PlannerPage: React.FC<PlannerPageProps> = ({ scenario, onRefreshScenario }) => {
  const [activeStrategy, setActiveStrategy] = useState<'optimized' | 'baseline'>('optimized');
  const [running, setRunning] = useState(false);
  const [baselineResult, setBaselineResult] = useState<EvaluationResult | null>(null);
  const [optimizedResult, setOptimizedResult] = useState<EvaluationResult | null>(null);
  const [discountRecs, setDiscountRecs] = useState<DiscountRecommendation[]>([]);
  const [selectedShipment, setSelectedShipment] = useState<ShipmentPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBoth = async () => {
    if (!scenario) return;
    setRunning(true);
    setError(null);
    try {
      const [baseRes, optRes] = await Promise.all([
        runBaseline(scenario.id),
        runOptimizer(scenario.id),
      ]);
      setBaselineResult(baseRes.result);
      setOptimizedResult(optRes.result);
      setDiscountRecs(optRes.discount_recommendations || []);
      if (optRes.result.shipments.length > 0) {
        setSelectedShipment(optRes.result.shipments[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Execution error');
    } finally {
      setRunning(false);
    }
  };

  const currentResult = activeStrategy === 'optimized' ? optimizedResult : baselineResult;
  const shipments = currentResult?.shipments || [];

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Truck className="h-6 w-6 text-forest-700" />
              Distribution Dispatch Planner
            </h2>
            <Badge variant="success" size="sm">C1-C10 Hard Constraints</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            M2, M3, M4: Demand-aware allocation, shelf-life arrival feasibility, and dynamic markdown decisions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunBoth}
            disabled={running || !scenario}
            className="flex items-center gap-2 rounded-xl bg-forest-900 px-5 py-2.5 text-xs font-bold text-white shadow hover:bg-forest-800 active:scale-95 transition disabled:opacity-50"
          >
            <Play className={`h-4 w-4 text-fresh-lime ${running ? 'animate-spin' : ''}`} />
            {running ? 'Solving Allocations...' : 'Run Both Strategies'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800">
          {error}
        </div>
      )}

      {/* Strategy Toggle Tabs & KPI Strip */}
      {currentResult && (
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveStrategy('optimized')}
                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
                  activeStrategy === 'optimized'
                    ? 'bg-forest-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <Sparkles className={`h-3.5 w-3.5 ${activeStrategy === 'optimized' ? 'text-fresh-lime' : ''}`} />
                FreshRoute Optimizer (Heuristic)
              </button>
              <button
                onClick={() => setActiveStrategy('baseline')}
                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
                  activeStrategy === 'baseline'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                Earliest-Expiry-First (EEF Baseline)
              </button>
            </div>

            <div className="text-xs text-slate-500 font-medium">
              Execution time: <strong className="text-slate-900 font-mono">{currentResult.execution_time_ms.toFixed(1)} ms</strong>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <span className="text-[11px] font-semibold text-slate-400">Net Profit</span>
              <p className="text-base font-extrabold text-slate-900 mt-0.5">
                ₹{currentResult.net_revenue.toLocaleString('en-IN')}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <span className="text-[11px] font-semibold text-slate-400">Estimated Spoilage</span>
              <p className="text-base font-extrabold text-rose-600 mt-0.5">
                {currentResult.spoilage_rate_pct}% ({currentResult.spoiled_qty_kg.toLocaleString('en-IN')} kg)
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <span className="text-[11px] font-semibold text-slate-400">Demand Fulfilled</span>
              <p className="text-base font-extrabold text-slate-900 mt-0.5">
                {currentResult.fulfillment_pct}% ({currentResult.demand_fulfilled_qty_kg.toLocaleString('en-IN')} kg)
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <span className="text-[11px] font-semibold text-slate-400">Feasible Shipments</span>
              <p className="text-base font-extrabold text-slate-900 mt-0.5">
                {currentResult.feasible_shipment_count} dispatches
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Allocations Table + Explainability Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Dispatch Shipment Table */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h3 className="text-xs font-bold text-slate-800">
                Planned Shipments ({shipments.length} Total Allocations)
              </h3>
              <p className="text-[11px] text-slate-400">Click any row to inspect explainability and trade-off rationale</p>
            </div>
            {currentResult && (
              <Badge variant="success" size="sm">
                C7 Shelf-Life Buffer &ge; 4.0h
              </Badge>
            )}
          </div>

          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            {shipments.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                No shipments calculated yet. Click <strong>Run Both Strategies</strong> above to solve allocations.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Batch</th>
                    <th className="py-2.5 px-3 font-semibold">Destination Mandi</th>
                    <th className="py-2.5 px-3 font-semibold">Transport</th>
                    <th className="py-2.5 px-3 font-semibold">Weight</th>
                    <th className="py-2.5 px-3 font-semibold">Delivery Remaining</th>
                    <th className="py-2.5 px-3 font-semibold">Net Margin</th>
                    <th className="py-2.5 px-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shipments.map((s, idx) => {
                    const isSelected = selectedShipment?.batch_id === s.batch_id && selectedShipment?.transport_id === s.transport_id;
                    const marginTight = s.shelf_life_remaining_at_delivery_hours < 12;

                    return (
                      <tr
                        key={`${s.batch_id}-${s.transport_id}-${idx}`}
                        onClick={() => setSelectedShipment(s)}
                        className={`cursor-pointer transition ${
                          isSelected ? 'bg-forest-50/80 font-medium' : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{s.batch_id}</td>
                        <td className="py-2.5 px-3 text-slate-700">{s.destination_id.replace('DEST-', '')}</td>
                        <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">{s.transport_id}</td>
                        <td className="py-2.5 px-3 font-bold text-slate-900 font-mono">
                          {s.allocated_qty_kg.toLocaleString('en-IN')} kg
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-flex items-center gap-1 font-semibold ${marginTight ? 'text-amber-600' : 'text-emerald-700'}`}>
                            <Clock className="h-3 w-3" />
                            {s.shelf_life_remaining_at_delivery_hours.toFixed(1)}h
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-emerald-700 font-bold">
                          ₹{s.net_contribution.toLocaleString('en-IN')}
                        </td>
                        <td className="py-2.5 px-2 text-slate-400">
                          <ChevronRight className="h-4 w-4" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: Transparent Explainability Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-forest-700" />
              <h3 className="text-sm font-bold text-slate-900">Decision Explainability</h3>
            </div>
            {selectedShipment && (
              <Badge variant="info" size="sm">
                Rank #{selectedShipment.explanation?.dispatch_priority ? selectedShipment.explanation.dispatch_priority.split('#')[1]?.split('.')[0] : '1'}
              </Badge>
            )}
          </div>

          {selectedShipment ? (
            <div className="space-y-3.5 text-xs">
              <div>
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Why This Batch?</span>
                <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  {selectedShipment.explanation?.why_this_batch || 'Allocated based on earliest-expiry urgency.'}
                </p>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Why This Destination?</span>
                <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  {selectedShipment.explanation?.why_this_destination || 'Highest unfulfilled demand at attractive market price.'}
                </p>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Why This Route & Vehicle?</span>
                <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  {selectedShipment.explanation?.why_this_route || 'Optimal trade-off between transit speed and per-kg freight cost.'}
                </p>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Economic Breakdown</span>
                <div className="mt-0.5 bg-slate-50 p-2.5 rounded-xl border border-slate-100 space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Gross Sales:</span>
                    <span className="font-bold text-slate-900">₹{selectedShipment.revenue.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between text-rose-600">
                    <span>Freight Cost:</span>
                    <span>-₹{selectedShipment.transport_cost.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between text-rose-600">
                    <span>Handling Cost:</span>
                    <span>-₹{selectedShipment.handling_cost.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-200 pt-1 text-emerald-700 font-bold">
                    <span>Net Contribution:</span>
                    <span>₹{selectedShipment.net_contribution.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Infeasibility Sensitivity</span>
                <p className="mt-0.5 text-slate-600 leading-relaxed bg-amber-50/70 p-2.5 rounded-xl border border-amber-200/60 text-[11px]">
                  {selectedShipment.explanation?.what_makes_infeasible || 'Would violate C7 if road transit experiences >4.0h delay.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">
              Select an allocation row from the table to view its full mathematical justification.
            </div>
          )}
        </div>
      </div>

      {/* M4 Discount Recommendations Panel */}
      <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="h-5 w-5 text-amber-700" />
            <div>
              <h3 className="text-sm font-bold text-amber-950">
                M4 Dynamic Discount Recommendations ({discountRecs.length} Batches Evaluated)
              </h3>
              <p className="text-xs text-amber-800">
                Rule-based price markdown suggestions for at-risk unallocated inventory under 1.5x demand elasticity assumptions.
              </p>
            </div>
          </div>
          <Badge variant="warning" size="sm">Elasticity 1.5x Disclosed</Badge>
        </div>

        {discountRecs.length === 0 ? (
          <p className="text-xs text-amber-800 italic">
            Run optimizer to evaluate discounting opportunities for near-expiry or unallocated batches.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {discountRecs.map((rec) => (
              <div key={rec.batch_id} className="rounded-xl border border-amber-200 bg-white p-3.5 text-xs shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold font-mono text-slate-900">{rec.batch_id}</span>
                  <Badge variant={rec.recommended_discount_pct > 0 ? 'success' : 'neutral'} size="sm">
                    {rec.recommended_discount_pct > 0 ? `${rec.recommended_discount_pct}% Markdown` : 'No Discount'}
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-600 line-clamp-2">
                  {rec.risk_reason}
                </p>
                <div className="bg-slate-50 p-2 rounded-lg font-mono text-[11px] space-y-0.5">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Price:</span>
                    <span>₹{rec.original_price_inr} &rarr; ₹{rec.discounted_price_inr}/kg</span>
                  </div>
                  <div className="flex justify-between text-emerald-700 font-semibold">
                    <span>Net Margin Impact:</span>
                    <span>+₹{rec.expected_net_contribution_change_inr}</span>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">
                  {rec.assumptions}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
