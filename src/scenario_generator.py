# scenario_generator.py
# ============================================================
# Monte Carlo scenario generator for the e-DND model.
# Implements Algorithm 2 (Appendix 7.2) and the market
# condition process (Appendix 7.1) from:
# Arslan, Klibi & Montreuil (2021)
# ============================================================
# Generates N scenarios, each consisting of:
#   - Online orders per customer location per day
#   - Physical demand per product per store per day
#   - Store fulfillment capacity per store per day
# ============================================================

import numpy as np
from scipy.stats import truncnorm
from dataclasses import dataclass
from typing import Dict, List, Tuple

import config as cfg


# ------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------

@dataclass
class OnlineOrder:
    """Represents a single online order."""
    order_id:      str
    location:      int            # customer location index l
    arrival_day:   int            # day t the order arrives (0-indexed)
    response_time: int            # requested response time in days
    products:      Dict[int, int] # {product_index: quantity}
    total_items:   int            # total number of items in the order
    revenue:       float          # net sales revenue pi^o(omega)


@dataclass
class Scenario:
    """
    A single scenario omega — one complete realization of all
    uncertain parameters over the planning horizon T.
    """
    scenario_id:            int
    orders:                 List[OnlineOrder]
    orders_by_day:          Dict[int, List[OnlineOrder]]
    orders_by_location_day: Dict[Tuple[int, int], List[OnlineOrder]]
    physical_demand:        Dict[Tuple[int, int, int], int]  # (p, s, t) -> qty
    store_capacity:         Dict[Tuple[int, int], int]       # (s, t) -> capacity


# ------------------------------------------------------------
# INSTANCE DATA
# Deterministic parameters fixed across all scenarios
# ------------------------------------------------------------

class InstanceData:
    """
    Generates and holds all deterministic instance parameters.
    These are fixed across scenarios — only uncertain parameters
    vary per scenario via Monte Carlo sampling.
    """

    def __init__(self, seed: int = cfg.RANDOM_SEED):
        self.rng = np.random.default_rng(seed)
        self._generate()

    def _generate(self):

        # --- Product prices: Uc[15, 50] (Table 2) ---
        self.product_prices = self.rng.uniform(
            cfg.PRODUCT_PRICE_RANGE[0],
            cfg.PRODUCT_PRICE_RANGE[1],
            size=cfg.NUM_PRODUCTS
        )

        # --- Product inclusion probabilities: Uc[0,1] normalized (Section 5.1) ---
        raw_probs = self.rng.uniform(0, 1, size=cfg.NUM_PRODUCTS)
        self.product_inclusion_probs = raw_probs / raw_probs.sum()  # alpha_p

        # --- Product quantity std devs: Uc[0.7, 1.2] per product (Section 5.1) ---
        self.product_quantity_stds = self.rng.uniform(
            cfg.ORDER_QUANTITY_STD_RANGE[0],
            cfg.ORDER_QUANTITY_STD_RANGE[1],
            size=cfg.NUM_PRODUCTS
        )

        # --- Store categories: high-traffic or regular ---
        n_high = max(1, int(cfg.NUM_STORES * cfg.HIGH_TRAFFIC_FRACTION))
        self.store_category = ["regular"] * cfg.NUM_STORES
        high_indices = self.rng.choice(cfg.NUM_STORES, size=n_high, replace=False)
        for i in high_indices:
            self.store_category[i] = "high"

        # --- Store fixed activation costs (Table 2) ---
        self.store_fixed_costs = np.zeros(cfg.NUM_STORES)
        for s in range(cfg.NUM_STORES):
            lo, hi = cfg.STORE_FIXED_COST_RANGE[self.store_category[s]]
            self.store_fixed_costs[s] = (
                self.rng.integers(lo // 1000, hi // 1000 + 1) * 1000
            )

        # --- Store average fulfillment capacity (Section 5.1) ---
        self.store_avg_capacity = np.zeros(cfg.NUM_STORES, dtype=int)
        for s in range(cfg.NUM_STORES):
            lo, hi = cfg.STORE_CAPACITY_RANGE[self.store_category[s]]
            self.store_avg_capacity[s] = self.rng.integers(lo, hi + 1)

        # --- Store replenishment periods (Section 5.1) ---
        # High-traffic stores replenished every 2 days
        # Regular stores replenished every 5 days
        self.store_replenishment_periods: List[List[int]] = []
        for s in range(cfg.NUM_STORES):
            freq = cfg.REPLENISHMENT_FREQUENCY[self.store_category[s]]
            periods = list(range(0, cfg.NUM_PERIODS, freq))
            self.store_replenishment_periods.append(periods)

        # --- FC replenishment: every period (Section 3.1) ---
        self.fc_replenishment_periods: List[List[int]] = []
        for _ in range(cfg.NUM_FCS):
            self.fc_replenishment_periods.append(list(range(cfg.NUM_PERIODS)))

        # --- Online order arrival rates per customer location ---
        # lambda_l = 0.165 * Ud[1,10] (Section 5.1)
        self.order_arrival_rates = (
            cfg.ORDER_ARRIVAL_RATE_MULTIPLIER *
            self.rng.integers(
                cfg.ORDER_ARRIVAL_RATE_RANGE[0],
                cfg.ORDER_ARRIVAL_RATE_RANGE[1] + 1,
                size=cfg.NUM_CUSTOMER_LOCATIONS
            ).astype(float)
        )

        # Apply demand ratio multiplier (Section 5.1)
        dr_multiplier = cfg.DEMAND_RATIO_MULTIPLIERS[cfg.DEMAND_RATIO]
        self.order_arrival_rates *= dr_multiplier

        # --- Expected physical demand per product per store ---
        # lambda^p_s = 1.3 * Ud[1,6] (Section 5.1)
        base_demand = (
            cfg.PHYSICAL_DEMAND_MULTIPLIER *
            self.rng.integers(
                cfg.PHYSICAL_DEMAND_RANGE[0],
                cfg.PHYSICAL_DEMAND_RANGE[1] + 1,
                size=(cfg.NUM_PRODUCTS, cfg.NUM_STORES)
            ).astype(float)
        )
        # High-traffic stores multiply by 1.2
        for s in range(cfg.NUM_STORES):
            if self.store_category[s] == "high":
                base_demand[:, s] *= cfg.HIGH_TRAFFIC_DEMAND_MULTIPLIER
        self.expected_physical_demand = base_demand  # shape: (P, S)

        # --- Response time distribution for active RE level ---
        rt_dist = cfg.RESPONSE_TIME_DISTRIBUTIONS[cfg.RESPONSE_TIME_EXPECTATION]
        self.response_time_probs = [
            rt_dist["1D"],
            rt_dist["2D"],
            rt_dist["3D"],
        ]
        self.response_time_values = [1, 2, 3]  # days

        # --- Store-to-customer response times ---
        # All stores and FCs in city => next-day (1 day) feasible
        # Warehouse => 2-day only
        self.store_response_times = np.ones(
            (cfg.NUM_STORES, cfg.NUM_CUSTOMER_LOCATIONS), dtype=int
        )
        self.fc_response_times = np.ones(
            (cfg.NUM_FCS, cfg.NUM_CUSTOMER_LOCATIONS), dtype=int
        )
        self.warehouse_response_time = cfg.WAREHOUSE_RESPONSE_TIME  # 2 days

        # --- Transportation costs: store to customer location ---
        # Uc[3,5] $/order (Table 2)
        self.store_transport_costs = self.rng.uniform(
            cfg.STORE_TRANSPORT_COST_RANGE[0],
            cfg.STORE_TRANSPORT_COST_RANGE[1],
            size=(cfg.NUM_STORES, cfg.NUM_CUSTOMER_LOCATIONS)
        )

        # --- FC transport costs: 3.5 $/order (Table 2) ---
        self.fc_transport_costs = np.full(
            (cfg.NUM_FCS, cfg.NUM_CUSTOMER_LOCATIONS),
            cfg.FC_TRANSPORT_COST_PER_ORDER
        )

        # --- Warehouse transport costs: 5 $/order (Table 2) ---
        self.warehouse_transport_costs = np.full(
            cfg.NUM_CUSTOMER_LOCATIONS,
            cfg.WAREHOUSE_TRANSPORT_COST_PER_ORDER
        )

        # --- Picking costs per supply point (Table 2) ---
        self.warehouse_picking_cost = cfg.WAREHOUSE_PICKING_COST_BASE
        self.store_picking_costs = np.full(
            cfg.NUM_STORES,
            cfg.STORE_PICKING_COST_MULTIPLIER * cfg.WAREHOUSE_PICKING_COST_BASE
        )
        self.fc_picking_costs = np.full(
            cfg.NUM_FCS,
            cfg.FC_PICKING_COST_MULTIPLIER * cfg.WAREHOUSE_PICKING_COST_BASE
        )

        # --- Per-order warehouse charge cwo (Table 2) ---
        # Combines fixed (40%), holding (1%), replenishment (15%) charges
        avg_price = self.product_prices.mean()
        self.warehouse_order_charge = (
            cfg.WAREHOUSE_FIXED_CHARGE +
            cfg.WAREHOUSE_HOLDING_CHARGE +
            cfg.WAREHOUSE_REPLENISHMENT_CHARGE
        ) * avg_price


# ------------------------------------------------------------
# MARKET CONDITION PROCESS  (Appendix 7.1)
# ------------------------------------------------------------

def generate_market_conditions(rng: np.random.Generator) -> np.ndarray:
    """
    Generates a sequence of market conditions m_t for t in T.
    Implements the truncated normal process from Appendix 7.1.

    The market condition governs the correlation between
    physical demand and store fulfillment capacity:
      - High mt => more shoppers => higher demand, lower capacity
      - Low mt  => fewer shoppers => lower demand, higher capacity

    Returns:
        market_conditions: array of shape (T,) with values in [mmin, mmax]
    """
    mc          = cfg.MARKET_CONDITION
    m_bar       = mc["m_bar"]
    s_base      = mc["s"]
    delta_m_bar = mc["delta_m_bar"]
    delta_s     = mc["delta_s"]
    beta        = mc["beta"]
    m_min       = mc["m_min"]
    m_max       = mc["m_max"]

    market_conditions = np.zeros(cfg.NUM_PERIODS)
    mt = mc["m0"]  # start at steady state mean

    for t in range(cfg.NUM_PERIODS):
        # Update mean: revert toward m_bar
        if mt < m_bar:
            mu = mt + min(delta_m_bar * (m_bar - mt), m_bar - mt)
        else:
            mu = mt - min(delta_m_bar * (mt - m_bar), mt - m_bar)

        # Update std: increases with distance from steady state
        s_t = s_base + delta_s * (mt - m_bar) ** 2

        # Truncation bounds centered on current mt
        a = max(m_min, mt - beta)
        b = min(m_max, mt + beta)

        # Sample from truncated normal
        if a >= b or s_t <= 0:
            mt = np.clip(mu, m_min, m_max)
        else:
            alpha_trunc = (a - mu) / s_t
            beta_trunc  = (b - mu) / s_t
            mt = truncnorm.rvs(
                alpha_trunc, beta_trunc,
                loc=mu, scale=s_t,
                random_state=rng.integers(0, 2**31)
            )

        market_conditions[t] = mt

    return market_conditions


# ------------------------------------------------------------
# SCENARIO GENERATOR  (Algorithm 2, Appendix 7.2)
# ------------------------------------------------------------

class ScenarioGenerator:
    """
    Generates N scenarios via repeated Monte Carlo sampling.
    Each scenario is a complete realization of the uncertain
    environment over the planning horizon T.
    """

    def __init__(self, instance: InstanceData, seed: int = cfg.RANDOM_SEED):
        self.instance = instance
        self.rng = np.random.default_rng(seed + 1)  # separate from instance seed

    def generate(self, n_scenarios: int = cfg.N_SCENARIOS) -> List[Scenario]:
        """Generate n_scenarios independent scenarios."""
        scenarios = []
        for i in range(n_scenarios):
            scenario = self._generate_single_scenario(i)
            scenarios.append(scenario)
        return scenarios

    def _generate_single_scenario(self, scenario_id: int) -> Scenario:
        """
        Implements Algorithm 2 from Appendix 7.2.
        Generates one complete scenario omega.
        """
        inst = self.instance

        # --------------------------------------------------
        # STEP 1: Generate market conditions for all periods
        # Drives correlation between demand and capacity
        # --------------------------------------------------
        market_conditions = generate_market_conditions(self.rng)
        mu_bar = cfg.MARKET_CONDITION["m_bar"]

        # --------------------------------------------------
        # STEP 2: Generate online orders per customer location
        # Poisson arrival process over continuous time [0, T]
        # mapped onto discrete days (Algorithm 2, lines 1-18)
        # --------------------------------------------------
        all_orders: List[OnlineOrder] = []
        order_counter = 0

        for l in range(cfg.NUM_CUSTOMER_LOCATIONS):
            arrival_rate      = inst.order_arrival_rates[l]  # lambda_l
            inter_arrival_mean = 1.0 / arrival_rate

            eta = 0.0  # continuous time position
            while True:
                # Sample next inter-arrival from Exponential(lambda_l)
                inter_arrival = self.rng.exponential(inter_arrival_mean)
                eta += inter_arrival

                if eta > cfg.NUM_PERIODS:
                    break

                # Map to discrete day (0-indexed, ceiling rule)
                arrival_day = min(int(np.ceil(eta)) - 1, cfg.NUM_PERIODS - 1)
                arrival_day = max(0, arrival_day)

                # Sample requested response time
                response_time = int(self.rng.choice(
                    inst.response_time_values,
                    p=inst.response_time_probs
                ))

                # Sample number of product types in order: Ud[kmin, kmax]
                k_o = int(self.rng.integers(
                    cfg.ORDER_MIN_ITEMS,
                    cfg.ORDER_MAX_ITEMS + 1
                ))

                # Sample products and quantities
                products: Dict[int, int] = {}
                for _ in range(k_o):
                    p_idx = int(self.rng.choice(
                        cfg.NUM_PRODUCTS,
                        p=inst.product_inclusion_probs
                    ))
                    qty = max(1, int(round(
                        self.rng.normal(
                            cfg.ORDER_QUANTITY_MEAN,
                            inst.product_quantity_stds[p_idx]
                        )
                    )))
                    products[p_idx] = products.get(p_idx, 0) + qty

                total_items = sum(products.values())
                revenue = sum(
                    inst.product_prices[p] * qty
                    for p, qty in products.items()
                )

                all_orders.append(OnlineOrder(
                    order_id=f"o_{scenario_id}_{l}_{order_counter}",
                    location=l,
                    arrival_day=arrival_day,
                    response_time=response_time,
                    products=products,
                    total_items=total_items,
                    revenue=revenue
                ))
                order_counter += 1

        # Sort chronologically (Algorithm 2, line 18)
        all_orders.sort(key=lambda o: (o.arrival_day, o.location))

        # Build index structures for efficient model access
        orders_by_day: Dict[int, List[OnlineOrder]] = {
            t: [] for t in range(cfg.NUM_PERIODS)
        }
        orders_by_location_day: Dict[Tuple[int, int], List[OnlineOrder]] = {}

        for order in all_orders:
            orders_by_day[order.arrival_day].append(order)
            key = (order.location, order.arrival_day)
            if key not in orders_by_location_day:
                orders_by_location_day[key] = []
            orders_by_location_day[key].append(order)

        # --------------------------------------------------
        # STEP 3: Generate physical demand d^p_st(omega)
        # Poisson with rate adjusted by market condition
        # (Algorithm 2, lines 23-26)
        # --------------------------------------------------
        physical_demand: Dict[Tuple[int, int, int], int] = {}

        for t in range(cfg.NUM_PERIODS):
            mt = market_conditions[t]
            for s in range(cfg.NUM_STORES):
                for p in range(cfg.NUM_PRODUCTS):
                    adjusted_rate = max(
                        0.01,
                        inst.expected_physical_demand[p, s] * (mt / mu_bar)
                    )
                    physical_demand[(p, s, t)] = int(self.rng.poisson(adjusted_rate))

        # --------------------------------------------------
        # STEP 4: Generate store capacities b_st(omega)
        # Inversely adjusted by market condition
        # High-traffic stores further reduced when mt > mu_bar
        # (Algorithm 2, lines 27-29)
        # --------------------------------------------------
        store_capacity: Dict[Tuple[int, int], int] = {}
        f_factor = 0.8  # reduction factor for popular stores (0 < f < 1)

        for t in range(cfg.NUM_PERIODS):
            mt = market_conditions[t]
            for s in range(cfg.NUM_STORES):
                cap = inst.store_avg_capacity[s] * (mu_bar / mt)
                if inst.store_category[s] == "high" and mt > mu_bar:
                    cap *= f_factor
                store_capacity[(s, t)] = max(1, int(round(cap)))

        return Scenario(
            scenario_id=scenario_id,
            orders=all_orders,
            orders_by_day=orders_by_day,
            orders_by_location_day=orders_by_location_day,
            physical_demand=physical_demand,
            store_capacity=store_capacity
        )


# ------------------------------------------------------------
# VALIDATION
# Run after generation to confirm distributions match
# paper Section 5.1 and Table 3
# ------------------------------------------------------------

def validate_scenarios(scenarios: List[Scenario], instance: InstanceData):
    """
    Prints summary statistics to validate scenario distributions
    against expected values from the paper.
    """
    print("=" * 60)
    print("SCENARIO VALIDATION SUMMARY")
    print("=" * 60)

    # --- Order volume ---
    total_orders = [len(s.orders) for s in scenarios]
    print("\nOnline Orders per Scenario:")
    print(f"  Mean : {np.mean(total_orders):.1f}")
    print(f"  Std  : {np.std(total_orders):.1f}")
    print(f"  Min  : {np.min(total_orders)}")
    print(f"  Max  : {np.max(total_orders)}")

    # --- Response time distribution vs Table 3 ---
    rt_counts = {1: 0, 2: 0, 3: 0}
    for s in scenarios:
        for o in s.orders:
            rt_counts[o.response_time] += 1
    total = sum(rt_counts.values())
    print("\nResponse Time Distribution (actual vs expected from Table 3):")
    rt_dist = cfg.RESPONSE_TIME_DISTRIBUTIONS[cfg.RESPONSE_TIME_EXPECTATION]
    for rt, label in [(1, "1D"), (2, "2D"), (3, "3D")]:
        actual   = rt_counts[rt] / total if total > 0 else 0
        expected = rt_dist[label]
        print(f"  {label}: actual={actual:.3f}  expected={expected:.3f}")

    # --- Order size ---
    all_items = [o.total_items for s in scenarios for o in s.orders]
    print("\nItems per Order:")
    print(f"  Mean : {np.mean(all_items):.2f}")
    print(f"  Std  : {np.std(all_items):.2f}")
    print(f"  Min  : {np.min(all_items)}")
    print(f"  Max  : {np.max(all_items)}")

    # --- Physical demand ---
    avg_demand = np.mean([v for s in scenarios for v in s.physical_demand.values()])
    print(f"\nAverage Physical Demand per (product, store, day): {avg_demand:.3f}")

    # --- Store capacity ---
    avg_cap = np.mean([v for s in scenarios for v in s.store_capacity.values()])
    print(f"Average Store Capacity per (store, day): {avg_cap:.2f}")

    # --- Store categories and parameters ---
    print("\nStore Parameters:")
    for s in range(cfg.NUM_STORES):
        print(f"  Store {s}: category={instance.store_category[s]:<8}"
              f"  avg_cap={instance.store_avg_capacity[s]}"
              f"  fixed_cost={instance.store_fixed_costs[s]:.0f}")

    print("=" * 60)


# ------------------------------------------------------------
# MAIN
# Run directly to generate and validate scenarios
# ------------------------------------------------------------

if __name__ == "__main__":
    print(f"Generating scenarios for {cfg.CITY} | "
          f"RE={cfg.RESPONSE_TIME_EXPECTATION} | "
          f"DR={cfg.DEMAND_RATIO}")
    print(f"N={cfg.N_SCENARIOS} scenarios | "
          f"T={cfg.NUM_PERIODS} periods | "
          f"P={cfg.NUM_PRODUCTS} products\n")

    instance  = InstanceData(seed=cfg.RANDOM_SEED)
    generator = ScenarioGenerator(instance, seed=cfg.RANDOM_SEED)
    scenarios = generator.generate(n_scenarios=cfg.N_SCENARIOS)

    validate_scenarios(scenarios, instance)

    print(f"\nGeneration complete. Total scenarios: {len(scenarios)}")
    print(f"Scenario 0 — total orders    : {len(scenarios[0].orders)}")
    print(f"Scenario 0 — orders on day 0 : {len(scenarios[0].orders_by_day[0])}")
