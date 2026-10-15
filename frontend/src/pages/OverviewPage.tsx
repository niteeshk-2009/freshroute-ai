import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Percent,
  IndianRupee,
  Package,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  Sparkles,
  BarChart2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Scenario, ComparisonResponse, ScenarioSummary } from '../types';
import { runEvaluation } from '../services/api';
import { Badge } from '../components/Badge';

interface OverviewPageProps {
  currentScenario: Scenario | null;
  scenarios: ScenarioSummary[];
  onSelectScenario: (id: string) => void;
  onNavigate: (page: any) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  currentScenario,
  scenarios,
  onSelectScenario,
  onNavigate,
}) => {
  const [evalData, setEvalData] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (currentScenario?.id) {
      loadEvaluation(currentScenario.id);
    }
  }, [currentScenario?.id]);

  const loadEvaluation = async (scenarioId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await runEvaluation(scenarioId);
      setEvalData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  };

  const baseline = evalData?.baseline;
  const optimized = evalData?.optimized;
  const summary = evalData?.summary;

  // Comparison metrics bar chart data
  const comparisonChartData = [
    {
      name: 'Spoilage Rate (%)',
      Baseline: baseline?.spoilage_rate_pct ?? 0,
      Optimized: optimized?.spoilage_rate_pct ?? 0,
    },
    {
      name: 'Demand Fulfillment (%)',
      Baseline: baseline?.fulfillment_pct ?? 0,
      Optimized: optimized?.fulfillment_pct ?? 0,
    },
    {
      name: 'Inventory Utilized (%)',
      Baseline: baseline?.inventory_utilization_pct ?? 0,
      Optimized: optimized?.inventory_utilization_pct ?? 0,
    },
  ];

  // Financial chart data (in ₹ Thousands for chart readability)
  const financialChartData = [
    {
      name: 'Gross Sales',
      Baseline: ((baseline?.total_revenue ?? 0) / 1000),
      Optimized: ((optimized?.total_revenue ?? 0) / 1000),
    },
    {
      name: 'Transport Cost',
      Baseline: ((baseline?.total_transport_cost ?? 0) / 1000),
      Optimized: ((optimized?.total_transport_cost ?? 0) / 1000),
    },
    {
      name: 'Spoilage Loss',
      Baseline: ((baseline?.total_spoilage_cost ?? 0) / 1000),
      Optimized: ((optimized?.total_spoilage_cost ?? 0) / 1000),
    },
    {
      name: 'Net Profit',
      Baseline: ((baseline?.net_revenue ?? 0) / 1000),
      Optimized: ((optimized?.net_revenue ?? 0) / 1000),
    },
  ];

  // Perishability buckets
  const shelfLifeBuckets = [
    { name: 'Critical (<24h)', count: 0, color: '#EF4444' },
    { name: 'Urgent (24-48h)', count: 0, color: '#F59E0B' },
    { name: 'Moderate (48-96h)', count: 0, color: '#3B82F6' },
    { name: 'Stable (>96h)', count: 0, color: '#10B981' },
  ];

  currentScenario?.inventory_batches.forEach((b) => {
    if (b.remaining_shelf_life_hours < 24) shelfLifeBuckets[0].count += b.quantity_kg;
    else if (b.remaining_shelf_life_hours <= 48) shelfLifeBuckets[1].count += b.quantity_kg;
    else if (b.remaining_shelf_life_hours <= 96) shelfLifeBuckets[2].count += b.quantity_kg;
    else shelfLifeBuckets[3].count += b.quantity_kg;
  });

  const totalInventoryKg = currentScenario?.inventory_batches.reduce((sum, b) => sum + b.quantity_kg, 0) || 0;
  const criticalBatchesCount = currentScenario?.inventory_batches.filter(b => b.remaining_shelf_life_hours < 36).length || 0;

  return (
    <div className="space-y-6">
      {/* Top Banner & Scenario Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl bg-gradient-to-r from-forest-900 via-forest-800 to-forest-900 p-6 text-white shadow-md">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-fresh-lime">
              FreshRoute Operations Intelligence
            </span>
            <span className="h-1.5 w-1.5 rounded-full bg-fresh-lime" />
            <span className="text-xs text-forest-200">Intelligent Dispatch Engine</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight">Executive Operations Dashboard</h2>
          <p className="mt-1 text-xs text-forest-100 max-w-2xl leading-relaxed">
            Real-time trade-off optimization between remaining shelf-life, mandi demand, freight costs, and spoilage risk.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs text-forest-200 font-medium">Scenario:</label>
          <select
            value={currentScenario?.id || ''}
            onChange={(e) => onSelectScenario(e.target.value)}
            className="rounded-xl border border-forest-700 bg-forest-950/80 px-3.5 py-2 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-fresh-lime"
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Net Revenue */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Net Profit (After All Costs)</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
              <IndianRupee className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            ₹{optimized?.net_revenue.toLocaleString('en-IN') ?? '0'}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-slate-500">EEF Baseline: ₹{baseline?.net_revenue.toLocaleString('en-IN') ?? '0'}</span>
            {evalData?.comparison?.net_revenue && (
              <span className={`inline-flex items-center font-bold ${evalData.comparison.net_revenue.absolute_difference >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {evalData.comparison.net_revenue.absolute_difference >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                ₹{Math.abs(evalData.comparison.net_revenue.absolute_difference).toLocaleString('en-IN')}
              </span>
            )}
          </div>
        </div>

        {/* Spoilage Rate */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Estimated Spoilage Rate</span>
            <div className="rounded-lg bg-rose-50 p-2 text-rose-700">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            {optimized?.spoilage_rate_pct ?? 0}%
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-slate-500">Baseline: {baseline?.spoilage_rate_pct ?? 0}%</span>
            {evalData?.comparison?.spoilage_rate_pct && (
              <span className={`inline-flex items-center font-bold ${evalData.comparison.spoilage_rate_pct.absolute_difference <= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {evalData.comparison.spoilage_rate_pct.absolute_difference <= 0 ? <ArrowDownRight className="h-3.5 w-3.5" /> : <ArrowUpRight className="h-3.5 w-3.5" />}
                {Math.abs(evalData.comparison.spoilage_rate_pct.absolute_difference)}% pts
              </span>
            )}
          </div>
        </div>

        {/* Demand Fulfillment */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Demand Fulfillment</span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
              <Percent className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            {optimized?.fulfillment_pct ?? 0}%
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-slate-500">
              {optimized?.demand_fulfilled_qty_kg.toLocaleString('en-IN') ?? 0} / {optimized?.total_demand_kg.toLocaleString('en-IN') ?? 0} kg
            </span>
            <span className="font-semibold text-emerald-600">
              {baseline ? `+${(optimized?.fulfillment_pct! - baseline.fulfillment_pct).toFixed(1)}%` : ''}
            </span>
          </div>
        </div>

        {/* Inventory In-Warehouse */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Total Inventory</span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-700">
              <Package className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            {totalInventoryKg.toLocaleString('en-IN')} kg
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-rose-600 font-semibold flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {criticalBatchesCount} batches &lt;36h shelf life
            </span>
            <span className="text-slate-500">
              {currentScenario?.destinations.length || 0} Mandis
            </span>
          </div>
        </div>
      </div>

      {/* Strategy Comparison Summary Banner */}
      {summary && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-emerald-600 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900">
                  Algorithmic Verdict: {summary.verdict.replace(/_/g, ' ')}
                </h4>
                <Badge variant="success" size="sm">
                  {summary.improvements_count} Metrics Improved
                </Badge>
              </div>
              <p className="mt-0.5 text-xs text-emerald-800 leading-relaxed">
                {summary.narrative || summary.description}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => onNavigate('planner')}
              className="rounded-xl bg-forest-900 px-4 py-2 text-xs font-bold text-white hover:bg-forest-800 transition"
            >
              Open Distribution Planner
            </button>
            <button
              onClick={() => onNavigate('evaluation')}
              className="rounded-xl border border-emerald-300 bg-white px-3.5 py-2 text-xs font-semibold text-emerald-900 hover:bg-emerald-50 transition"
            >
              Full Evaluation Audit
            </button>
          </div>
        </div>
      )}

      {/* Dual Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Operations Performance Chart */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Fulfillment & Spoilage Metrics</h3>
              <p className="text-xs text-slate-500">Comparison of key efficiency ratios (%)</p>
            </div>
            <Badge variant="neutral" size="sm">Baseline vs Optimizer</Badge>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis unit="%" tick={{ fontSize: 11 }} domain={[0, 100]} />
                <Tooltip
                  formatter={(val: number) => [`${val.toFixed(1)}%`, '']}
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', border: '1px solid #E2E8F0', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Baseline" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Optimized" fill="#15803D" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Financial Flow Breakdown (₹ Thousands) */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Economic Breakdown (₹ in Thousands)</h3>
              <p className="text-xs text-slate-500">Gross revenue, transport costs, and net profit</p>
            </div>
            <Badge variant="info" size="sm">Unit Economics Accounting</Badge>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={financialChartData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis unit="k" tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val: number) => [`₹${(val * 1000).toLocaleString('en-IN')}`, '']}
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', border: '1px solid #E2E8F0', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Baseline" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Optimized" fill="#16A34A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Inventory Perishability Distribution & Mandi Demand Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shelf Life Distribution Pie */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">Inventory Perishability Distribution</h3>
            <p className="text-xs text-slate-500">Produce volume by remaining shelf life hours</p>
          </div>
          <div className="h-48 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={shelfLifeBuckets}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="count"
                >
                  {shelfLifeBuckets.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: number) => [`${val.toLocaleString('en-IN')} kg`, 'Weight']}
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2 mt-2">
            {shelfLifeBuckets.map((b) => (
              <div key={b.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: b.color }} />
                  <span className="text-slate-600">{b.name}</span>
                </div>
                <span className="font-semibold text-slate-900">{b.count.toLocaleString('en-IN')} kg</span>
              </div>
            ))}
          </div>
        </div>

        {/* Mandi Destinations Summary */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Destination APMC Mandi Capacity & Demand</h3>
              <p className="text-xs text-slate-500">Nashik hub distribution target markets</p>
            </div>
            <button
              onClick={() => onNavigate('planner')}
              className="text-xs font-bold text-forest-700 hover:text-forest-900 flex items-center gap-1"
            >
              View Route Plan &rarr;
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-2.5 font-semibold">Mandi / Destination</th>
                  <th className="pb-2.5 font-semibold">Priority</th>
                  <th className="pb-2.5 font-semibold">Total Demand</th>
                  <th className="pb-2.5 font-semibold">Intake Capacity</th>
                  <th className="pb-2.5 font-semibold">Delivery Window</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentScenario?.destinations.map((d) => {
                  const destTotalDemand = Object.values(d.demand).reduce((a, b) => a + b, 0);
                  return (
                    <tr key={d.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-2.5 font-semibold text-slate-900">{d.name}</td>
                      <td className="py-2.5">
                        <Badge variant={d.priority === 1 ? 'danger' : d.priority === 2 ? 'warning' : 'neutral'} size="sm">
                          P{d.priority}
                        </Badge>
                      </td>
                      <td className="py-2.5 font-mono text-slate-700">{destTotalDemand.toLocaleString('en-IN')} kg</td>
                      <td className="py-2.5 font-mono text-slate-500">{d.receiving_capacity_kg.toLocaleString('en-IN')} kg</td>
                      <td className="py-2.5 text-slate-600">{d.demand_window_hours}h</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
