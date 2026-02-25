# Distribution Network Optimization for Omnichannel Retail

## Business Question

As e-commerce demand grows, our existing distribution network — built for bulk store replenishment — is increasingly unable to fulfill online orders profitably and on time. The central warehouse is too far from urban customers to meet next-day delivery expectations, stores were never designed for order picking, and transportation capacity is already under pressure.

**The question this project answers:** Given our existing network, what is the optimal way to reconfigure it — repurposing stores as fulfillment points, opening urban fulfillment centers, or both — to serve online and in-store customers profitably as e-commerce scales?

---

## What We Found

Activating existing stores as ship-from fulfillment points delivers **immediate, significant gains** — reducing lost online sales by more than 50% and increasing online revenue substantially, without opening any new infrastructure. This should be the first move.

Urban fulfillment centers are not always the answer. They only justify their cost when online demand is high *and* the majority of customers expect next-day delivery simultaneously. In most scenarios, one well-placed urban fulfillment center is sufficient — a network of them is not necessary.

The binding constraint in most cases is not how many fulfillment locations we have, but **store capacity and replenishment dynamics**. When store replenishment schedules overlap, inbound transportation capacity becomes saturated, and online fulfillment suffers regardless of how many locations are activated. Omnichannel integration strains the distribution network in ways that are not visible until modeled explicitly.

The distance between the central warehouse and the city is not just a logistics variable — **it is a revenue variable**. When the warehouse cannot offer next-day delivery due to distance, the pressure to restructure the network increases sharply, and the cost of inaction compounds with every percentage point of customers who expect faster delivery.

---

## Recommendations

| Business Situation | Recommended Action |
|---|---|
| Low online demand, flexible delivery expectations | Activate 1–2 stores for fulfillment. No urban FC needed. |
| Moderate online demand, mixed delivery expectations | Activate 2–3 stores. Monitor capacity utilization before committing to an FC. |
| High online demand, majority expecting next-day delivery | Activate stores plus open one urban FC. |
| Inbound transportation already near capacity | Revisit replenishment schedules before activating ship-from-store. The bottleneck is inbound, not outbound. |

---

## Approach

Deployment decisions — which stores to activate, whether to open an urban fulfillment center — must be made before online demand fully materializes. Optimizing for a single demand forecast is insufficient; the right network structure must perform well across a range of plausible futures.

This project models the problem as a **two-stage stochastic program**: network configuration decisions are made in Stage 1 before uncertainty is resolved, and operational decisions (order assignment, replenishment quantities, inventory levels) are made in Stage 2 after demand is observed. The model is solved across 18 demand scenarios combining city size, customer delivery expectations, and online-to-physical demand ratios.

Three network strategies are evaluated:

| Strategy | Description |
|---|---|
| **Ship-from Warehouse (SW)** | Baseline. All online orders fulfilled from the central warehouse. |
| **Ship-from Stores (SS)** | Selected existing stores repurposed as e-commerce fulfillment points. |
| **Ship-from Fulfillment Platforms (SF)** | Stores plus a dedicated urban fulfillment center. |

Sensitivity analysis stress-tests four variables: store fulfillment capacity, the maximum number of ship-from locations, replenishment schedule flexibility, and urban FC usage cost — to identify which levers most significantly affect network performance and under what conditions the recommended strategy changes.

---

## Model Structure

**Decision Variables**

| Variable | Description |
|---|---|
| `y_ς` | Whether ship-from point ς is activated (store or FC) |
| `z^o_ς(ω)` | Whether order `o` is fulfilled from supply point ς under scenario ω |
| `x^p_ςt(ω)` | Units of product `p` replenished to ship-from point ς on day `t` under scenario ω |
| `I^p_ςt(ω)` | Inventory level of product `p` at ship-from point ς at start of period `t` |
| `B^p_st(ω)` | Backlog of product `p` at store `s` at start of period `t` |

**Objective:** Maximize total expected profit — revenues from physical and online sales minus fixed activation costs, replenishment, inventory holding, backlogging, transportation, and picking costs.

**Key Constraints**
- Inventory balance at stores and fulfillment centers each period
- Transportation capacity on inbound replenishment flows
- Each online order fulfilled at most once, within its requested response time
- Fulfillment capacity limits at stores and urban FCs
- Stock availability — all items in an order must be in stock at the assigned location

---

## Repository Structure

```
├── data/
│   ├── raw/                     # Instance generation inputs
│   └── scenarios/               # Monte Carlo generated scenario sets
├── model/
│   ├── stage1.py                # Stage 1: network deployment decisions
│   ├── stage2.py                # Stage 2: order fulfillment subproblem
│   └── l_shaped.py              # Integer L-shaped solution algorithm
├── analysis/
│   ├── scenario_analysis.py     # Network performance across demand futures
│   └── sensitivity.py           # Parameter sensitivity experiments
├── results/
│   ├── network_structures/      # Optimal configurations by scenario
│   └── figures/                 # Inventory, capacity, and cost visualizations
└── notebooks/
    └── results_walkthrough.ipynb
```

---

## Reference

Arslan, A. N., Klibi, W., & Montreuil, B. (2021). Distribution network deployment for omnichannel retailing. *European Journal of Operational Research, 294*(3), 1042–1058.
