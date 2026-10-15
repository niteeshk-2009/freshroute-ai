import React from 'react';
import { Leaf, ShieldCheck, RefreshCw, Cpu, Activity } from 'lucide-react';
import { Badge } from './Badge';

interface NavbarProps {
  currentScenarioName: string;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentScenarioName,
  onRefresh,
  isLoading = false,
}) => {
  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-forest-900 text-fresh-lime shadow-sm">
          <Leaf className="h-5 w-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-slate-900">
              FreshRoute <span className="text-forest-700">AI</span>
            </h1>
            <Badge variant="success" size="sm">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Enterprise Edition
            </Badge>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            Intelligent Decision Support for Perishable Produce Distribution
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700">
          <Activity className="h-3.5 w-3.5 text-forest-700" />
          <span className="font-medium text-slate-500">Active Scenario:</span>
          <span className="font-semibold text-slate-900 truncate max-w-[200px]">
            {currentScenarioName || 'Default Nashik Demo'}
          </span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 active:scale-95 transition"
            title="Refresh scenario state"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-forest-700' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        )}

        <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span className="hidden md:inline">Feasibility Checks Active</span>
        </div>
      </div>
    </header>
  );
};
