import React, { useState, useEffect } from 'react';
import {
  Truck,
  Play,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  Percent,
  IndianRupee,
  Clock,
  ChevronRight,
  Tag,
  Search,
  Filter,
  ShieldCheck,
  Scale,
  RefreshCw,
} from 'lucide-react';
import { Scenario, EvaluationResult, ShipmentPlan, DiscountRecommendation } from '../types';
import { runBaseline, runOptimizer, fetchDiscounts } from '../services/api';
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
  const [searchFilter, setSearchFilter] = useState('');

  useEffect(() => {
    if (scenario?.id) {
      handleRunBoth();
    }
  }, [scenario?.id]);

  const handleRunBoth = async () => {
    if (!scenario) return;
    setRunning(true);
    setError(null);
    try {
      const [baseRes, optRes, discounts] = await Promise.all([
        runBaseline(scenario.id),
        runOptimizer(scenario.id),
        fetchDiscounts(scenario.id).catch(() => []),
      ]);
      setBaselineResult(baseRes);
      setOptimizedResult(optRes);
      setDiscountRecs(discounts || []);
      if (optRes && optRes.shipments && optRes.shipments.length > 0) {
        setSelectedShipment(optRes.shipments[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Execution error during optimization run.');
    } finally {
      setRunning(false);
    }
  };

  const currentResult = activeStrategy === 'optimized' ? optimizedResult : baselineResult;
  const rawShipments = currentResult?.shipments || [];

  const filteredShipments = rawShipments.filter((s) => {
    if (!searchFilter.trim()) return true;
    const term = searchFilter.toLowerCase();
    return (
      s.batch_id.toLowerCase().includes(term) ||
      s.destination_id.toLowerCase().includes(term) ||
      s.transport_id.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Truck className="h-6 w-6 text-forest-700" />
              Distribution Planner
            </h2>
            <Badge variant="success" size="sm">
              All Feasibility Rules Enforced
            </Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Build a feasible dispatch plan that balances shelf life, demand, transport capacity and profitability.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunBoth}
            disabled={running || !scenario}
            className="flex items-center gap-2 rounded-xl bg-forest-900 px-5 py-2.5 text-xs font-bold text-white shadow hover:bg-forest-800 active:scale-95 transition disabled:opacity-50"
          >
            {running ? (
              <RefreshCw className="h-4 w-4 text-fresh-lime animate-spin" />
            ) : (
              <Play className="h-4 w-4 text-fresh-lime" />
            )}
            {running ? 'Solving Allocations...' : 'Generate Dispatch Plan'}
          </button>
        </div>
      </div>

      {/* Error Alert with Retry */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={handleRunBoth}
            className="rounded-lg bg-rose-100 px-3 py-1 text-xs font-bold text-rose-900 hover:bg-rose-200 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {running && (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm text-center space-y-3">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-forest-50 text-forest-700 animate-pulse">
            <Sparkles className="h-6 w-6 animate-spin" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">
            Evaluating Dispatch Allocations
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Filtering feasible candidate triples (batch, destination mandi, transport route), verifying arrival shelf-life margins, and computing net economic contributions...
          </p>
        </div>
      )}

      {/* Initial Empty State before Running */}
      {!running && !currentResult && (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 shadow-sm text-center space-y-4">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-forest-50 text-forest-700">
            <Truck className="h-8 w-8" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Ready to Solve Distribution Plan
            </h3>
            <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1 leading-relaxed">
              Click <strong>Run Both Strategies</strong> to execute both the Earliest-Expiry-First (EEF) baseline and the multi-criteria FreshRoute optimizer on this scenario.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto pt-2 text-left">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
              <span className="font-bold text-slate-800 block">60% Economic Margin</span>
              <span className="text-[11px] text-slate-500">Gross mandi revenue minus freight and handling.</span>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
              <span className="font-bold text-slate-800 block">25% Perishability Urgency</span>
              <span className="text-[11px] text-slate-500">Prioritizes batches nearest to spoilage cutoffs.</span>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs">
              <span className="font-bold text-slate-800 block">15% Mandi Priority</span>
              <span className="text-[11px] text-slate-500">Safeguards premium Tier-1 demand contracts.</span>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={handleRunBoth}
              disabled={!scenario}
              className="inline-flex items-center gap-2 rounded-xl bg-forest-900 px-6 py-2.5 text-xs font-bold text-white shadow hover:bg-forest-800 active:scale-95 transition"
            >
              <Play className="h-4 w-4 text-fresh-lime" />
              Generate Dispatch Plan
            </button>
          </div>
        </div>
      )}

      {/* Strategy Toggle Tabs & KPI Strip */}
      {!running && currentResult && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveStrategy('optimized')}
                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
                  activeStrategy === 'optimized'
                    ? 'bg-forest-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <Sparkles
                  className={`h-3.5 w-3.5 ${
                    activeStrategy === 'optimized' ? 'text-fresh-lime' : ''
                  }`}
                />
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
              Execution time:{' '}
              <strong className="text-slate-900 font-mono">
                {currentResult.execution_time_ms.toFixed(1)} ms
              </strong>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
              <span className="text-[11px] font-semibold text-slate-400">Net Profit</span>
              <p className="text-base font-extrabold text-slate-900 mt-0.5">
                ₹{currentResult.net_revenue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
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
      {!running && currentResult && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Dispatch Shipment Table */}
          <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col">
            <div className="px-5 py-3.5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50">
              <div>
                <h3 className="text-xs font-bold text-slate-800">
                  Planned Shipments ({filteredShipments.length} of {rawShipments.length} Total Allocations)
                </h3>
                <p className="text-[11px] text-slate-400">
                  Click any row to inspect explainability and trade-off rationale
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                  <input
                    type="text"
                    placeholder="Filter batch or mandi..."
                    aria-label="Filter shipments by batch ID, destination mandi, or transport route"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="pl-8 pr-3 py-1 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-forest-600 focus:border-forest-600 w-44 transition"
                  />
                </div>
                <Badge variant="success" size="sm">
                  Buffer Safety: &ge; 4.0h
                </Badge>
              </div>
            </div>

            <div className="overflow-x-auto max-h-[520px] overflow-y-auto" role="region" aria-label="Dispatch Shipment Allocation Table">
              {filteredShipments.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  {rawShipments.length === 0
                    ? 'No shipments calculated. Click Generate Dispatch Plan above.'
                    : 'No shipments match your filter criteria.'}
                </div>
              ) : (
                <table className="w-full text-left text-xs" aria-label="Feasible Produce Dispatches">
                  <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500">
                    <tr>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Batch</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Destination Mandi</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Transport</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Weight</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Delivery Remaining</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold">Net Contribution</th>
                      <th scope="col" className="py-2.5 px-2" aria-label="Selection indicator"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredShipments.map((s, idx) => {
                      const isSelected =
                        selectedShipment?.batch_id === s.batch_id &&
                        selectedShipment?.transport_id === s.transport_id &&
                        selectedShipment?.destination_id === s.destination_id;
                      const marginTight = s.shelf_life_remaining_at_delivery_hours < 12;

                      return (
                        <tr
                          key={`${s.batch_id}-${s.transport_id}-${s.destination_id}-${idx}`}
                          tabIndex={0}
                          role="button"
                          aria-pressed={isSelected}
                          aria-label={`Shipment ${s.batch_id} to ${s.destination_id.replace('DEST-', '')}, ${s.allocated_qty_kg} kg`}
                          onClick={() => setSelectedShipment(s)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setSelectedShipment(s);
                            }
                          }}
                          className={`cursor-pointer transition focus:outline-none focus-visible:ring-2 focus-visible:ring-forest-600 ${
                            isSelected ? 'bg-forest-50/80 font-medium' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                            {s.batch_id}
                          </td>
                          <td className="py-2.5 px-3 text-slate-700">
                            {s.destination_id.replace('DEST-', '')}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">
                            {s.transport_id}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-slate-900 font-mono">
                            {s.allocated_qty_kg.toLocaleString('en-IN')} kg
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`inline-flex items-center gap-1 font-semibold ${
                                marginTight ? 'text-amber-600' : 'text-emerald-700'
                              }`}
                            >
                              <Clock className="h-3 w-3" />
                              {s.shelf_life_remaining_at_delivery_hours.toFixed(1)}h
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-emerald-700 font-bold">
                            ₹{s.net_contribution.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
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
                  {selectedShipment.batch_id} &rarr; {selectedShipment.destination_id.replace('DEST-', '')}
                </Badge>
              )}
            </div>

            {selectedShipment ? (
              <div className="space-y-3.5 text-xs">
                <div>
                  <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">
                    Why This Batch?
                  </span>
                  <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                    {selectedShipment.explanation?.why_this_batch ||
                      'Allocated based on earliest-expiry urgency and perishability constraints.'}
                  </p>
                </div>

                <div>
                  <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">
                    Why This Destination Mandi?
                  </span>
                  <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                    {selectedShipment.explanation?.why_this_destination ||
                      'Highest unfulfilled demand at attractive market price.'}
                  </p>
                </div>

                <div>
                  <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">
                    Why This Route & Vehicle?
                  </span>
                  <p className="mt-0.5 text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                    {selectedShipment.explanation?.why_this_route ||
                      'Optimal balance between transit speed and per-kg freight cost.'}
                  </p>
                </div>

                <div>
                  <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">
                    Economic Breakdown
                  </span>
                  <div className="mt-0.5 bg-slate-50 p-2.5 rounded-xl border border-slate-100 space-y-1 font-mono text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Gross Sales:</span>
                      <span className="font-bold text-slate-900">
                        ₹{selectedShipment.revenue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div className="flex justify-between text-rose-600">
                      <span>Freight Cost:</span>
                      <span>-₹{selectedShipment.transport_cost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-rose-600">
                      <span>Handling Cost:</span>
                      <span>-₹{selectedShipment.handling_cost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                    </div>
                    {selectedShipment.holding_cost > 0 && (
                      <div className="flex justify-between text-rose-600">
                        <span>Holding Cost:</span>
                        <span>-₹{selectedShipment.holding_cost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t border-slate-200 pt-1 text-emerald-700 font-bold">
                      <span>Net Contribution:</span>
                      <span>₹{selectedShipment.net_contribution.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">
                    Buffer Safety & Delay Sensitivity
                  </span>
                  <p className="mt-0.5 text-slate-600 leading-relaxed bg-amber-50/70 p-2.5 rounded-xl border border-amber-200/60 text-[11px]">
                    {selectedShipment.explanation?.what_makes_infeasible ||
                      `Requires ≥4.0h shelf-life buffer upon delivery. Buffer at arrival is ${selectedShipment.shelf_life_remaining_at_delivery_hours.toFixed(1)}h.`}
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
      )}

      {/* Dynamic Discount Recommendations Panel */}
      {!running && currentResult && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Tag className="h-5 w-5 text-amber-700" />
              <div>
                <h3 className="text-sm font-bold text-amber-950">
                  Dynamic Markdown & Discount Recommendations ({discountRecs.length} Batches Evaluated)
                </h3>
                <p className="text-xs text-amber-800">
                  Rule-based price markdown suggestions for at-risk unallocated inventory under 1.5× demand elasticity assumptions.
                </p>
              </div>
            </div>
            <Badge variant="warning" size="sm">
              Demand Response: 1.5×
            </Badge>
          </div>

          {discountRecs.length === 0 ? (
            <p className="text-xs text-amber-800 italic">
              All batches comfortably allocated or shelf-life values well within safety margins.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {discountRecs.map((rec) => (
                <div
                  key={rec.batch_id}
                  className="rounded-xl border border-amber-200 bg-white p-3.5 text-xs shadow-sm space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold font-mono text-slate-900">{rec.batch_id}</span>
                    <Badge
                      variant={rec.recommended_discount_pct > 0 ? 'success' : 'neutral'}
                      size="sm"
                    >
                      {rec.recommended_discount_pct > 0
                        ? `${rec.recommended_discount_pct}% Markdown`
                        : 'No Discount'}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-600 line-clamp-2">{rec.risk_reason}</p>
                  <div className="bg-slate-50 p-2 rounded-lg font-mono text-[11px] space-y-0.5">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Price:</span>
                      <span>
                        ₹{rec.original_price_inr} &rarr; ₹{rec.discounted_price_inr}/kg
                      </span>
                    </div>
                    <div className="flex justify-between text-emerald-700 font-semibold">
                      <span>Net Margin Impact:</span>
                      <span>+₹{rec.expected_net_contribution_change_inr}</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-tight">{rec.assumptions}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
