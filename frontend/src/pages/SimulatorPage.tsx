import React, { useState } from 'react';
import {
  Sliders,
  Play,
  RotateCcw,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  CheckCircle2,
  Clock,
  Truck,
  IndianRupee,
} from 'lucide-react';
import { Scenario, SimulationModifications, ComparisonResponse } from '../types';
import { runSimulation } from '../services/api';
import { Badge } from '../components/Badge';

interface SimulatorPageProps {
  scenario: Scenario | null;
}

export const SimulatorPage: React.FC<SimulatorPageProps> = ({ scenario }) => {
  const [demandMultiplier, setDemandMultiplier] = useState(1.0);
  const [delayHours, setDelayHours] = useState(0.0);
  const [capacityMultiplier, setCapacityMultiplier] = useState(1.0);
  const [priceMultiplier, setPriceMultiplier] = useState(1.0);
  const [disabledRouteId, setDisabledRouteId] = useState<string>('');

  const [simulating, setSimulating] = useState(false);
  const [simulationData, setSimulationData] = useState<{
    original_comparison: ComparisonResponse;
    modified_comparison: ComparisonResponse;
    affected_shipments: any[];
    changes_explanation: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunSimulation = async () => {
    if (!scenario) return;
    setSimulating(true);
    setError(null);

    const modifications: SimulationModifications = {};

    if (demandMultiplier !== 1.0) {
      modifications.demand_multipliers = {
        Tomatoes: demandMultiplier,
        Bananas: demandMultiplier,
        Mangoes: demandMultiplier,
        'Leafy Greens': demandMultiplier,
        Onions: demandMultiplier,
      };
    }

    if (priceMultiplier !== 1.0) {
      modifications.price_multipliers = {
        Tomatoes: priceMultiplier,
        Bananas: priceMultiplier,
        Mangoes: priceMultiplier,
        'Leafy Greens': priceMultiplier,
        Onions: priceMultiplier,
      };
    }

    if (delayHours > 0) {
      const delays: Record<string, number> = {};
      scenario.transport_options.forEach((t) => {
        delays[t.id] = delayHours;
      });
      modifications.transport_delays_hours = delays;
    }

    if (capacityMultiplier !== 1.0) {
      const caps: Record<string, number> = {};
      scenario.transport_options.forEach((t) => {
        caps[t.id] = capacityMultiplier;
      });
      modifications.capacity_multipliers = caps;
    }

    if (disabledRouteId) {
      modifications.transport_availability = { [disabledRouteId]: false };
    }

    try {
      const data = await runSimulation(scenario.id, modifications);
      setSimulationData(data);
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  const handleReset = () => {
    setDemandMultiplier(1.0);
    setDelayHours(0.0);
    setCapacityMultiplier(1.0);
    setPriceMultiplier(1.0);
    setDisabledRouteId('');
    setSimulationData(null);
  };

  const orig = simulationData?.original_comparison?.optimized;
  const mod = simulationData?.modified_comparison?.optimized;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="h-6 w-6 text-forest-700" />
              Disruption-Aware Scenario Simulator
            </h2>
            <Badge variant="warning" size="sm">Operational Re-planning</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Simulate highway delays, mandi demand shocks, fleet capacity squeezes, and route closures in real-time.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 active:scale-95 transition"
          >
            <RotateCcw className="h-4 w-4 text-slate-400" />
            Reset
          </button>
          <button
            onClick={handleRunSimulation}
            disabled={simulating || !scenario}
            className="flex items-center gap-2 rounded-xl bg-forest-900 px-5 py-2 text-xs font-bold text-white shadow hover:bg-forest-800 active:scale-95 transition disabled:opacity-50"
          >
            <Play className={`h-4 w-4 text-fresh-lime ${simulating ? 'animate-spin' : ''}`} />
            {simulating ? 'Re-planning...' : 'Apply Disruption & Re-plan'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-800">
          {error}
        </div>
      )}

      {/* Disruption Parameter Sliders */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Transit Delays */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-amber-500" />
              Highway Delays (+hrs)
            </span>
            <span className="font-mono font-bold text-forest-700">+{delayHours}h</span>
          </div>
          <input
            type="range"
            min="0"
            max="24"
            step="1"
            value={delayHours}
            onChange={(e) => setDelayHours(parseFloat(e.target.value))}
            className="w-full accent-forest-700"
          />
          <p className="text-[11px] text-slate-400">Adds transit time, evaluating shelf-life safety buffers upon arrival.</p>
        </div>

        {/* Mandi Demand Scale */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <Truck className="h-4 w-4 text-blue-500" />
              Demand Shock
            </span>
            <span className="font-mono font-bold text-forest-700">{(demandMultiplier * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.3"
            max="2.5"
            step="0.1"
            value={demandMultiplier}
            onChange={(e) => setDemandMultiplier(parseFloat(e.target.value))}
            className="w-full accent-forest-700"
          />
          <p className="text-[11px] text-slate-400">Scales APMC mandi demand across all commodities.</p>
        </div>

        {/* Transport Capacity */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-rose-500" />
              Fleet Capacity
            </span>
            <span className="font-mono font-bold text-forest-700">{(capacityMultiplier * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.2"
            max="1.5"
            step="0.1"
            value={capacityMultiplier}
            onChange={(e) => setCapacityMultiplier(parseFloat(e.target.value))}
            className="w-full accent-forest-700"
          />
          <p className="text-[11px] text-slate-400">Simulates vehicle breakdown or fuel shortage constraints.</p>
        </div>

        {/* Route Closure */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-purple-500" />
              Route Closure
            </span>
            {disabledRouteId && <Badge variant="danger" size="sm">Closed</Badge>}
          </div>
          <select
            value={disabledRouteId}
            onChange={(e) => setDisabledRouteId(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2 text-xs font-semibold text-slate-700 focus:outline-none"
          >
            <option value="">None (All Routes Operational)</option>
            {scenario?.transport_options.map((t) => (
              <option key={t.id} value={t.id}>
                {t.id} ({t.origin} &rarr; {t.destination_id.replace('DEST-', '')})
              </option>
            ))}
          </select>
          <p className="text-[11px] text-slate-400">Simulates roadblocks or weather closures to test rerouting feasibility.</p>
        </div>
      </div>

      {/* Disruption Impact Comparison Cards */}
      {simulationData && orig && mod && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-1">
              Replanning Explanation & Audit Rationale
            </h4>
            <p className="text-xs text-blue-800 leading-relaxed font-mono">
              {simulationData.changes_explanation}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Net Revenue Delta */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-slate-500">Net Revenue Impact</span>
              <div className="mt-2 flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-400">Before: ₹{orig.net_revenue.toLocaleString('en-IN')}</span>
                  <p className="text-xl font-extrabold text-slate-900">After: ₹{mod.net_revenue.toLocaleString('en-IN')}</p>
                </div>
                <Badge variant={mod.net_revenue >= orig.net_revenue ? 'success' : 'danger'}>
                  {mod.net_revenue >= orig.net_revenue ? '+' : ''}
                  ₹{(mod.net_revenue - orig.net_revenue).toLocaleString('en-IN')}
                </Badge>
              </div>
            </div>

            {/* Spoilage Delta */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-slate-500">Spoilage Rate Impact</span>
              <div className="mt-2 flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-400">Before: {orig.spoilage_rate_pct}%</span>
                  <p className="text-xl font-extrabold text-slate-900">After: {mod.spoilage_rate_pct}%</p>
                </div>
                <Badge variant={mod.spoilage_rate_pct <= orig.spoilage_rate_pct ? 'success' : 'danger'}>
                  {(mod.spoilage_rate_pct - orig.spoilage_rate_pct).toFixed(1)}% pts
                </Badge>
              </div>
            </div>

            {/* Demand Fulfillment Delta */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="text-xs font-semibold text-slate-500">Demand Fulfillment</span>
              <div className="mt-2 flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-400">Before: {orig.fulfillment_pct}%</span>
                  <p className="text-xl font-extrabold text-slate-900">After: {mod.fulfillment_pct}%</p>
                </div>
                <Badge variant={mod.fulfillment_pct >= orig.fulfillment_pct ? 'success' : 'warning'}>
                  {(mod.fulfillment_pct - orig.fulfillment_pct).toFixed(1)}% pts
                </Badge>
              </div>
            </div>
          </div>

          {/* Affected Shipments Table */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800">
                Affected Shipments ({(simulationData.affected_shipments || []).length} Modifications Detected)
              </h3>
              <Badge variant="info" size="sm">Dynamic Reallocation</Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 bg-slate-50/80">
                    <th className="py-2.5 px-4 font-semibold">Batch</th>
                    <th className="py-2.5 px-4 font-semibold">Destination</th>
                    <th className="py-2.5 px-4 font-semibold">Original Qty</th>
                    <th className="py-2.5 px-4 font-semibold">Simulated Qty</th>
                    <th className="py-2.5 px-4 font-semibold">Delta</th>
                    <th className="py-2.5 px-4 font-semibold">Status / Change Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(simulationData.affected_shipments || []).map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition">
                      <td className="py-2.5 px-4 font-mono font-bold text-slate-900">{item.batch_id}</td>
                      <td className="py-2.5 px-4 text-slate-700">{item.destination_id}</td>
                      <td className="py-2.5 px-4 font-mono text-slate-500">{item.original_qty_kg} kg</td>
                      <td className="py-2.5 px-4 font-mono font-bold text-slate-900">{item.simulated_qty_kg} kg</td>
                      <td className="py-2.5 px-4 font-mono font-bold">
                        <span className={item.delta_kg < 0 ? 'text-rose-600' : 'text-emerald-600'}>
                          {item.delta_kg > 0 ? '+' : ''}{item.delta_kg} kg
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-600">{item.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
