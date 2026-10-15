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
  const sections = [
    {
      title: 'OPERATIONS',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'inventory', label: 'Inventory', icon: Boxes },
        { id: 'planner', label: 'Distribution Planner', icon: Truck },
        { id: 'simulator', label: 'Scenario Simulator', icon: Sliders, badge: 'What-If' },
      ],
    },
    {
      title: 'INSIGHTS',
      items: [
        { id: 'evaluation', label: 'Performance Evaluation', icon: BarChart3, badge: '10 Benchmarks' },
        { id: 'reports', label: 'Reports', icon: FileText },
      ],
    },
    {
      title: 'CONFIGURATION',
      items: [
        { id: 'settings', label: 'Data & Settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col justify-between py-5 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        {sections.map((section) => (
          <div key={section.title}>
            <div className="px-4 mb-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {section.title}
              </p>
            </div>

            <nav className="space-y-1 px-3">
              {section.items.map((item) => {
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
                    {item.badge && (
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          isActive
                            ? 'bg-forest-800 text-fresh-lime'
                            : 'bg-emerald-50 text-emerald-700'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      <div className="px-4 space-y-4 pt-4 border-t border-slate-100">
        <div className="rounded-xl border border-forest-100 bg-forest-50/60 p-3.5">
          <div className="flex items-center justify-between text-xs font-bold text-forest-900 mb-1">
            <span>Optimization Engine</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <p className="text-[11px] text-forest-700 leading-relaxed">
            Constraint-aware dispatch heuristics allocating Nashik hub stock across 6 wholesale APMC mandis.
          </p>
          <div className="mt-2 text-[10px] text-forest-700 font-medium bg-white/80 rounded p-1.5 border border-forest-100/80">
            All 10 Feasibility Rules Enforced
          </div>
        </div>

        <div className="text-[11px] text-slate-400 flex items-center justify-between px-1">
          <span>Nashik Hub Network</span>
          <span className="font-mono text-[10px]">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
