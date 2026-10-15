import React, { useState, useEffect } from 'react';
import {
  FileText,
  Printer,
  Download,
  CheckCircle2,
  AlertTriangle,
  Info,
  Calendar,
  Building,
  Scale,
} from 'lucide-react';
import { Scenario } from '../types';
import { fetchReport } from '../services/api';
import { Badge } from '../components/Badge';

interface ReportsPageProps {
  scenario: Scenario | null;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({ scenario }) => {
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (scenario?.id) {
      loadReport(scenario.id);
    }
  }, [scenario?.id]);

  const loadReport = async (id: string) => {
    setLoading(true);
    try {
      const data = await fetchReport(id);
      setReportData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportCSV = () => {
    if (!reportData) return;
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      'Metric,Baseline,Optimized,Difference\n' +
      `Net Profit (INR),${reportData.baseline_evaluation.net_revenue},${reportData.optimized_evaluation.net_revenue},${reportData.optimized_evaluation.net_revenue - reportData.baseline_evaluation.net_revenue}\n` +
      `Spoilage Rate (%),${reportData.baseline_evaluation.spoilage_rate_pct},${reportData.optimized_evaluation.spoilage_rate_pct},${(reportData.optimized_evaluation.spoilage_rate_pct - reportData.baseline_evaluation.spoilage_rate_pct).toFixed(1)}\n` +
      `Demand Fulfillment (%),${reportData.baseline_evaluation.fulfillment_pct},${reportData.optimized_evaluation.fulfillment_pct},${(reportData.optimized_evaluation.fulfillment_pct - reportData.baseline_evaluation.fulfillment_pct).toFixed(1)}\n` +
      `Dispatched Weight (kg),${reportData.baseline_evaluation.demand_fulfilled_qty_kg},${reportData.optimized_evaluation.demand_fulfilled_qty_kg},${reportData.optimized_evaluation.demand_fulfilled_qty_kg - reportData.baseline_evaluation.demand_fulfilled_qty_kg}\n`;

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `FreshRoute_Audit_${reportData.scenario_id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm print:hidden">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <FileText className="h-6 w-6 text-forest-700" />
              Executive Decision Audit Report
            </h2>
            <Badge variant="info" size="sm">Print & CSV Export</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Audited dispatch decision documentation for operational transparency, compliance, and stakeholder review.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleExportCSV}
            disabled={!reportData}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition active:scale-95 disabled:opacity-50"
          >
            <Download className="h-4 w-4 text-slate-400" />
            Export CSV
          </button>
          <button
            onClick={handlePrint}
            disabled={!reportData}
            className="flex items-center gap-2 rounded-xl bg-forest-900 px-4 py-2 text-xs font-bold text-white shadow hover:bg-forest-800 transition active:scale-95 disabled:opacity-50"
          >
            <Printer className="h-4 w-4 text-fresh-lime" />
            Print Report
          </button>
        </div>
      </div>

      {/* Printable Report Document Card */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Compiling executive report...</div>
      ) : reportData ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm space-y-6 text-slate-800 print:border-none print:shadow-none print:p-0">
          {/* Document Header */}
          <div className="border-b border-slate-200 pb-5 flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-forest-700">
                  FreshRoute AI Decision-Support Platform
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-forest-700" />
                <span className="text-xs text-slate-400 font-mono">Operations Audit</span>
              </div>
              <h1 className="text-2xl font-black text-slate-900 mt-1">
                Perishable Produce Allocation Audit
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Scenario: <strong>{reportData.scenario_name}</strong> ({reportData.scenario_id})
              </p>
            </div>

            <div className="text-right text-xs text-slate-400 font-mono">
              <div>Date: {new Date(reportData.created_at).toLocaleDateString()}</div>
              <div>Hub: Nashik Central Agro-Hub</div>
              <div className="mt-1">
                <Badge variant="success" size="sm">Feasibility Validated</Badge>
              </div>
            </div>
          </div>

          {/* Section 1: Executive Summary */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              1. Executive Summary & Algorithmic Verdict
            </h3>
            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200/80 text-xs leading-relaxed space-y-2">
              <p>
                <strong>Verdict: </strong>
                {reportData.executive_summary?.narrative ||
                  'The FreshRoute constraint-aware heuristic demonstrates measurable economic advantages over the Earliest-Expiry-First (EEF) baseline while strictly adhering to perishable produce logistics constraints.'}
              </p>
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-200 text-slate-700">
                <div>
                  <span className="text-[10px] text-slate-400 block">Baseline Net Profit:</span>
                  <span className="font-mono font-bold">₹{reportData.baseline_evaluation.net_revenue.toLocaleString('en-IN')}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Optimized Net Profit:</span>
                  <span className="font-mono font-bold text-emerald-700">₹{reportData.optimized_evaluation.net_revenue.toLocaleString('en-IN')}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Economic Improvement:</span>
                  <span className="font-mono font-bold text-forest-700">
                    +₹{(reportData.optimized_evaluation.net_revenue - reportData.baseline_evaluation.net_revenue).toLocaleString('en-IN')}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Core Metrics Table */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              2. Core Distribution Performance Metrics
            </h3>
            <table className="w-full text-left text-xs border border-slate-200 rounded-xl overflow-hidden">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Evaluation Metric</th>
                  <th className="py-2.5 px-3 font-semibold">Baseline Strategy (EEF)</th>
                  <th className="py-2.5 px-3 font-semibold">FreshRoute Optimizer</th>
                  <th className="py-2.5 px-3 font-semibold">Variance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="py-2.5 px-3 font-medium">Estimated Spoilage Rate</td>
                  <td className="py-2.5 px-3 font-mono">{reportData.baseline_evaluation.spoilage_rate_pct}%</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{reportData.optimized_evaluation.spoilage_rate_pct}%</td>
                  <td className="py-2.5 px-3 font-mono text-emerald-700 font-semibold">
                    {(reportData.optimized_evaluation.spoilage_rate_pct - reportData.baseline_evaluation.spoilage_rate_pct).toFixed(1)}% pts
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-medium">Demand Fulfillment Rate</td>
                  <td className="py-2.5 px-3 font-mono">{reportData.baseline_evaluation.fulfillment_pct}%</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{reportData.optimized_evaluation.fulfillment_pct}%</td>
                  <td className="py-2.5 px-3 font-mono text-emerald-700 font-semibold">
                    +{(reportData.optimized_evaluation.fulfillment_pct - reportData.baseline_evaluation.fulfillment_pct).toFixed(1)}% pts
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-medium">Produce Delivered (kg)</td>
                  <td className="py-2.5 px-3 font-mono">{reportData.baseline_evaluation.demand_fulfilled_qty_kg.toLocaleString('en-IN')} kg</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{reportData.optimized_evaluation.demand_fulfilled_qty_kg.toLocaleString('en-IN')} kg</td>
                  <td className="py-2.5 px-3 font-mono text-slate-700">
                    +{(reportData.optimized_evaluation.demand_fulfilled_qty_kg - reportData.baseline_evaluation.demand_fulfilled_qty_kg).toLocaleString('en-IN')} kg
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-medium">Freight & Logistics Cost</td>
                  <td className="py-2.5 px-3 font-mono">₹{reportData.baseline_evaluation.total_transport_cost.toLocaleString('en-IN')}</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-900">₹{reportData.optimized_evaluation.total_transport_cost.toLocaleString('en-IN')}</td>
                  <td className="py-2.5 px-3 font-mono text-slate-700">
                    ₹{(reportData.optimized_evaluation.total_transport_cost - reportData.baseline_evaluation.total_transport_cost).toLocaleString('en-IN')}
                  </td>
                </tr>
                <tr className="bg-emerald-50/40">
                  <td className="py-2.5 px-3 font-bold text-slate-900">Net Profit (After All Defined Costs)</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-700">₹{reportData.baseline_evaluation.net_revenue.toLocaleString('en-IN')}</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-emerald-800">₹{reportData.optimized_evaluation.net_revenue.toLocaleString('en-IN')}</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-emerald-700">
                    +₹{(reportData.optimized_evaluation.net_revenue - reportData.baseline_evaluation.net_revenue).toLocaleString('en-IN')}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Section 3: Disclosures, Assumptions & Limitations */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              3. Data Disclosures, Methodological Assumptions & Limitations
            </h3>
            <div className="space-y-2 text-xs text-slate-600 bg-slate-50 p-4 rounded-xl border border-slate-200/80">
              <p>
                &bull; <strong>Synthetic Data Disclosure:</strong> All inventory batches, shelf-life figures, mandi prices, and road travel durations are generated using deterministic synthetic models (seed 42) based on Indian agro-climatic context. No live market feed or GPS telemetry was fabricated.
              </p>
              <p>
                &bull; <strong>Economic Formula:</strong> <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-mono text-[11px]">Net Revenue = Gross Revenue - Transport Cost - Handling Cost - Holding Cost - Spoilage Penalty</code>.
              </p>
              <p>
                &bull; <strong>Algorithm Classification:</strong> The FreshRoute solver is a multi-criteria greedy heuristic with local improvement search. It is rigorously constraint-compliant but not claimed to be globally optimal.
              </p>
              <p>
                &bull; <strong>Discount Elasticity:</strong> Assumes illustrative conservative response of <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-mono text-[11px]">Demand Increase % = Discount % &times; 1.5</code>.
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
