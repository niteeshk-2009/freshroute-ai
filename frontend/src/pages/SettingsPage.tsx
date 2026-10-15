import React, { useState } from 'react';
import {
  Settings,
  Download,
  UploadCloud,
  RotateCcw,
  Save,
  CheckCircle2,
  Database,
  Sliders,
  Shield,
  FileSpreadsheet,
} from 'lucide-react';
import { Scenario } from '../types';
import { getTemplateDownloadUrl, importInventoryCSV } from '../services/api';
import { Badge } from '../components/Badge';

interface SettingsPageProps {
  scenario: Scenario | null;
  onRefreshScenario: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ scenario, onRefreshScenario }) => {
  const [handlingCost, setHandlingCost] = useState(scenario?.cost_assumptions.handling_cost_per_kg || 1.5);
  const [holdingCost, setHoldingCost] = useState(scenario?.cost_assumptions.holding_cost_default_per_kg_hr || 0.08);
  const [spoilageMultiplier, setSpoilageMultiplier] = useState(scenario?.cost_assumptions.spoilage_penalty_multiplier || 1.0);
  const [allowNegative, setAllowNegative] = useState(scenario?.cost_assumptions.allow_negative_contribution || false);
  const [spoilageThreshold, setSpoilageThreshold] = useState(scenario?.cost_assumptions.spoilage_threshold_hours || 4.0);

  const [elasticity, setElasticity] = useState(scenario?.discount_config.elasticity_multiplier || 1.5);
  const [discountThreshold, setDiscountThreshold] = useState(scenario?.discount_config.shelf_life_threshold_hours || 36.0);

  const [saved, setSaved] = useState(false);

  const handleSaveAssumptions = () => {
    if (scenario) {
      scenario.cost_assumptions.handling_cost_per_kg = handlingCost;
      scenario.cost_assumptions.holding_cost_default_per_kg_hr = holdingCost;
      scenario.cost_assumptions.spoilage_penalty_multiplier = spoilageMultiplier;
      scenario.cost_assumptions.allow_negative_contribution = allowNegative;
      scenario.cost_assumptions.spoilage_threshold_hours = spoilageThreshold;

      scenario.discount_config.elasticity_multiplier = elasticity;
      scenario.discount_config.shelf_life_threshold_hours = discountThreshold;
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Settings className="h-6 w-6 text-forest-700" />
              Data & Economic Parameters
            </h2>
            <Badge variant="neutral" size="sm">System Configuration</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Configure financial cost parameters, discount elasticity models, and download seed data templates.
          </p>
        </div>

        <button
          onClick={handleSaveAssumptions}
          className="flex items-center gap-2 rounded-xl bg-forest-900 px-4 py-2 text-xs font-bold text-white shadow hover:bg-forest-800 transition active:scale-95"
        >
          <Save className="h-4 w-4 text-fresh-lime" />
          {saved ? 'Saved!' : 'Save Parameters'}
        </button>
      </div>

      {saved && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          Economic model assumptions saved successfully. Run the optimizer to see changes in allocations.
        </div>
      )}

      {/* Grid of Settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Economic Model Config */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Sliders className="h-4 w-4 text-forest-700" />
              Economic Cost Accounting (C8 & C9)
            </h3>
            <Badge variant="info" size="sm">INR (₹)</Badge>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Standard Handling Cost (₹ / kg)
              </label>
              <input
                type="number"
                step="0.1"
                value={handlingCost}
                onChange={(e) => setHandlingCost(parseFloat(e.target.value))}
                className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
              />
              <span className="text-[10px] text-slate-400">Loading/unloading labor at Nashik hub and target mandis.</span>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Default Holding / Cold Storage (₹ / kg-hour)
              </label>
              <input
                type="number"
                step="0.01"
                value={holdingCost}
                onChange={(e) => setHoldingCost(parseFloat(e.target.value))}
                className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
              />
              <span className="text-[10px] text-slate-400">Power and pre-cooling holding charge per kg-hour.</span>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Spoilage Penalty Multiplier
              </label>
              <input
                type="number"
                step="0.1"
                value={spoilageMultiplier}
                onChange={(e) => setSpoilageMultiplier(parseFloat(e.target.value))}
                className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
              />
              <span className="text-[10px] text-slate-400">Multiplier applied to batch disposal / write-off penalty.</span>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Shelf-Life Safety Buffer (Hours)
              </label>
              <input
                type="number"
                step="0.5"
                value={spoilageThreshold}
                onChange={(e) => setSpoilageThreshold(parseFloat(e.target.value))}
                className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
              />
              <span className="text-[10px] text-slate-400">Minimum remaining shelf life required upon unloading (C7).</span>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-800 block">Allow Negative Margin Shipments (C9)</span>
                <span className="text-[10px] text-slate-400">When disabled, shipments where costs exceed revenue are rejected.</span>
              </div>
              <input
                type="checkbox"
                checked={allowNegative}
                onChange={(e) => setAllowNegative(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-forest-700 accent-forest-700"
              />
            </div>
          </div>
        </div>

        {/* M4 Discount Engine Config & Templates */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Sliders className="h-4 w-4 text-forest-700" />
                M4 Discounting Engine Assumptions
              </h3>
              <Badge variant="warning" size="sm">Rule-Based</Badge>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Assumed Demand Elasticity Multiplier
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={elasticity}
                  onChange={(e) => setElasticity(parseFloat(e.target.value))}
                  className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
                />
                <span className="text-[10px] text-slate-400">
                  Formula: Additional Demand % = Discount % &times; {elasticity}x (Disclosed assumption).
                </span>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Urgency Threshold for Discounting (Hours)
                </label>
                <input
                  type="number"
                  step="1"
                  value={discountThreshold}
                  onChange={(e) => setDiscountThreshold(parseFloat(e.target.value))}
                  className="w-full rounded-xl border border-slate-200 p-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-forest-700"
                />
                <span className="text-[10px] text-slate-400">
                  Batches below this remaining shelf life are evaluated for markdown recommendations.
                </span>
              </div>
            </div>
          </div>

          {/* Downloadable Data Templates */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Download className="h-4 w-4 text-forest-700" />
              Download Standard CSV Templates
            </h3>
            <p className="text-xs text-slate-500">
              Download formatted templates to import custom datasets with validated C1-C10 schemas.
            </p>

            <div className="flex flex-wrap gap-2 pt-1">
              <a
                href={getTemplateDownloadUrl('inventory')}
                download
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-slate-400" />
                Inventory Batches (.csv)
              </a>
              <a
                href={getTemplateDownloadUrl('destinations')}
                download
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-slate-400" />
                Mandi Destinations (.csv)
              </a>
              <a
                href={getTemplateDownloadUrl('transports')}
                download
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-slate-400" />
                Transport Fleet (.csv)
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
