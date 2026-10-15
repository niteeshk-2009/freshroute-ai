import React, { useState, useMemo } from 'react';
import {
  Boxes,
  Search,
  Filter,
  ArrowUpDown,
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  Clock,
  IndianRupee,
  Download,
} from 'lucide-react';
import { InventoryBatch } from '../types';
import { Badge } from '../components/Badge';
import { importInventoryCSV, getTemplateDownloadUrl } from '../services/api';

interface InventoryPageProps {
  batches: InventoryBatch[];
  onRefresh: () => void;
}

export const InventoryPage: React.FC<InventoryPageProps> = ({ batches, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [commodityFilter, setCommodityFilter] = useState('ALL');
  const [shelfLifeFilter, setShelfLifeFilter] = useState('ALL');
  const [sortField, setSortField] = useState<'quantity_kg' | 'remaining_shelf_life_hours'>('remaining_shelf_life_hours');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Distinct commodities
  const commodities = useMemo(() => {
    const set = new Set(batches.map((b) => b.commodity));
    return Array.from(set);
  }, [batches]);

  // Filtering & Sorting
  const filteredBatches = useMemo(() => {
    return batches
      .filter((b) => {
        const matchesSearch =
          b.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          b.commodity.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCommodity = commodityFilter === 'ALL' || b.commodity === commodityFilter;

        let matchesShelfLife = true;
        if (shelfLifeFilter === 'CRITICAL') matchesShelfLife = b.remaining_shelf_life_hours < 24;
        else if (shelfLifeFilter === 'URGENT') matchesShelfLife = b.remaining_shelf_life_hours >= 24 && b.remaining_shelf_life_hours <= 48;
        else if (shelfLifeFilter === 'STABLE') matchesShelfLife = b.remaining_shelf_life_hours > 48;

        return matchesSearch && matchesCommodity && matchesShelfLife;
      })
      .sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (sortOrder === 'asc') return valA - valB;
        return valB - valA;
      });
  }, [batches, searchTerm, commodityFilter, shelfLifeFilter, sortField, sortOrder]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMessage(null);
    try {
      const res = await importInventoryCSV(file);
      setUploadMessage({
        type: 'success',
        text: `Successfully imported ${res.imported_count} inventory batches into central hub warehouse.`,
      });
      onRefresh();
    } catch (err: any) {
      setUploadMessage({
        type: 'error',
        text: err.message || 'CSV validation failed. Ensure required columns are present: id, commodity, quantity_kg, unit, remaining_shelf_life_hours',
      });
    } finally {
      setUploading(false);
    }
  };

  const totalKg = batches.reduce((sum, b) => sum + b.quantity_kg, 0);

  return (
    <div className="space-y-6">
      {/* Header & CSV Upload */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Boxes className="h-6 w-6 text-forest-700" />
            Central Hub Inventory Batches
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Active warehouse inventory batches with commodity types, available quantities (kg), and remaining shelf-life estimates.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <a
            href={getTemplateDownloadUrl('inventory')}
            download
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            <Download className="h-4 w-4 text-slate-400" />
            Template CSV
          </a>

          <label className="flex items-center gap-2 rounded-xl bg-forest-900 px-3.5 py-2 text-xs font-bold text-white hover:bg-forest-800 cursor-pointer shadow-sm transition active:scale-95">
            <UploadCloud className="h-4 w-4 text-fresh-lime" />
            {uploading ? 'Validating...' : 'Import Batch CSV'}
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Upload Notification Message */}
      {uploadMessage && (
        <div
          className={`flex items-start gap-2.5 rounded-xl p-4 text-xs font-medium border ${
            uploadMessage.type === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : 'border-rose-200 bg-rose-50 text-rose-900'
          }`}
        >
          {uploadMessage.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
          )}
          <span>{uploadMessage.text}</span>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search batch ID or commodity..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-xl border border-slate-200 pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-forest-700"
            />
          </div>

          {/* Commodity Filter */}
          <select
            value={commodityFilter}
            onChange={(e) => setCommodityFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-forest-700"
          >
            <option value="ALL">All Commodities ({batches.length})</option>
            {commodities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {/* Shelf-Life Urgency Filter */}
          <select
            value={shelfLifeFilter}
            onChange={(e) => setShelfLifeFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-forest-700"
          >
            <option value="ALL">All Shelf-Life Statuses</option>
            <option value="CRITICAL">Critical (&lt;24 hours)</option>
            <option value="URGENT">Urgent (24 - 48 hours)</option>
            <option value="STABLE">Stable (&gt;48 hours)</option>
          </select>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Sort by:</span>
          <button
            onClick={() => {
              if (sortField === 'remaining_shelf_life_hours') {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
              } else {
                setSortField('remaining_shelf_life_hours');
                setSortOrder('asc');
              }
            }}
            className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 font-semibold transition ${
              sortField === 'remaining_shelf_life_hours'
                ? 'border-forest-700 bg-forest-50 text-forest-900'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            Shelf Life {sortField === 'remaining_shelf_life_hours' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => {
              if (sortField === 'quantity_kg') {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
              } else {
                setSortField('quantity_kg');
                setSortOrder('desc');
              }
            }}
            className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 font-semibold transition ${
              sortField === 'quantity_kg'
                ? 'border-forest-700 bg-forest-50 text-forest-900'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            Weight {sortField === 'quantity_kg' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <span className="text-xs font-bold text-slate-700">
            Showing {filteredBatches.length} of {batches.length} batches
          </span>
          <span className="text-xs font-semibold text-slate-500">
            Total Available Weight: <strong className="text-slate-900 font-mono">{totalKg.toLocaleString('en-IN')} kg</strong>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 bg-slate-50/80">
                <th className="py-3 px-4 font-semibold">Batch ID</th>
                <th className="py-3 px-4 font-semibold">Commodity</th>
                <th className="py-3 px-4 font-semibold">Quantity (kg)</th>
                <th className="py-3 px-4 font-semibold">Remaining Shelf Life</th>
                <th className="py-3 px-4 font-semibold">Perishability Risk</th>
                <th className="py-3 px-4 font-semibold">Holding Cost</th>
                <th className="py-3 px-4 font-semibold">Spoilage Penalty</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredBatches.map((b) => {
                const isCritical = b.remaining_shelf_life_hours < 24;
                const isUrgent = b.remaining_shelf_life_hours >= 24 && b.remaining_shelf_life_hours <= 48;

                return (
                  <tr key={b.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">{b.id}</td>
                    <td className="py-3 px-4 font-semibold text-slate-800">{b.commodity}</td>
                    <td className="py-3 px-4 font-mono text-slate-900 font-bold">
                      {b.quantity_kg.toLocaleString('en-IN')} <span className="text-[10px] text-slate-400 font-normal">kg</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                        <Clock className={`h-3.5 w-3.5 ${isCritical ? 'text-rose-500 animate-pulse' : isUrgent ? 'text-amber-500' : 'text-slate-400'}`} />
                        <span>{b.remaining_shelf_life_hours.toFixed(1)} hrs</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={isCritical ? 'danger' : isUrgent ? 'warning' : 'success'} size="sm">
                        {isCritical ? 'Critical Expiry' : isUrgent ? 'Urgent Dispatch' : 'Stable Margin'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      ₹{b.holding_cost_per_kg_hr.toFixed(2)} /kg-hr
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      ₹{b.spoilage_cost_per_kg.toFixed(2)} /kg
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
