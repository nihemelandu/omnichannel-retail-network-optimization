# Two-Stage Stochastic Programming Model for e-DND

## Problem Objective
Maximize expected profit by selecting optimal fulfillment platform locations (Stage 1) while anticipating operational costs and revenues under demand uncertainty (Stage 2).

---

## Mathematical Formulation

### Stage 1: Deployment Decisions

**Objective Function:**
```
max  -∑_{ς∈SF} c^f_ς y_ς + E_Ω[Q(y, ω)]
```

**Subject to:**
```
∑_{ς∈SF} y_ς ≤ s_max                    (Maximum number of ship-from points)
y_ς ∈ {0,1}  ∀ς ∈ SF                     (Binary deployment decisions)
```

**Note:** The warehouse w is always operational and does not require a deployment decision. Only ship-from points ς ∈ SF = S ∪ F have associated binary variables y_ς.

---

### Stage 2: Operational Decisions for Scenario ω

**Recourse Function Q(y, ω):**
```
Q(y, ω) = max  
    /* PHYSICAL CHANNEL REVENUE */
    ∑_{s∈S} ∑_{p∈P} ∑_{t∈T} π_p(d^p_{st}(ω) - B^p_{s(t+1)}(ω))
    
    /* ONLINE CHANNEL REVENUE */
    + ∑_{t∈T} ∑_{l∈L} ∑_{o∈Õ_{lt}(ω)} ∑_{ς∈SF} (π_o(ω) - c^t_{ςl} - c^p_ς n_o(ω)) z^o_ς(ω)     [From ship-from points]
    + ∑_{t∈T} ∑_{l∈L} ∑_{o∈Õ_{lt}(ω)} (π_o(ω) - c_{wo} - c^t_{wl} - c^p_w n_o(ω)) z^o_w(ω)     [From warehouse]
    
    /* OPERATIONAL COSTS */
    - ∑_{s∈S} ∑_{t∈T} ∑_{p∈P} c^b_{ps} B^p_{st}(ω)                [Backlog costs]
    - ∑_{ς∈SF} ∑_{t∈τ_ς} ∑_{p∈P} c^r_{pς} x^p_{ςt}(ω)            [Replenishment costs]
    - ∑_{ς∈SF} ∑_{t∈T} ∑_{p∈P} c^h_{pς} I^p_{ςt}(ω)              [Holding costs]
```

**Subject to:**

**Inventory Balance Constraints (Stores - Non-replenishment periods):**
```
Ī^p_{st}(ω) = Ī^p_{s(t+1)}(ω) + d^p_{st}(ω) + ∑_{o∈Õ_t(ω)} n^o_p(ω) z^o_s(ω)     ∀s∈S, t∈T\τ_s, p∈P
```
where Ī^p_{st}(ω) = I^p_{st}(ω) - B^p_{st}(ω) (net inventory)

**Inventory Balance Constraints (Stores - Replenishment periods):**
```
Ī^p_{st}(ω) + x^p_{st}(ω) = Ī^p_{s(t+1)}(ω) + d^p_{st}(ω) + ∑_{o∈Õ_t(ω)} n^o_p(ω) z^o_s(ω)     ∀s∈S, t∈τ_s, p∈P
```

**Inventory Balance Constraints (FCs - Non-replenishment periods):**
```
I^p_{ft}(ω) = I^p_{f(t+1)}(ω) + ∑_{o∈Õ_t(ω)} n^o_p(ω) z^o_f(ω)     ∀f∈F, t∈T\τ_f, p∈P
```

**Inventory Balance Constraints (FCs - Replenishment periods):**
```
I^p_{ft}(ω) + x^p_{ft}(ω) = I^p_{f(t+1)}(ω) + ∑_{o∈Õ_t(ω)} n^o_p(ω) z^o_f(ω)     ∀f∈F, t∈τ_f, p∈P
```

**Transportation Capacity:**
```
∑_{ς∈SF|t∈τ_ς} ∑_{p∈P} x^p_{ςt}(ω) ≤ k_t     ∀t∈T
```

**Order Assignment (at most once, respecting response time):**
```
∑_{ς∈SP|r_{ςl}≤η_o(ω)} z^o_ς(ω) ≤ 1     ∀o∈Õ(ω)
```
where SP = SF ∪ {w} (ship-from points + warehouse)

**Fulfillment Capacity:**
```
∑_{o∈Õ_t(ω)} z^o_ς(ω) ≤ b_{ςt}(ω) y_ς     ∀ς∈SF, t∈T
```
**Note:** This constraint only applies to ship-from points (not warehouse), linking Stage 2 fulfillment to Stage 1 deployment decisions.

**Inventory Availability (orders can only be fulfilled if inventory exists):**
```
n^o_p(ω) z^o_ς(ω) ≤ I^p_{ςt}(ω) - ∑_{o'∈Õ_t(ω)≺o} n^{o'}_p(ω) z^{o'}_ς(ω)     ∀ς∈SF, t∈T, o∈Õ_t(ω), p∈P(o)
```

**Variable Domains:**
```
z^o_ς(ω) ∈ {0,1}     ∀o∈Õ(ω), ς∈SP
x^p_{ςt}(ω) ≥ 0      ∀p∈P, ς∈SF, t∈T
I^p_{ςt}(ω) ≥ 0      ∀p∈P, ς∈SF, t∈T
B^p_{st}(ω) ≥ 0      ∀p∈P, s∈S, t∈T
```

---

## Decision Variables

### Stage 1 (Here-and-Now):
- **y_ς**: Binary variable = 1 if ship-from point ς is deployed for online fulfillment, 0 otherwise
  - Decided **before** uncertainty is realized
  - Same value across all scenarios
  - Only defined for ς ∈ SF (stores and FCs, not warehouse)

### Stage 2 (Wait-and-See) for each scenario ω:
- **z^o_ς(ω)**: Binary variable = 1 if order o is fulfilled from supply point ς under scenario ω, 0 otherwise
  - Defined for ς ∈ SP = SF ∪ {w} (includes warehouse)
- **x^p_{ςt}(ω)**: Quantity of product p replenished to ship-from point ς on day t under scenario ω
  - Only defined for ς ∈ SF (warehouse does not receive replenishments)
- **I^p_{ςt}(ω)**: Inventory level of product p at ship-from point ς at beginning of period t under scenario ω
  - Only defined for ς ∈ SF
- **B^p_{st}(ω)**: Backlog level of product p at store s at beginning of period t under scenario ω
  - Only defined for s ∈ S (only stores have backlogs)
  - All decided **after** observing scenario ω
  - Different values for each scenario

---

## Indices

### Sets:
- **T = {1, ..., T}**: Planning horizon (e.g., 30 days)
- **S**: Set of existing stores
- **F**: Set of potential urban fulfillment centers
- **SF = S ∪ F**: Set of all ship-from points (require deployment decisions)
- **SP = S ∪ F ∪ {w}**: Set of all supply points (ship-from points + warehouse)
- **P**: Set of products
- **L**: Set of customer locations/zones
- **Ω**: Set of scenarios
- **Õ(ω)**: Set of online orders under scenario ω
- **Õ_t(ω)**: Set of online orders arriving in period t under scenario ω
- **Õ_{lt}(ω)**: Set of online orders from customer location l in period t under scenario ω
- **P(o)**: Set of products in order o
- **τ_ς**: Set of replenishment periods for ship-from point ς

### Individual Indices:
- **t**: Time period (day)
- **s**: Store
- **f**: Fulfillment center
- **ς**: Ship-from point (store or FC)
- **p**: Product
- **l**: Customer location/zone
- **ω**: Scenario
- **o**: Online order
- **w**: Warehouse (always operational, no deployment decision)

---

## Input Data (Parameters)

### Stage 1 Parameters (Deterministic):
- **s_max**: Maximum number of ship-from points that can be deployed
- **c^f_ς**: Fixed/usage cost of deploying ship-from point ς (only for ς ∈ SF)

### Stage 2 Parameters (Deterministic):
- **π_p**: Net sales revenue per unit of product p
- **c^r_{pς}**: Unit replenishment cost for product p at ship-from point ς
- **c^h_{pς}**: Unit inventory holding cost for product p at ship-from point ς
- **c^b_{ps}**: Unit backlog cost for product p at store s
- **c^t_{ςl}**: Transportation cost per order from supply point ς to customer location l (defined for ς ∈ SP)
- **c^p_ς**: Picking cost per item at supply point ς (defined for ς ∈ SP)
- **c_{wo}**: Per-order charge from warehouse (includes fixed, replenishment, holding costs)
- **r_{ςl}**: Response time (delivery time) from supply point ς to customer location l (defined for ς ∈ SP)
- **k_t**: Available transportation capacity on day t
- **τ_ς**: Scheduled replenishment periods for ship-from point ς

### Stage 2 Parameters (Stochastic - Scenario-Dependent):
- **d^p_{st}(ω)**: Physical demand for product p at store s in period t under scenario ω
- **b_{ςt}(ω)**: Fulfillment capacity (max orders processable) at ship-from point ς on day t under scenario ω
- **n^o_p(ω)**: Quantity of product p in online order o under scenario ω
- **n_o(ω)**: Total number of items in online order o under scenario ω
- **π_o(ω)**: Revenue from online order o under scenario ω
- **η_o(ω)**: Required response time for online order o under scenario ω
- **Õ_{lt}(ω)**: The actual set of orders arriving from location l in period t (scenario-dependent)

### Probability Distribution:
- **p(ω)**: Probability of scenario ω occurring (where ∑_{ω∈Ω} p(ω) = 1)

---

## Key Relationships

### Warehouse Treatment:
- **Always available**: Warehouse w has no deployment decision (no y_w variable)
- **Unlimited inventory**: Warehouse assumed to always have stock available
- **Can fulfill orders**: Warehouse appears in order assignment constraint as part of SP
- **Does not receive replenishments**: Warehouse only appears in constraints where it ships TO ship-from points, not where it receives FROM others
- **No capacity constraint**: Unlike ship-from points, warehouse has no fulfillment capacity limit

### Where Stage 1 Constrains Stage 2:
- If y_ς = 0 (ship-from point not deployed), then fulfillment capacity constraint forces ∑_{o∈Õ_t(ω)} z^o_ς(ω) = 0
- If y_ς = 1 (ship-from point deployed), then up to b_{ςt}(ω) orders can be assigned
- Warehouse is unaffected by Stage 1 decisions (always available)

### Scenario Structure:
Each scenario ω represents one complete realization of:
1. All online orders across all customer locations over entire horizon
2. All physical demands at all stores over entire horizon
3. All capacity realizations at all stores over entire horizon
