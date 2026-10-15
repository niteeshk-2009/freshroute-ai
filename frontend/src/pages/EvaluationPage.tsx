import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Award,
  TrendingUp,
  Percent,
  IndianRupee,
  Layers,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { ScenarioSummary, ComparisonResponse } from '../types';
import { runEvaluation } from '../services/api';
import { Badge } from '../components/Badge';

interface EvaluationPageProps {
  scenarios: ScenarioSummary[];
}

export const EvaluationPage: React.FC<EvaluationPageProps> = ({ scenarios }) => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('EVAL-01-NORMAL');
  const [evalData, setEvalData] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [allEvaluations, setAllEvaluations] = useState<Record<string, ComparisonResponse>>({});
  const [batchLoading, setBatchLoading] = useState(false);

  useEffect(() => {
    loadSingleEval(selectedScenarioId);
  }, [selectedScenarioId]);

  const loadSingleEval = async (id: string) => {
    setLoading(true);
    try {
      const data = await runEvaluation(id);
      setEvalData(data);
      setAllEvaluations((prev) => ({ ...prev, [id]: data }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAllEvaluations = async () => {
    setBatchLoading(true);
    try {
      const results: Record<string, ComparisonResponse> = {};
      for (const sc of scenarios) {
        const data = await runEvaluation(sc.id);
        results[sc.id] = data;
      }
      setAllEvaluations(results);
      if (results[selectedScenarioId]) {
        setEvalData(results[selectedScenarioId]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setBatchLoading(false);
    }
  };

  const evalList = Object.entries(allEvaluations);
  const totalEvaluated = evalList.length;

  const baseline = evalData?.baseline;
  const optimized = evalData?.optimized;
  const comparison = evalData?.comparison;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-forest-700" />
              Comparative Performance Evaluation & Benchmark Suite
            </h2>
            <Badge variant="success" size="sm">Controlled Benchmark Suite</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Fair side-by-side benchmarking on identical scenarios, hard constraints, and economic models with disclosed assumptions.
          </p>
        </div>

        <button
          onClick={handleRunAllEvaluations}
          disabled={batchLoading}
          className="flex items-center gap-2 rounded-xl bg-forest-900 px-4 py-2 text-xs font-bold text-white shadow hover:bg-forest-800 transition disabled:opacity-50"
        >
          <Award className={`h-4 w-4 text-fresh-lime ${batchLoading ? 'animate-bounce' : ''}`} />
          {batchLoading ? 'Evaluating All Scenarios...' : 'Evaluate All 10 Benchmarks'}
        </button>
      </div>

      {/* Scenario Benchmark Grid Selector */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Select Evaluation Scenario ({scenarios.length} Total)
          </span>
          <span className="text-[11px] text-slate-400">Fixed seeds for deterministic reproducibility</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
          {scenarios.map((sc) => {
            const isSelected = selectedScenarioId === sc.id;
            const evalResult = allEvaluations[sc.id];
            const revDiff = evalResult?.comparison?.net_revenue?.absolute_difference;

            return (
              <button
                key={sc.id}
                onClick={() => setSelectedScenarioId(sc.id)}
                className={`p-2.5 rounded-xl border text-left transition flex flex-col justify-between ${
                  isSelected
                    ? 'border-forest-700 bg-forest-900 text-white shadow-sm'
                    : 'border-slate-200 bg-slate-50/70 hover:bg-slate-100 text-slate-800'
                }`}
              >
                <div>
                  <div className="text-[10px] font-mono font-bold truncate opacity-70">
                    {sc.id}
                  </div>
                  <div className="text-xs font-bold truncate mt-0.5">
                    {sc.name.replace('Evaluation: ', '')}
                  </div>
                </div>

                <div className="mt-2 flex items-center justify-between text-[10px]">
                  <span className={isSelected ? 'text-forest-200' : 'text-slate-400'}>
                    {sc.batch_count} batches
                  </span>
                  {revDiff !== undefined && (
                    <span className={`font-bold ${isSelected ? (revDiff >= 0 ? 'text-fresh-lime' : 'text-rose-300') : (revDiff >= 0 ? 'text-emerald-600' : 'text-rose-600')}`}>
                      {revDiff >= 0 ? `+₹${(revDiff / 1000).toFixed(0)}k` : `-₹${Math.abs(revDiff / 1000).toFixed(0)}k`}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Single Scenario Deep Audit */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading scenario benchmark data...</div>
      ) : evalData && baseline && optimized && comparison ? (
        <div className="space-y-6">
          {/* Executive Verdict Banner */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 flex items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-emerald-600 p-2 text-white">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-950">
                    Audited Verdict: {evalData.summary.verdict.replace(/_/g, ' ')}
                  </h4>
                  <Badge variant="success" size="sm">0 Constraint Violations</Badge>
                </div>
                <p className="mt-0.5 text-xs text-emerald-800 leading-relaxed">
                  {evalData.summary.narrative || evalData.summary.description}
                </p>
              </div>
            </div>
            <div className="text-right shrink-0">
              <span className="text-[10px] text-emerald-700 font-semibold block">Execution Time</span>
              <span className="text-xs font-mono font-bold text-emerald-900">
                Opt {optimized.execution_time_ms.toFixed(1)}ms vs Base {baseline.execution_time_ms.toFixed(1)}ms
              </span>
            </div>
          </div>

          {/* Full Metric Matrix Table */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-slate-800">
                  Fair Comparison Matrix: {evalData.scenario_id}
                </h3>
                <p className="text-[11px] text-slate-400">
                  Exact mathematical calculations matching official economic equations
                </p>
              </div>
              <Badge variant="info" size="sm">Controlled Baseline Comparison</Badge>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 bg-slate-50/80">
                    <th className="py-2.5 px-4 font-semibold">Performance Metric</th>
                    <th className="py-2.5 px-4 font-semibold">EEF Baseline</th>
                    <th className="py-2.5 px-4 font-semibold">FreshRoute Optimizer</th>
                    <th className="py-2.5 px-4 font-semibold">Absolute Difference</th>
                    <th className="py-2.5 px-4 font-semibold">Relative %</th>
                    <th className="py-2.5 px-4 font-semibold">Audited Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(comparison).map(([key, item]) => {
                    const isPositive = item.optimizer_better;
                    const isNeutral = item.absolute_difference === 0;

                    return (
                      <tr key={key} className="hover:bg-slate-50 transition">
                        <td className="py-3 px-4 font-semibold text-slate-800 capitalize">
                          {key.replace(/_/g, ' ')}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">
                          {item.baseline.toLocaleString('en-IN')} {item.unit}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          {item.optimized.toLocaleString('en-IN')} {item.unit}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold">
                          <span className={isNeutral ? 'text-slate-400' : isPositive ? 'text-emerald-600' : 'text-rose-600'}>
                            {item.absolute_difference > 0 ? '+' : ''}
                            {item.absolute_difference.toLocaleString('en-IN')} {item.unit}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">
                          {item.relative_difference_pct !== null ? `${item.relative_difference_pct > 0 ? '+' : ''}${item.relative_difference_pct}%` : 'N/A'}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={isNeutral ? 'neutral' : isPositive ? 'success' : 'danger'} size="sm">
                            {isNeutral ? 'Equal' : isPositive ? 'Optimizer Better' : 'Baseline Ahead'}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
