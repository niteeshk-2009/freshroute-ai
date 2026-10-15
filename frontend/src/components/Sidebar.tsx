import React from 'react';
import {
  LayoutDashboard,
  Boxes,
  Truck,
  Sliders,
  BarChart3,
  FileText,
  Settings,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';

export type PageId =
  | 'overview'
  | 'inventory'
  | 'planner'
  | 'simulator'
  | 'evaluation'
  | 'reports'
  | 'settings';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  scenarioCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  scenarioCount = 11,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'inventory', label: 'Inventory', icon: Boxes },
    { id: 'planner', label: 'Distribution Planner', icon: Truck },
    { id: 'simulator', label: 'Scenario Simulator', icon: Sliders },
    { id: 'evaluation', label: 'Performance Evaluation', icon: BarChart3 },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'settings', label: 'Data & Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col justify-between py-5 min-h-[calc(100vh-4rem)]">
      <div>
        <div className="px-4 mb-2">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Operations Platform
          </p>
        </div>

        <nav className="space-y-1 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectPage(item.id as PageId)}
                className={`w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-forest-900 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-fresh-lime' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.id === 'simulator' && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${isActive ? 'bg-forest-800 text-fresh-lime' : 'bg-slate-100 text-slate-600'}`}>
                    What-If
                  </span>
                )}
                {item.id === 'evaluation' && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${isActive ? 'bg-forest-800 text-fresh-lime' : 'bg-emerald-50 text-emerald-700'}`}>
                    10 Scenarios
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="px-4 space-y-4">
        <div className="rounded-xl border border-forest-100 bg-forest-50/60 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-forest-900 mb-1">
            <span>Optimization Engine</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <p className="text-[11px] text-forest-700 leading-relaxed">
            Constraint-aware heuristics allocating Nashik hub produce across 6 wholesale APMC mandis.
          </p>
          <div className="mt-2 text-[10px] text-forest-600 font-mono bg-white/70 rounded p-1.5 border border-forest-100">
            C1-C10 Hard Constraints Enforced
          </div>
        </div>

        <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
          <span>Official PS-07 Solution</span>
          <span className="font-mono text-[10px]">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
