# subproblem.py
# ============================================================
# Stage 2 subproblem: Order Fulfillment MIP — Q(y, omega)
# ============================================================
# Given:
#   y     — fixed Stage 1 network configuration (which stores
#            and FCs are activated as ship-from points)
#   omega — one realized scenario (orders, demand, capacities)
#
# Finds the optimal:
#   z^o_ς    — order-to-supply-point assignment
#   x^p_ςt  — replenishment quantities
#   I^p_ςt  — inventory levels
#   B^p_st  — backlog levels
#
# Returns:
#   Q(y, omega) — optimal profit for this network and scenario
#   Solution object with all decision variable values
#
# Reference: Arslan, Klibi & Montreuil (2021), Section 3.4
#            Equations (4) - (13)
# ============================================================
# Installation required:
#   pip install pulp
# ============================================================

import pulp
from dataclasses import dataclass
from typing import Dict, Tuple

import config as cfg
from scenario_generator import InstanceData, Scenario, OnlineOrder


# ------------------------------------------------------------
# SOLUTION DATA STRUCTURE
# ------------------------------------------------------------

@dataclass
class SubproblemSolution:
    """Holds the optimal solution to Q(y, omega)."""

    # Objective value
    profit:              float

    # Revenue components
    physical_revenue:    float
    online_revenue:      float

    # Cost components
    backlog_cost:        float
    replenishment_cost:  float
    holding_cost:        float
    picking_cost:        float
    transport_cost:      float
    warehouse_cost:      float

    # Fulfillment statistics
    orders_fulfilled_store:     int
    orders_fulfilled_fc:        int
    orders_fulfilled_warehouse: int
    orders_lost:                int
    total_orders:               int
    pct_lost:                   float

    # Decision variable values
    order_assignments:   Dict[str, str]          # order_id -> supply point label
    replenishment:       Dict[Tuple, float]       # (supply_point, product, day) -> qty
    inventory:           Dict[Tuple, float]       # (supply_point, product, day) -> level
    backlog:             Dict[Tuple, float]        # (store, product, day) -> backlog

    # SW fairness adjustment (only non-zero for SW strategy)
    # = expected physical replenishment + holding cost subtracted
    #   to level the playing field vs SS/SF
    sw_physical_cost_adjustment: float = 0.0

    # Solver status
    status:              str = 'Unknown'


# ------------------------------------------------------------
# SUPPLY POINT INDEXING HELPERS
# ------------------------------------------------------------

def get_supply_points(y: Dict[int, int]) -> Dict[str, dict]:
    """
    Builds a dictionary of active supply points given deployment y.

    y is a dict: {supply_point_index: 0 or 1}
    Indices 0..NUM_STORES-1 are stores
    Indices NUM_STORES..NUM_STORES+NUM_FCS-1 are FCs
    The warehouse is always available (index = -1 / label = 'w')

    Returns dict keyed by supply point label, e.g.:
        's0', 's1', 'f0', 'w'
    """
    supply_points = {}

    # Warehouse is always available
    supply_points['w'] = {
        'type':  'warehouse',
        'index': -1,
        'active': True
    }

    # Stores
    for s in range(cfg.NUM_STORES):
        label = f's{s}'
        supply_points[label] = {
            'type':   'store',
            'index':  s,
            'active': bool(y.get(s, 0))
        }

    # Fulfillment centers
    for f in range(cfg.NUM_FCS):
        idx   = cfg.NUM_STORES + f
        label = f'f{f}'
        supply_points[label] = {
            'type':   'fc',
            'index':  f,
            'active': bool(y.get(idx, 0))
        }

    return supply_points


def can_fulfill_in_time(
    sp_label: str,
    sp_info: dict,
    order: OnlineOrder,
    instance: InstanceData
) -> bool:
    """
    Returns True if supply point can fulfill the order
    within its requested response time.

    Constraint (10): order assigned only if r_ςl <= eta^o(omega)
    """
    rt = order.response_time
    l  = order.location

    if sp_info['type'] == 'warehouse':
        return instance.warehouse_response_time <= rt

    elif sp_info['type'] == 'store':
        s = sp_info['index']
        return instance.store_response_times[s, l] <= rt

    elif sp_info['type'] == 'fc':
        f = sp_info['index']
        return instance.fc_response_times[f, l] <= rt

    return False


# ------------------------------------------------------------
# SW PHYSICAL COST CORRECTION
# ------------------------------------------------------------

def compute_sw_physical_cost_adjustment(
    scenarios: list,
    instance: 'InstanceData'
) -> float:
    """
    Computes the expected physical replenishment and holding costs
    that SW incurs at stores but does not charge in its MIP objective.

    Under SS and SF, activated stores bear explicit replenishment and
    holding costs driven by shared inventory (physical + online demand).
    Under SW, stores are not modeled — their physical replenishment and
    holding costs are implicitly zero in the MIP, creating an unfair
    advantage for SW in profit comparisons.

    This function computes the EXPECTED value of those missing costs
    across all scenarios and returns a single fixed constant. Subtracting
    this constant from every SW scenario profit:
      - Eliminates the cost asymmetry
      - Does NOT introduce scenario-level variance into SW
        (same constant subtracted from every scenario)
      - Does NOT affect SS or SF models (they are unchanged)
      - Makes the profit comparison apples-to-apples

    Physical replenishment cost per replenishment period:
        cost = STORE_REPLENISHMENT_COST * price[p]
               * demand accumulated since last replenishment

    Physical holding cost per period:
        cost = STORE_HOLDING_COST * price[p] * inventory_level[t]

    Inventory level is approximated as a simple sawtooth:
        starts at replenishment qty, depletes linearly to zero
        by next replenishment. Average = replenishment_qty / 2.

    Parameters
    ----------
    scenarios : list of Scenario objects (the same N scenarios used in MIP)
    instance  : InstanceData

    Returns
    -------
    float — fixed constant to subtract from every SW scenario profit
    """
    inst = instance
    total_cost_across_scenarios = 0.0
    N = len(scenarios)

    for scenario in scenarios:
        scenario_cost = 0.0

        for s in range(cfg.NUM_STORES):
            rep_periods = inst.store_replenishment_periods[s]

            # Cycle structure and cost treatment:
            #
            # rep_periods = [5, 10, 15, 20, 25] for a regular store (T=30)
            #
            # FIRST cycle [0, rep_periods[0]):
            #   Demand covered by INITIAL INVENTORY — no replenishment fires.
            #   Skip both replenishment and holding cost.
            #   (initial inventory cost is a pre-horizon sunk cost)
            #
            # INTERIOR cycles [rep_periods[k-1], rep_periods[k]):
            #   A replenishment fires at rep_periods[k] to cover this demand.
            #   Charge BOTH replenishment cost AND holding cost.
            #
            # LAST partial cycle [rep_periods[-1], T):
            #   The day-rep_periods[-1] delivery already arrived and is on shelves.
            #   Demand on these days depletes that inventory — holding cost applies.
            #   No new replenishment fires within the horizon — replenishment cost = $0.
            #   Charge HOLDING COST ONLY.

            if len(rep_periods) == 0:
                continue

            for p in range(cfg.NUM_PRODUCTS):
                price = inst.product_prices[p]

                # --- Interior cycles: both replenishment and holding ---
                # Cycle k covers demand from [rep_periods[k-1], rep_periods[k])
                # replenished at rep_periods[k]. Skip k=0 (first cycle = initial inv).
                for k in range(1, len(rep_periods)):
                    t_start = rep_periods[k - 1]
                    t_end   = rep_periods[k]

                    cycle_demand = sum(
                        scenario.physical_demand.get((p, s, t), 0)
                        for t in range(t_start, t_end)
                    )

                    # Replenishment cost: delivery on rep_periods[k] covers this demand
                    scenario_cost += cfg.STORE_REPLENISHMENT_COST * price * cycle_demand

                    # Holding cost: sawtooth — inventory starts at cycle_demand,
                    # depletes linearly to 0 by the next replenishment
                    cycle_length = t_end - t_start
                    if cycle_length > 0:
                        avg_inventory = cycle_demand / 2.0
                        scenario_cost += (
                            cfg.STORE_HOLDING_COST * price
                            * avg_inventory * cycle_length
                        )

                # --- Last partial cycle: holding cost only ---
                # Days from final replenishment to end of horizon.
                # Inventory received on rep_periods[-1] sits on shelves — holding applies.
                # No replenishment fires after rep_periods[-1] within the horizon.
                t_last_start = rep_periods[-1]
                t_last_end   = cfg.NUM_PERIODS        # e.g. day 30

                if t_last_end > t_last_start:
                    last_cycle_demand = sum(
                        scenario.physical_demand.get((p, s, t), 0)
                        for t in range(t_last_start, t_last_end)
                    )
                    last_cycle_length = t_last_end - t_last_start
                    avg_inventory_last = last_cycle_demand / 2.0
                    scenario_cost += (
                        cfg.STORE_HOLDING_COST * price
                        * avg_inventory_last * last_cycle_length
                    )
                    # No replenishment cost — delivery for this demand is outside horizon

        total_cost_across_scenarios += scenario_cost

    # Return expected cost = mean across all N scenarios
    expected_cost = total_cost_across_scenarios / N
    return expected_cost


# ------------------------------------------------------------
# SUBPROBLEM SOLVER
# ------------------------------------------------------------

class SubproblemSolver:
    """
    Builds and solves the Stage 2 MIP Q(y, omega) using PuLP.

    The model follows equations (4)-(13) from the paper exactly.
    """

    def __init__(self, instance: InstanceData):
        self.instance = instance

    def solve(
        self,
        y: Dict[int, int],
        scenario: Scenario,
        verbose: bool = False,
        sw_physical_cost_adjustment: float = 0.0
    ) -> SubproblemSolution:
        """
        Solve Q(y, omega) for a given network configuration y
        and a single scenario omega.

        Parameters
        ----------
        y        : deployment decision {supply_point_index: 0/1}
        scenario : one realized scenario omega
        verbose  : if True, print solver output

        Returns
        -------
        SubproblemSolution with optimal profit and all variable values
        """
        inst = self.instance
        T    = cfg.NUM_PERIODS
        P    = cfg.NUM_PRODUCTS
        #S    = cfg.NUM_STORES
        #F    = cfg.NUM_FCS

        # Get active supply points
        supply_points = get_supply_points(y)
        active_sps    = {k: v for k, v in supply_points.items() if v['active']}
        active_stores = {k: v for k, v in active_sps.items() if v['type'] == 'store'}
        #active_fcs    = {k: v for k, v in active_sps.items() if v['type'] == 'fc'}

        # Pre-compute physical replenishment baseline (sunk cost, not optimized)
        # x_phys[(s_index, p, t)] = demand accumulated since last replenishment
        #x_phys_baseline = compute_physical_replenishment(scenario, inst)

        # All orders in this scenario
        all_orders = scenario.orders

        # -----------------------------------------------
        # BUILD PuLP MODEL
        # -----------------------------------------------
        model = pulp.LpProblem("Q_y_omega", pulp.LpMaximize)

        # -----------------------------------------------
        # DECISION VARIABLES
        # -----------------------------------------------

        # z^o_ς(omega): binary — order o fulfilled from supply point ς
        # Equation (13): z in {0,1}
        z = {}
        # Use integer indices for variable names to ensure CBC
        # correctly parses and enforces binary constraints.
        # String-based names with underscores can cause CBC to
        # fail to register variables in its binary variable list.
        z_idx = 0
        for order in all_orders:
            for sp_label, sp_info in supply_points.items():
                # Only create variable if supply point is active
                # and can meet the response time requirement
                if not sp_info['active']:
                    continue
                if not can_fulfill_in_time(sp_label, sp_info, order, inst):
                    continue
                z[(order.order_id, sp_label)] = pulp.LpVariable(
                    f"z{z_idx}",
                    cat='Binary'
                )
                z_idx += 1

        # x^p_ςt(omega): continuous — replenishment qty of product p
        # at ship-from point ς on day t
        # Only on replenishment days, only for active non-warehouse points
        x = {}
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue
            if sp_info['type'] == 'store':
                s      = sp_info['index']
                rep_days = inst.store_replenishment_periods[s]
            else:
                f        = sp_info['index']
                rep_days = inst.fc_replenishment_periods[f]

            for p in range(P):
                for t in rep_days:
                    x[(sp_label, p, t)] = pulp.LpVariable(
                        f"x_{sp_label}_{p}_{t}",
                        lowBound=0
                    )

        # I^p_ςt(omega): continuous — inventory level at start of period t
        # Equation (13): I >= 0
        I = {}
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue
            for p in range(P):
                for t in range(T + 1):  # +1 for end-of-horizon inventory
                    I[(sp_label, p, t)] = pulp.LpVariable(
                        f"I_{sp_label}_{p}_{t}",
                        lowBound=0
                    )

        # B^p_st(omega): continuous — backlog of product p at store s
        # Only stores have backlogs (physical demand can be backlogged)
        # Equation (13): B >= 0
        B = {}
        for sp_label, sp_info in active_stores.items():
            s = sp_info['index']
            for p in range(P):
                for t in range(T + 1):
                    B[(sp_label, p, t)] = pulp.LpVariable(
                        f"B_{sp_label}_{p}_{t}",
                        lowBound=0
                    )

        # -----------------------------------------------
        # OBJECTIVE FUNCTION  (Equation 4)
        # Maximize total profit:
        #   + physical sales revenue (net of backlog)
        #   - backlogging cost
        #   - replenishment cost
        #   - holding cost
        #   + online order profit from ship-from points
        #   + online order profit from warehouse
        # -----------------------------------------------
        obj_terms = []

        # --- Physical sales revenue and backlog cost (ALL stores) ---
        # Physical revenue exists at every store regardless of activation.
        # Non-activated stores are assumed to fully meet physical demand.
        # Activated stores share inventory with online orders => may backlog.
        all_store_sps = {k: v for k, v in supply_points.items()
                         if v['type'] == 'store'}
        for sp_label, sp_info in all_store_sps.items():
            s = sp_info['index']
            for p in range(P):
                price = inst.product_prices[p]
                for t in range(T):
                    d_pst = scenario.physical_demand.get((p, s, t), 0)
                    if sp_info['active']:
                        # Activated: revenue net of NEW backlog created in period t
                        # Units actually sold in t = d_pst - (B[t+1] - B[t])
                        # i.e. demand minus the NEW shortfall created this period.
                        # B[t+1] is cumulative backlog; subtracting B[t] isolates
                        # only the increment, avoiding double-counting across periods.
                        # Backlog penalty applies to the stock of backlog at start of t.
                        obj_terms.append(price * d_pst)
                        obj_terms.append(-price * B[(sp_label, p, t + 1)])
                        obj_terms.append(+price * B[(sp_label, p, t)])
                        b_cost = cfg.STORE_BACKLOGGING_COST * price
                        obj_terms.append(-b_cost * B[(sp_label, p, t)])
                    else:
                        # Non-activated: full physical revenue, no backlog
                        obj_terms.append(price * d_pst)

        # --- Replenishment cost at ship-from points ---
        # x[s,p,t] represents total replenishment covering both physical
        # and online demand. Physical replenishment cost in SW strategy
        # is zero (stores not modeled). The incremental replenishment cost
        # in SS versus SW reflects the additional inventory needed to
        # serve the online channel from activated stores.        
        for (sp_label, p, t), var in x.items():
            sp_info = supply_points[sp_label]
            price   = inst.product_prices[p]
            if sp_info['type'] == 'store':
                r_cost = cfg.STORE_REPLENISHMENT_COST * price
            else:
                r_cost = cfg.FC_REPLENISHMENT_COST * price
            obj_terms.append(-r_cost * var)

        # --- Holding cost at ship-from points ---
        for (sp_label, p, t), var in I.items():
            if t == T:
                continue  # no holding cost for end-of-horizon inventory
            sp_info = supply_points[sp_label]
            price   = inst.product_prices[p]
            if sp_info['type'] == 'store':
                h_cost = cfg.STORE_HOLDING_COST * price
            else:
                h_cost = cfg.FC_HOLDING_COST * price
            obj_terms.append(-h_cost * var)

        # --- Online order profit from active ship-from points ---
        for (order_id, sp_label), var in z.items():
            if sp_label == 'w':
                continue
            order   = next(o for o in all_orders if o.order_id == order_id)
            sp_info = supply_points[sp_label]
            l       = order.location

            if sp_info['type'] == 'store':
                s           = sp_info['index']
                t_cost      = inst.store_transport_costs[s, l]
                pick_cost   = inst.store_picking_costs[s] * order.total_items
            else:
                f           = sp_info['index']
                t_cost      = inst.fc_transport_costs[f, l]
                pick_cost   = inst.fc_picking_costs[f] * order.total_items

            profit_term = order.revenue - t_cost - pick_cost
            obj_terms.append(profit_term * var)

        # --- Online order profit from warehouse ---
        for (order_id, sp_label), var in z.items():
            if sp_label != 'w':
                continue
            order     = next(o for o in all_orders if o.order_id == order_id)
            l         = order.location
            t_cost    = inst.warehouse_transport_costs[l]
            pick_cost = inst.warehouse_picking_cost * order.total_items
            w_charge  = inst.warehouse_order_charge

            profit_term = order.revenue - w_charge - t_cost - pick_cost
            obj_terms.append(profit_term * var)

        model += pulp.lpSum(obj_terms), "Total_Profit"

        # -----------------------------------------------
        # CONSTRAINTS
        # -----------------------------------------------

        # --- Initial inventory (Section 5.1) ---
        # Paper: 5 units per product per store, 10 per FC at horizon start.
        # For activated stores that have day 0 as a replenishment day,
        # the replenishment quantity x[(sp,p,0)] supplements initial stock.
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue
            for p in range(P):
                if sp_info['type'] == 'store':
                    init_inv = cfg.INITIAL_INVENTORY_STORE
                else:
                    init_inv = cfg.INITIAL_INVENTORY_FC
                model += (
                    I[(sp_label, p, 0)] == init_inv,
                    f"InitInv_{sp_label}_{p}"
                )

        # --- Initial backlog = 0 ---
        # Backlog at t=0 is zero by definition (start of horizon).
        # The balance equations allow B to grow from t=1 onward
        # if physical demand exceeds available inventory.
        for sp_label in active_stores:
            for p in range(P):
                model += (
                    B[(sp_label, p, 0)] == 0,
                    f"InitBacklog_{sp_label}_{p}"
                )

        # --- Inventory balance constraints (Equations 5-8) ---
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue

            if sp_info['type'] == 'store':
                s        = sp_info['index']
                rep_days = set(inst.store_replenishment_periods[s])
            else:
                f        = sp_info['index']
                rep_days = set(inst.fc_replenishment_periods[f])

            for p in range(P):
                for t in range(T):
                    # Online demand consumed from this supply point on day t
                    online_demand = pulp.lpSum(
                        order.products.get(p, 0) * z[(order.order_id, sp_label)]
                        for order in scenario.orders_by_day.get(t, [])
                        if (order.order_id, sp_label) in z
                    )

                    if sp_info['type'] == 'store':
                        # Physical demand (with backlog carry-forward)
                        d_pst = scenario.physical_demand.get((p, s, t), 0)

                        if t in rep_days:
                            # Replenishment period (Equation 6):
                            # Paper: Ibar[t] + x[t] = Ibar[t+1] + d[t] + online[t]
                            # where Ibar = I - B
                            # Substituting: (I[t]-B[t]) + x[t] = (I[t+1]-B[t+1]) + d[t] + online[t]
                            # Rearranged:   I[t] + x[t] = I[t+1] - B[t+1] + B[t] + d[t] + online[t]
                            #
                            # x[t] here = x_online[t] + x_phys[t]
                            # x_phys is a known constant (sunk physical replenishment)
                            # x_online is the decision variable (incremental for online)
                            # Move x_phys to RHS as a known constant:
                            # I[t] + x_online[t] = I[t+1] - B[t+1] + B[t] + d[t] + online[t] - x_phys[t]
                            #x_phys_val = x_phys_baseline.get((s, p, t), 0.0)
                            model += (
                                I[(sp_label, p, t)] + x[(sp_label, p, t)]
                                - I[(sp_label, p, t + 1)]
                                + B[(sp_label, p, t + 1)]
                                - B[(sp_label, p, t)]
                                == online_demand
                                + d_pst,
                                #- x_phys_val,
                                f"InvBal_rep_{sp_label}_{p}_{t}"
                            )
                        else:
                            # Regular period (Equation 5):
                            # Paper: Ibar[t] = Ibar[t+1] + d[t] + online[t]
                            # Substituting: (I[t]-B[t]) = (I[t+1]-B[t+1]) + d[t] + online[t]
                            # Rearranged:   I[t] = I[t+1] - B[t+1] + B[t] + d[t] + online[t]
                            model += (
                                I[(sp_label, p, t)]
                                -I[(sp_label, p, t + 1)]
                                + B[(sp_label, p, t + 1)]
                                - B[(sp_label, p, t)]
                                == online_demand
                                + d_pst,
                                f"InvBal_reg_{sp_label}_{p}_{t}"
                            )
                    else:
                        # FC: no physical demand, no backlog (Equations 7-8)
                        if t in rep_days:
                            model += (
                                I[(sp_label, p, t)] + x[(sp_label, p, t)]
                                == I[(sp_label, p, t + 1)] + online_demand,
                                f"InvBal_fc_rep_{sp_label}_{p}_{t}"
                            )
                        else:
                            model += (
                                I[(sp_label, p, t)]
                                == I[(sp_label, p, t + 1)] + online_demand,
                                f"InvBal_fc_reg_{sp_label}_{p}_{t}"
                            )

        # --- Transportation capacity constraint (Equation 9) ---
        # k_t = 1.2 * avg_daily_demand * avg_rep_frequency
        # avg_daily_demand: total expected demand across all stores and products per day
        # avg_rep_frequency: average days between replenishments across all stores
        # The frequency adjustment accounts for trucks delivering a full cycle's
        # worth of inventory per trip, not one day's worth at a time.
        # The 20% residual above physical replenishment needs is available
        # for online channel incremental replenishment (Section 3.1).
        n_high = sum(1 for s in range(cfg.NUM_STORES)
                     if inst.store_category[s] == 'high')
        n_regular = cfg.NUM_STORES - n_high
        avg_rep_frequency = (
            cfg.REPLENISHMENT_FREQUENCY['regular'] * n_regular +
            cfg.REPLENISHMENT_FREQUENCY['high']    * n_high
        ) / cfg.NUM_STORES
        avg_daily_demand = inst.expected_physical_demand.sum()
        k_t = cfg.TRANSPORT_CAPACITY_MULTIPLIER * avg_daily_demand * avg_rep_frequency
        
        for t in range(T):
            rep_on_t = [
                x[(sp_label, p, t)]
                for (sp_label, p, t2) in x
                if t2 == t
            ]
            if rep_on_t:
                model += (
                    pulp.lpSum(rep_on_t) <= k_t,
                    f"TransportCap_{t}"
                )

        # --- Each order fulfilled at most once (Equation 10) ---
        # An order is assigned to at most one supply point.
        # Use enumerate for unique constraint naming to avoid PuLP conflicts.
        for idx, order in enumerate(all_orders):
            fulfillment_options = [
                z[(order.order_id, sp_label)]
                for sp_label in supply_points
                if (order.order_id, sp_label) in z
            ]
            if len(fulfillment_options) > 0:
                model += (
                    pulp.lpSum(fulfillment_options) <= 1,
                    f"OneAssign_{idx}"
                )

        # --- Capacity constraint at stores and FCs (Equation 11) ---
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue
            for t in range(T):
                orders_on_t = scenario.orders_by_day.get(t, [])
                assigned = [
                    z[(o.order_id, sp_label)]
                    for o in orders_on_t
                    if (o.order_id, sp_label) in z
                ]
                if assigned:
                    if sp_info['type'] == 'store':
                        s   = sp_info['index']
                        cap = scenario.store_capacity.get((s, t), 0)
                    else:
                        cap = cfg.FC_CAPACITY

                    model += (
                        pulp.lpSum(assigned) <= cap,
                        f"FulfillCap_{sp_label}_{t}"
                    )

        # --- Stock availability constraint (Equation 12) ---
        # Order o can only be assigned to supply point ς if all products
        # in the order are available in inventory.
        # On regular days:       consumption <= I[t]
        # On replenishment days: consumption <= I[t] + x[t]
        # Replenishment arrives and is available on the same day (Remark 3.2).
        for sp_label, sp_info in active_sps.items():
            if sp_info['type'] == 'warehouse':
                continue  # warehouse has unlimited inventory

            # Get replenishment days for this supply point
            if sp_info['type'] == 'store':
                s_idx    = sp_info['index']
                rep_days = set(inst.store_replenishment_periods[s_idx])
            else:
                f_idx    = sp_info['index']
                rep_days = set(inst.fc_replenishment_periods[f_idx])

            for t in range(T):
                orders_on_t = scenario.orders_by_day.get(t, [])
                for p in range(P):
                    # Total online consumption of product p on day t
                    total_consumption = pulp.lpSum(
                        order.products.get(p, 0) * z[(order.order_id, sp_label)]
                        for order in orders_on_t
                        if (order.order_id, sp_label) in z
                        and p in order.products
                    )
                    if not total_consumption:
                        continue

                    if t in rep_days and (sp_label, p, t) in x:
                        # Replenishment day: available stock = opening inventory + replenishment
                        model += (
                            total_consumption <= I[(sp_label, p, t)] + x[(sp_label, p, t)],
                            f"StockAvail_{sp_label}_{p}_{t}"
                        )
                    else:
                        # Regular day: available stock = opening inventory only
                        model += (
                            total_consumption <= I[(sp_label, p, t)],
                            f"StockAvail_{sp_label}_{p}_{t}"
                        )

        # -----------------------------------------------
        # SOLVE
        # -----------------------------------------------
        # Write model as MPS file for reliable integer variable handling
        # LP file format has known issues with binary variable declarations
        # in some PuLP/CBC version combinations
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.mps', delete=False) as tmp:
            mps_path = tmp.name
        model.writeMPS(mps_path)

        solver = pulp.PULP_CBC_CMD(
            msg=1 if verbose else 0,
            gapRel=cfg.OPTIMALITY_GAP,
            timeLimit=cfg.TIME_LIMIT_SEC,
            mip=True
        )
        model.solve(solver)

        # Clean up temp file
        try:
            os.unlink(mps_path)
        except:
            pass

        # Use sol_status to correctly identify if a feasible solution exists.
        # model.status reflects solver termination reason (can be 'Infeasible'
        # even when a feasible MIP solution was found before LP proved infeasible).
        # model.sol_status=1 means a feasible solution exists.
        if model.sol_status == 1:
            status = 'Optimal' if model.status == 1 else 'Feasible'
        else:
            status = pulp.LpStatus[model.status]
            # --- IIS Diagnostic: identify conflicting constraints ---
            if verbose:  # only print IIS diagnostic when verbose=True
                print("\n=== INFEASIBILITY DIAGNOSTIC ===")
                print("Checking for violated constraints...")
                violated = []
                for name, constraint in model.constraints.items():
                    slack = constraint.value()
                    if slack is not None and slack < -1e-6:
                        violated.append((name, slack))
                if violated:
                    print(f"Found {len(violated)} violated constraints:")
                    for name, slack in sorted(violated, key=lambda x: x[1])[:20]:
                        print(f"  {name}: slack={slack:.4f}")
                else:
                    print("No violated constraints found in solution")
                    print("Infeasibility may be in LP relaxation, not MIP solution")
                print("================================\n")

        # -----------------------------------------------
        # EXTRACT SOLUTION
        # -----------------------------------------------
        # Only extract solution if solver found a feasible solution
        if status not in ['Optimal', 'Feasible']:
            print(f"\nSolver status: {status} — no feasible solution found")
            print("Returning empty solution\n")
            return SubproblemSolution(
                profit=0.0, physical_revenue=0.0, online_revenue=0.0,
                backlog_cost=0.0, replenishment_cost=0.0, holding_cost=0.0,
                picking_cost=0.0, transport_cost=0.0, warehouse_cost=0.0,
                orders_fulfilled_store=0, orders_fulfilled_fc=0,
                orders_fulfilled_warehouse=0, orders_lost=len(scenario.orders),
                total_orders=len(scenario.orders),
                pct_lost=100.0, order_assignments={}, replenishment={},
                inventory={}, backlog={},
                sw_physical_cost_adjustment=sw_physical_cost_adjustment,
                status=status
            )

        return self._extract_solution(
            model, status, z, x, I, B,
            supply_points, scenario, inst,
            sw_physical_cost_adjustment=sw_physical_cost_adjustment
        )

    def _extract_solution(
        self, model, status, z, x, I, B,
        supply_points, scenario, inst,
        sw_physical_cost_adjustment: float = 0.0
    ) -> SubproblemSolution:
        """Extract and summarize the optimal solution."""

        T = cfg.NUM_PERIODS
        P = cfg.NUM_PRODUCTS

        # --- Order assignments ---
        order_assignments: Dict[str, str] = {}
        orders_store     = 0
        orders_fc        = 0
        orders_warehouse = 0
        orders_lost      = 0
        online_revenue   = 0.0
        transport_cost   = 0.0
        picking_cost     = 0.0
        warehouse_cost   = 0.0

        assigned_order_ids = set()

        # First pass: collect all assignments (guard against double assignment)
        raw_assignments: Dict[str, str] = {}
        for (order_id, sp_label), var in z.items():
            if pulp.value(var) is not None and pulp.value(var) > 0.5:
                if order_id not in raw_assignments:
                    raw_assignments[order_id] = sp_label
                else:
                    # Double assignment detected - keep store/FC over warehouse
                    existing = raw_assignments[order_id]
                    if supply_points[existing]['type'] == 'warehouse':
                        raw_assignments[order_id] = sp_label

        # Second pass: count and compute costs from clean assignments
        for order_id, sp_label in raw_assignments.items():
            order_assignments[order_id] = sp_label
            assigned_order_ids.add(order_id)
            order = next(
                o for o in scenario.orders if o.order_id == order_id
            )
            sp_info = supply_points[sp_label]
            l = order.location

            online_revenue += order.revenue

            if sp_info['type'] == 'store':
                orders_store += 1
                s = sp_info['index']
                transport_cost += inst.store_transport_costs[s, l]
                picking_cost   += inst.store_picking_costs[s] * order.total_items
            elif sp_info['type'] == 'fc':
                orders_fc += 1
                f = sp_info['index']
                transport_cost += inst.fc_transport_costs[f, l]
                picking_cost   += inst.fc_picking_costs[f] * order.total_items
            elif sp_info['type'] == 'warehouse':
                orders_warehouse += 1
                transport_cost += inst.warehouse_transport_costs[l]
                picking_cost   += inst.warehouse_picking_cost * order.total_items
                warehouse_cost += inst.warehouse_order_charge

        orders_lost  = len(scenario.orders) - len(assigned_order_ids)
        total_orders = len(scenario.orders)
        pct_lost     = orders_lost / total_orders * 100 if total_orders > 0 else 0

        # --- Replenishment ---
        replenishment: Dict[Tuple, float] = {}
        replenishment_cost = 0.0
        for (sp_label, p, t), var in x.items():
            val = pulp.value(var) or 0.0
            if val > 1e-6:
                replenishment[(sp_label, p, t)] = val
                sp_info = supply_points[sp_label]
                price   = inst.product_prices[p]
                if sp_info['type'] == 'store':
                    replenishment_cost += cfg.STORE_REPLENISHMENT_COST * price * val
                else:
                    replenishment_cost += cfg.FC_REPLENISHMENT_COST * price * val

        # --- Inventory ---
        inventory: Dict[Tuple, float] = {}
        holding_cost = 0.0
        for (sp_label, p, t), var in I.items():
            val = pulp.value(var) or 0.0
            if val > 1e-6:
                inventory[(sp_label, p, t)] = val
                if t < T:
                    sp_info = supply_points[sp_label]
                    price   = inst.product_prices[p]
                    if sp_info['type'] == 'store':
                        holding_cost += cfg.STORE_HOLDING_COST * price * val
                    else:
                        holding_cost += cfg.FC_HOLDING_COST * price * val

        # --- Backlog and Physical Revenue (ALL stores) ---
        backlog: Dict[Tuple, float] = {}
        backlog_cost     = 0.0
        physical_revenue = 0.0

        all_store_sps = {
            k: v for k, v in supply_points.items()
            if v['type'] == 'store'
        }
        for sp_label, sp_info in all_store_sps.items():
            s = sp_info['index']
            for p in range(P):
                price = inst.product_prices[p]
                for t in range(T):
                    d_pst = scenario.physical_demand.get((p, s, t), 0)
                    if sp_info['active']:
                        # Activated store: revenue net of NEW backlog in period t
                        b_next = pulp.value(B.get((sp_label, p, t + 1))) or 0.0
                        b_curr = pulp.value(B.get((sp_label, p, t))) or 0.0
                        physical_revenue += price * (d_pst - (b_next - b_curr))
                        backlog_cost     += cfg.STORE_BACKLOGGING_COST * price * b_curr
                        if b_next > 1e-6:
                            backlog[(sp_label, p, t + 1)] = b_next
                    else:
                        # Non-activated store: full physical revenue
                        physical_revenue += price * d_pst

        profit = (pulp.value(model.objective) or 0.0) - sw_physical_cost_adjustment

        return SubproblemSolution(
            profit=profit,
            physical_revenue=physical_revenue,
            online_revenue=online_revenue,
            backlog_cost=backlog_cost,
            replenishment_cost=replenishment_cost,
            holding_cost=holding_cost,
            picking_cost=picking_cost,
            transport_cost=transport_cost,
            warehouse_cost=warehouse_cost,
            orders_fulfilled_store=orders_store,
            orders_fulfilled_fc=orders_fc,
            orders_fulfilled_warehouse=orders_warehouse,
            orders_lost=orders_lost,
            total_orders=total_orders,
            pct_lost=pct_lost,
            order_assignments=order_assignments,
            replenishment=replenishment,
            inventory=inventory,
            backlog=backlog,
            sw_physical_cost_adjustment=sw_physical_cost_adjustment,
            status=status
        )


# ------------------------------------------------------------
# MAIN — run directly to test subproblem in isolation
# Manually fix y and solve for scenario 0
# ------------------------------------------------------------

if __name__ == "__main__":
    from scenario_generator import InstanceData, ScenarioGenerator

    print("=" * 60)
    print("SUBPROBLEM VALIDATION")
    print("Testing Q(y, omega) for a fixed y and scenario 0")
    print("=" * 60)

    # --- Generate instance and scenarios ---
    instance  = InstanceData(seed=cfg.RANDOM_SEED)
    generator = ScenarioGenerator(instance, seed=cfg.RANDOM_SEED)
    scenarios = generator.generate(n_scenarios=1)  # one scenario for testing
    scenario  = scenarios[0]

    print(f"\nScenario 0: {len(scenario.orders)} orders over {cfg.NUM_PERIODS} days")

    # --- Compute SW physical cost adjustment ---
    # This is computed ONCE from all scenarios and applied as a fixed constant.
    # Here we use only the 1 validation scenario; in production use all N scenarios.
    sw_adjustment = compute_sw_physical_cost_adjustment(scenarios, instance)
    print(f"\nSW Physical Cost Adjustment (expected): ${sw_adjustment:,.2f}")
    print("  (= expected store replenishment + holding costs missing from SW MIP)")

    # --- Test 1: SW strategy (warehouse only) ---
    print("\n--- Strategy: SW (warehouse only) ---")
    y_sw   = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
    solver = SubproblemSolver(instance)

    # Solve WITHOUT adjustment (original paper approach)
    sol_sw_orig = solver.solve(y_sw, scenario, verbose=False,
                               sw_physical_cost_adjustment=0.0)
    # Solve WITH adjustment (corrected approach)
    sol_sw_adj  = solver.solve(y_sw, scenario, verbose=False,
                               sw_physical_cost_adjustment=sw_adjustment)

    print(f"Status                    : {sol_sw_orig.status}")
    print(f"Profit (original)         : ${sol_sw_orig.profit:,.2f}")
    print(f"Profit (adjusted)         : ${sol_sw_adj.profit:,.2f}")
    print(f"Adjustment applied        : -${sw_adjustment:,.2f}")
    print(f"Online Revenue            : ${sol_sw_orig.online_revenue:,.2f}")
    print(f"Physical Revenue          : ${sol_sw_orig.physical_revenue:,.2f}")
    print("--- Costs (original MIP) ---")
    print(f"Backlog Cost              : ${sol_sw_orig.backlog_cost:,.2f}")
    print(f"Replenish Cost            : ${sol_sw_orig.replenishment_cost:,.2f}  ← zero (not modeled)")
    print(f"Holding Cost              : ${sol_sw_orig.holding_cost:,.2f}  ← zero (not modeled)")
    print(f"Picking Cost              : ${sol_sw_orig.picking_cost:,.2f}")
    print(f"Transport Cost            : ${sol_sw_orig.transport_cost:,.2f}")
    print(f"Warehouse Charge          : ${sol_sw_orig.warehouse_cost:,.2f}")
    print("--- Fulfillment ---")
    print(f"Orders -> Store           : {sol_sw_orig.orders_fulfilled_store}")
    print(f"Orders -> FC              : {sol_sw_orig.orders_fulfilled_fc}")
    print(f"Orders -> WH              : {sol_sw_orig.orders_fulfilled_warehouse}")
    print(f"Orders Lost               : {sol_sw_orig.orders_lost} ({sol_sw_orig.pct_lost:.1f}%)")

    # --- Test 2: SS strategy (activate Store 3 — high traffic) ---
    print("\n--- Strategy: SS (Store 3 activated) ---")
    y_ss = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
    y_ss[3] = 1  # activate Store 3
    # SS needs NO adjustment — its MIP already includes physical costs via shared inventory
    sol_ss = solver.solve(y_ss, scenario, verbose=False,
                          sw_physical_cost_adjustment=0.0)
    print(f"Status                    : {sol_ss.status}")
    print(f"Profit                    : ${sol_ss.profit:,.2f}")
    print(f"Online Revenue            : ${sol_ss.online_revenue:,.2f}")
    print(f"Physical Revenue          : ${sol_ss.physical_revenue:,.2f}")
    print("--- Costs ---")
    print(f"Backlog Cost              : ${sol_ss.backlog_cost:,.2f}")
    print(f"Replenish Cost            : ${sol_ss.replenishment_cost:,.2f}  ← includes physical demand")
    print(f"Holding Cost              : ${sol_ss.holding_cost:,.2f}")
    print(f"Picking Cost              : ${sol_ss.picking_cost:,.2f}")
    print(f"Transport Cost            : ${sol_ss.transport_cost:,.2f}")
    print(f"Warehouse Charge          : ${sol_ss.warehouse_cost:,.2f}")
    print("--- Fulfillment ---")
    print(f"Orders -> Store           : {sol_ss.orders_fulfilled_store}")
    print(f"Orders -> FC              : {sol_ss.orders_fulfilled_fc}")
    print(f"Orders -> WH              : {sol_ss.orders_fulfilled_warehouse}")
    print(f"Orders Lost               : {sol_ss.orders_lost} ({sol_ss.pct_lost:.1f}%)")

    # --- Comparison: before and after correction ---
    print("\n--- Profit Comparison ---")
    print(f"{'':30s} {'Original':>15s} {'Corrected':>15s}")
    print(f"{'SW Profit':30s} ${sol_sw_orig.profit:>14,.2f} ${sol_sw_adj.profit:>14,.2f}")
    print(f"{'SS Profit':30s} ${sol_ss.profit:>14,.2f} ${sol_ss.profit:>14,.2f}")
    gap_orig = sol_ss.profit - sol_sw_orig.profit
    gap_adj  = sol_ss.profit - sol_sw_adj.profit
    print(f"{'SS - SW gap':30s} ${gap_orig:>14,.2f} ${gap_adj:>14,.2f}")
    print()
    if gap_adj > gap_orig:
        print("RESULT: Correction WIDENS the SS advantage over SW.")
        print("        SW was overstated in the original paper formulation.")
    elif gap_adj < gap_orig:
        print("RESULT: Correction NARROWS the SS advantage over SW.")
    else:
        print("RESULT: Correction has no effect on relative ranking.")

    # --- Sanity checks ---
    print("\n--- Sanity Checks ---")
    if sol_ss.orders_fulfilled_store + sol_ss.orders_fulfilled_warehouse >= \
       sol_sw_orig.orders_fulfilled_warehouse:
        print("PASS: SS fulfills at least as many orders as SW")
    else:
        print("WARN: SS fulfills fewer orders than SW — check assignment logic")

    if sol_ss.pct_lost <= sol_sw_orig.pct_lost:
        print("PASS: SS lost sales % <= SW lost sales %")
    else:
        print("INFO: SS lost sales % > SW — may reflect high physical replenishment"
              " cost making store activation unprofitable at this y configuration")

    print("\nSubproblem validation complete.")

