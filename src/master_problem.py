# master_problem.py
# ============================================================
# Stage 1 Master Problem: Network Deployment Decisions
# ============================================================
# Decides which stores and FCs to activate as ship-from points
# to maximize expected profit across all N scenarios.
#
# Objective:
#   max  (1/N) * sum_omega Q(y, omega) - sum_ς f_ς * y_ς
#
# Where:
#   y_ς  — binary: activate supply point ς (store or FC)
#   f_ς  — fixed annual cost of activating ς
#   Q(y, omega) — Stage 2 optimal profit for network y, scenario omega
#
# Solution approach:
#   Full enumeration for small instances (City1: 2^5 * 2^1 = 64 configs)
#   Integer L-shaped method for larger instances (l_shaped.py)
#
# Reference: Arslan, Klibi & Montreuil (2021), Section 3.3
#            Equations (1) - (3)
# ============================================================

import numpy as np
import itertools
from dataclasses import dataclass
from typing import Dict, List
import time

import config as cfg
from scenario_generator import InstanceData, Scenario, ScenarioGenerator
from subproblem import SubproblemSolver, SubproblemSolution, compute_sw_physical_cost_adjustment


# ------------------------------------------------------------
# SOLUTION DATA STRUCTURE
# ------------------------------------------------------------

@dataclass
class MasterSolution:
    """Holds the optimal Stage 1 network deployment decision."""

    # Optimal deployment
    y:                   Dict[int, int]     # {supply_point_index: 0/1}
    activated_stores:    List[int]          # store indices activated
    activated_fcs:       List[int]          # FC indices activated

    # Objective components
    expected_profit:     float              # (1/N) * sum Q(y, omega)
    fixed_cost:          float              # sum f_ς * y_ς
    total_profit:        float              # expected_profit - fixed_cost

    # SW fairness correction applied (0.0 for SS and SF)
    sw_physical_cost_adjustment: float

    # Per-scenario results
    scenario_profits:    List[float]        # Q(y, omega) for each omega
    scenario_solutions:  List[SubproblemSolution]

    # Performance statistics
    avg_lost_pct:        float
    avg_online_revenue:  float
    avg_backlog_cost:    float

    # Solver metadata
    n_configs_evaluated: int
    solve_time_sec:      float
    strategy:            str               # 'SW', 'SS', or 'SF'


# ------------------------------------------------------------
# STRATEGY HELPERS
# ------------------------------------------------------------

def get_strategy_label(y: Dict[int, int]) -> str:
    """Classify deployment y as SW, SS, or SF."""
    any_store = any(y.get(s, 0) for s in range(cfg.NUM_STORES))
    any_fc    = any(y.get(cfg.NUM_STORES + f, 0) for f in range(cfg.NUM_FCS))

    if not any_store and not any_fc:
        return 'SW'
    elif any_store and not any_fc:
        return 'SS'
    else:
        return 'SF'


def compute_fixed_cost(y: Dict[int, int], instance: InstanceData) -> float:
    """
    Compute total fixed deployment cost for configuration y.
    Fixed costs are annual costs amortized over the planning horizon.
    Reference: Section 3.3, Equation (1)
    """
    cost = 0.0
    for s in range(cfg.NUM_STORES):
        if y.get(s, 0):
            cost += instance.store_fixed_costs[s]
    for f in range(cfg.NUM_FCS):
        idx = cfg.NUM_STORES + f
        if y.get(idx, 0):
            cost += cfg.FC_USAGE_COST
    return cost


def enumerate_configurations(strategy: str) -> List[Dict[int, int]]:
    """
    Enumerate all valid y configurations for a given strategy.

    SW: no stores, no FCs activated — single configuration
    SS: all non-empty subsets of stores, no FCs
    SF: all non-empty subsets of stores, FC activated
        (paper assumes at most one FC per city)
    """
    configs = []
    store_indices = list(range(cfg.NUM_STORES))
    #fc_indices    = list(range(cfg.NUM_STORES, cfg.NUM_STORES + cfg.NUM_FCS))

    if strategy == 'SW':
        y = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
        configs.append(y)

    elif strategy == 'SS':
        # All non-empty subsets of stores with at most s_max stores activated
        # Equation (2): sum_{ς in SF} y_ς <= s_max
        for r in range(1, cfg.S_MAX + 1):
            for subset in itertools.combinations(store_indices, r):
                y = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
                for s in subset:
                    y[s] = 1
                configs.append(y)

    elif strategy == 'SF':
        # FC counts toward s_max, so stores can use at most s_max - 1 slots.
        # Also include FC-only config (0 stores + FC) as a valid configuration.
        # Equation (2): sum_{ς in SF} y_ς <= s_max
        max_stores_with_fc = cfg.S_MAX - cfg.NUM_FCS  # slots remaining after FC
        # FC-only: no stores activated
        y_fc_only = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
        y_fc_only[cfg.NUM_STORES] = 1
        configs.append(y_fc_only)
        # Stores + FC combinations
        for r in range(1, max_stores_with_fc + 1):
            for subset in itertools.combinations(store_indices, r):
                y = {i: 0 for i in range(cfg.NUM_STORES + cfg.NUM_FCS)}
                for s in subset:
                    y[s] = 1
                # Activate first FC
                y[cfg.NUM_STORES] = 1
                configs.append(y)

    return configs


# ------------------------------------------------------------
# MASTER PROBLEM SOLVER
# ------------------------------------------------------------

class MasterProblemSolver:
    """
    Solves the Stage 1 master problem by evaluating Q(y, omega)
    for each candidate deployment y across all N scenarios.

    For City1 (5 stores, 1 FC):
      SW:  1 configuration
      SS:  2^5 - 1 = 31 configurations
      SF:  31 configurations (same stores + FC)
      Total: 63 configurations * 50 scenarios = 3,150 subproblem solves

    Uses full enumeration. For larger instances, use l_shaped.py.
    """

    def __init__(self, instance: InstanceData, scenarios: List[Scenario]):
        self.instance  = instance
        self.scenarios = scenarios
        self.subproblem_solver = SubproblemSolver(instance)

    def solve(
        self,
        strategy: str,
        verbose: bool = False,
        progress: bool = True
    ) -> MasterSolution:
        """
        Find the optimal deployment y for a given strategy.

        Parameters
        ----------
        strategy : 'SW', 'SS', or 'SF'
        verbose  : print subproblem solver output
        progress : print progress updates

        Returns
        -------
        MasterSolution with optimal y and all scenario results
        """
        t_start = time.time()
        N       = len(self.scenarios)

        # Compute SW physical cost adjustment ONCE from all scenarios.
        # This is a fixed constant subtracted from every SW scenario profit
        # to make the cost basis comparable with SS and SF.
        # For SS and SF, this adjustment is 0.0 — their MIPs already
        # bear physical replenishment and holding costs via shared inventory.
        if strategy == 'SW':
            sw_adjustment = compute_sw_physical_cost_adjustment(
                self.scenarios, self.instance
            )
            if progress:
                print(f"  SW physical cost adjustment: ${sw_adjustment:,.2f} "
                      f"(subtracted from each scenario profit)")
        else:
            sw_adjustment = 0.0

        # Get all candidate configurations
        configs = enumerate_configurations(strategy)

        if progress:
            print(f"Strategy {strategy}: evaluating {len(configs)} configurations "
                  f"× {N} scenarios = {len(configs) * N} subproblem solves")

        best_total_profit   = -np.inf
        best_y              = None
        best_scenario_profs = None
        best_scenario_sols  = None
        best_fixed_cost     = None

        for c_idx, y in enumerate(configs):
            fixed_cost     = compute_fixed_cost(y, self.instance)
            scenario_profs = []
            scenario_sols  = []

            for omega_idx, scenario in enumerate(self.scenarios):
                sol = self.subproblem_solver.solve(
                    y, scenario, verbose=verbose,
                    sw_physical_cost_adjustment=sw_adjustment
                )
                scenario_profs.append(sol.profit)
                scenario_sols.append(sol)

            # Expected Stage 2 profit across scenarios
            expected_profit = np.mean(scenario_profs)

            # Total profit = expected Stage 2 - fixed deployment cost
            total_profit = expected_profit - fixed_cost

            if progress and (c_idx + 1) % 5 == 0:
                activated = [s for s in range(cfg.NUM_STORES) if y.get(s, 0)]
                print(f"  Config {c_idx+1}/{len(configs)}: "
                      f"stores={activated}, "
                      f"total_profit=${total_profit:,.0f}")

            if total_profit > best_total_profit:
                best_total_profit   = total_profit
                best_y              = y.copy()
                best_scenario_profs = scenario_profs.copy()
                best_scenario_sols  = scenario_sols.copy()
                best_fixed_cost     = fixed_cost

        solve_time = time.time() - t_start

        # Compute summary statistics from best configuration
        avg_lost    = np.mean([s.pct_lost for s in best_scenario_sols])
        avg_online  = np.mean([s.online_revenue for s in best_scenario_sols])
        avg_backlog = np.mean([s.backlog_cost for s in best_scenario_sols])

        activated_stores = [s for s in range(cfg.NUM_STORES)
                           if best_y.get(s, 0)]
        activated_fcs    = [f for f in range(cfg.NUM_FCS)
                           if best_y.get(cfg.NUM_STORES + f, 0)]

        return MasterSolution(
            y=best_y,
            activated_stores=activated_stores,
            activated_fcs=activated_fcs,
            expected_profit=np.mean(best_scenario_profs),
            fixed_cost=best_fixed_cost,
            total_profit=best_total_profit,
            sw_physical_cost_adjustment=sw_adjustment,
            scenario_profits=best_scenario_profs,
            scenario_solutions=best_scenario_sols,
            avg_lost_pct=avg_lost,
            avg_online_revenue=avg_online,
            avg_backlog_cost=avg_backlog,
            n_configs_evaluated=len(configs),
            solve_time_sec=solve_time,
            strategy=strategy
        )

    def solve_all_strategies(
        self,
        progress: bool = True
    ) -> Dict[str, MasterSolution]:
        """
        Solve SW, SS, and SF strategies and return all three solutions.
        This replicates the paper's Table 6/7/8 experiment structure.
        """
        results = {}
        for strategy in ['SW', 'SS', 'SF']:
            if progress:
                print(f"\n{'='*50}")
                print(f"Solving strategy: {strategy}")
                print(f"{'='*50}")
            results[strategy] = self.solve(strategy, progress=progress)

        return results


# ------------------------------------------------------------
# MAIN — run directly to test master problem
# Solves SW baseline and SS with N=5 scenarios for speed
# ------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("MASTER PROBLEM VALIDATION")
    print("Comparing SW vs SS strategies")
    print("=" * 60)

    # Use small N for validation speed
    N_VALIDATION = 5

    instance  = InstanceData(seed=cfg.RANDOM_SEED)
    generator = ScenarioGenerator(instance, seed=cfg.RANDOM_SEED)
    scenarios = generator.generate(n_scenarios=N_VALIDATION)

    print(f"\nInstance : {cfg.CITY}, {cfg.RESPONSE_TIME_EXPECTATION} RE, "
          f"{cfg.DEMAND_RATIO} DR")
    print(f"Scenarios: {N_VALIDATION} (paper uses {cfg.N_SCENARIOS})")
    print(f"Stores   : {cfg.NUM_STORES}, FCs: {cfg.NUM_FCS}")

    solver = MasterProblemSolver(instance, scenarios)

    # --- Solve SW ---
    print("\n--- Solving SW ---")
    sol_sw = solver.solve('SW', progress=True)
    print("\nSW Results:")
    print(f"  Total Profit          : ${sol_sw.total_profit:,.2f}")
    print(f"  Expected Q(y,ω)       : ${sol_sw.expected_profit:,.2f}")
    print(f"  Fixed Cost            : ${sol_sw.fixed_cost:,.2f}")
    print(f"  SW Physical Adjustment: -${sol_sw.sw_physical_cost_adjustment:,.2f}")
    print(f"  Avg Lost Orders       : {sol_sw.avg_lost_pct:.1f}%")
    print(f"  Solve Time            : {sol_sw.solve_time_sec:.1f}s")

    # --- Solve SS ---
    print("\n--- Solving SS ---")
    sol_ss = solver.solve('SS', progress=True)
    activated_labels = [
        f"Store {s} ({instance.store_category[s]})"
        for s in sol_ss.activated_stores
    ]
    print("\nSS Results:")
    print(f"  Optimal Network : {activated_labels}")
    print(f"  Total Profit    : ${sol_ss.total_profit:,.2f}")
    print(f"  Expected Q(y,ω) : ${sol_ss.expected_profit:,.2f}")
    print(f"  Fixed Cost      : ${sol_ss.fixed_cost:,.2f}")
    print(f"  Avg Lost Orders : {sol_ss.avg_lost_pct:.1f}%")
    print(f"  Solve Time      : {sol_ss.solve_time_sec:.1f}s")

    # --- Compare ---
    print("\n--- Comparison ---")
    profit_gain = sol_ss.total_profit - sol_sw.total_profit
    lost_reduction = sol_sw.avg_lost_pct - sol_ss.avg_lost_pct
    print(f"  Profit gain SS vs SW : ${profit_gain:,.2f}")
    print(f"  Lost sales reduction : {lost_reduction:.1f} ppts")

    if sol_ss.total_profit >= sol_sw.total_profit:
        print("  PASS: SS >= SW in total profit")
    else:
        print("  INFO: SW outperforms SS — store activation costs exceed online gains")
        print("        This is possible for high fixed cost / low demand ratio instances")

    print("\nMaster problem validation complete.")
