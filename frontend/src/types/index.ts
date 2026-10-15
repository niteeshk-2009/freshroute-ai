export interface InventoryBatch {
  id: string;
  commodity: string;
  quantity_kg: number;
  unit: string;
  remaining_shelf_life_hours: number;
  harvest_timestamp?: string;
  holding_cost_per_kg_hr: number;
  spoilage_cost_per_kg: number;
}

export interface Destination {
  id: string;
  name: string;
  demand: Record<string, number>;
  market_price: Record<string, number>;
  receiving_capacity_kg: number;
  priority: number;
  demand_window_hours: number;
}

export interface TransportOption {
  id: string;
  origin: string;
  destination_id: string;
  travel_time_hours: number;
  cost_per_kg: number;
  capacity_kg: number;
  handling_time_hours: number;
  available: boolean;
}

export interface CostAssumptions {
  handling_cost_per_kg: number;
  holding_cost_default_per_kg_hr: number;
  spoilage_penalty_multiplier: number;
  allow_negative_contribution: boolean;
  spoilage_threshold_hours: number;
}

export interface DiscountConfig {
  enabled: boolean;
  steps: number[];
  elasticity_multiplier: number;
  shelf_life_threshold_hours: number;
}

export interface ShipmentPlan {
  batch_id: string;
  destination_id: string;
  transport_id: string;
  allocated_qty_kg: number;
  departure_time: number;
  arrival_time: number;
  handling_completion_time: number;
  shelf_life_remaining_at_delivery_hours: number;
  expected_sale_qty_kg: number;
  discount_pct: number;
  revenue: number;
  transport_cost: number;
  handling_cost: number;
  holding_cost: number;
  net_contribution: number;
  feasibility_status: 'FEASIBLE' | 'INFEASIBLE';
  explanation: Record<string, any>;
  rejection_reasons: string[];
}

export interface EvaluationResult {
  strategy_name: string;
  shipments: ShipmentPlan[];
  total_revenue: number;
  total_transport_cost: number;
  total_handling_cost: number;
  total_holding_cost: number;
  total_spoilage_cost: number;
  net_revenue: number;
  spoiled_qty_kg: number;
  spoilage_rate_pct: number;
  demand_fulfilled_qty_kg: number;
  total_demand_kg: number;
  fulfillment_pct: number;
  inventory_utilization_pct: number;
  unallocated_qty_kg: number;
  feasible_shipment_count: number;
  shelf_life_violations: number;
  capacity_violations: number;
  execution_time_ms: number;
  metadata?: Record<string, any>;
}

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  inventory_batches: InventoryBatch[];
  destinations: Destination[];
  transport_options: TransportOption[];
  cost_assumptions: CostAssumptions;
  discount_config: DiscountConfig;
  seed: number;
  created_at?: string;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  batch_count: number;
  destination_count: number;
  transport_count: number;
  total_inventory_kg: number;
  total_demand_kg: number;
  seed: number;
  created_at: string;
}

export interface ComparisonMetric {
  baseline: number;
  optimized: number;
  absolute_difference: number;
  relative_difference_pct: number | null;
  preferred_direction: 'higher' | 'lower';
  unit: string;
  optimizer_better: boolean;
  display: string;
}

export interface ComparisonResponse {
  scenario_id: string;
  baseline: EvaluationResult;
  optimized: EvaluationResult;
  comparison: Record<string, ComparisonMetric>;
  summary: {
    verdict: string;
    description: string;
    narrative?: string;
    improvements_count: number;
    regressions_count: number;
    unchanged_count: number;
    key_findings: {
      net_revenue_change_inr: number;
      spoilage_rate_change_pct_points: number;
      fulfillment_change_pct_points: number;
    };
    baseline_execution_ms: number;
    optimizer_execution_ms: number;
  };
  discount_recommendations: DiscountRecommendation[];
}

export interface DiscountRecommendation {
  batch_id: string;
  commodity: string;
  destination?: string;
  risk_reason: string;
  recommended_discount_pct: number;
  original_price_inr: number;
  discounted_price_inr: number;
  assumed_additional_demand_pct: number;
  expected_revenue_change_inr: number;
  expected_net_contribution_change_inr: number;
  recommendation: string;
  assumptions: string;
}

export interface SimulationModifications {
  demand_multipliers?: Record<string, number>;
  price_multipliers?: Record<string, number>;
  destination_price_overrides?: Record<string, Record<string, number>>;
  destination_demand_overrides?: Record<string, Record<string, number>>;
  transport_delays_hours?: Record<string, number>;
  transport_availability?: Record<string, boolean>;
  capacity_multipliers?: Record<string, number>;
  allow_negative_contribution?: boolean;
  spoilage_threshold_hours?: number;
}
