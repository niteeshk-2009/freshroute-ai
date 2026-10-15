import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, PageId } from './components/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { InventoryPage } from './pages/InventoryPage';
import { PlannerPage } from './pages/PlannerPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { Scenario, ScenarioSummary, InventoryBatch } from './types';
import { fetchScenarios, fetchScenario, fetchInventory } from './services/api';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null);
  const [inventoryBatches, setInventoryBatches] = useState<InventoryBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const scList = await fetchScenarios();
      setScenarios(scList);

      const defaultScId = scList.find((s) => s.id === 'SCENARIO-DEFAULT')?.id || scList[0]?.id || 'EVAL-01-NORMAL';
      if (defaultScId) {
        const sc = await fetchScenario(defaultScId);
        setCurrentScenario(sc);
      }

      const inv = await fetchInventory();
      setInventoryBatches(inv);
    } catch (err) {
      console.error('Failed to load initial application state', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectScenario = async (id: string) => {
    setRefreshing(true);
    try {
      const sc = await fetchScenario(id);
      setCurrentScenario(sc);
      if (sc && sc.inventory_batches) {
        setInventoryBatches(sc.inventory_batches);
      }
    } catch (err) {
      console.error('Failed to load selected scenario', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    if (currentScenario) {
      await handleSelectScenario(currentScenario.id);
    }
    const inv = await fetchInventory();
    setInventoryBatches(inv);
  };

  return (
    <div className="min-h-screen bg-fresh-warmWhite flex flex-col font-sans">
      <Navbar
        currentScenarioName={currentScenario?.name || ''}
        onRefresh={handleRefresh}
        isLoading={refreshing}
      />

      <div className="flex flex-1">
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          scenarioCount={scenarios.length}
        />

        <main className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full">
          {loading ? (
            <div className="flex h-96 items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-forest-900 border-t-transparent" />
                <p className="text-xs font-semibold text-slate-500">
                  Initializing FreshRoute AI Engine & Benchmark Scenarios...
                </p>
              </div>
            </div>
          ) : (
            <>
              {currentPage === 'overview' && (
                <OverviewPage
                  currentScenario={currentScenario}
                  scenarios={scenarios}
                  onSelectScenario={handleSelectScenario}
                  onNavigate={setCurrentPage}
                />
              )}
              {currentPage === 'inventory' && (
                <InventoryPage
                  batches={inventoryBatches}
                  onRefresh={handleRefresh}
                />
              )}
              {currentPage === 'planner' && (
                <PlannerPage
                  scenario={currentScenario}
                  onRefreshScenario={handleRefresh}
                />
              )}
              {currentPage === 'simulator' && (
                <SimulatorPage
                  scenario={currentScenario}
                />
              )}
              {currentPage === 'evaluation' && (
                <EvaluationPage
                  scenarios={scenarios}
                />
              )}
              {currentPage === 'reports' && (
                <ReportsPage
                  scenario={currentScenario}
                />
              )}
              {currentPage === 'settings' && (
                <SettingsPage
                  scenario={currentScenario}
                  onRefreshScenario={handleRefresh}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
