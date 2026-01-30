# Complete Explanation: e-DND Optimization Problem and Integer L-Shaped Method

## What is The Master Problem

**The Master Problem** is in the context of decomposition algorithms.

### The Master Problem: Definition

**The Master Problem (MP)** is the "top-level" optimization problem in a **decomposition approach** that:

1. Contains the **first-stage decisions** (the strategic decisions)
2. Uses an **approximation** (variable θ) for the second-stage costs/profits
3. Gets progressively **refined** through the addition of cuts

It's called the "master" because it **coordinates** the overall solution, while delegating detailed evaluations to **subproblems**.

---

## In the e-DND Context

### The Original Two-Stage Problem:
```
┌─────────────────────────────────────────────────────┐
│  ORIGINAL MONOLITHIC PROBLEM (too big to solve)    │
└─────────────────────────────────────────────────────┘

max  -Σ c^f_ς y_ς + (1/N)Σ Q(y, ω)
                           ω∈Ω_N

s.t. Σ y_ς ≤ s_max
     y ∈ {0,1}^|SF|
     
     [For each scenario ω]:
        z^o_ς(ω) = order assignment variables
        x^p_st(ω) = replenishment variables
        I^p_st(ω) = inventory variables
        B^p_st(ω) = backlog variables
        
        [Thousands of constraints per scenario]
        [50 scenarios × ~10,000 constraints = 500,000 constraints!]

Decision variables: ~500,000 total
Constraints: ~500,000
Problem size: INTRACTABLE for commercial solvers
```

**Problem:** This is a massive mixed-integer program with hundreds of thousands of variables and constraints. CPLEX can't solve it efficiently.

---

### The Decomposition Idea:

Instead of solving everything at once, we **separate** the problem:
```
┌───────────────────────────────────────────────────┐
│  MASTER PROBLEM (small, easy to solve)           │
│  Decides: Which stores to open? (y variables)    │
│  Uses: Approximation θ for expected profit       │
└───────────────────────────────────────────────────┘
            │
            │ Proposes: y* = [1, 0, 1, 0, ...]
            │
            ▼
┌───────────────────────────────────────────────────┐
│  SUBPROBLEMS (solved separately for each ω)      │
│  Given y*, solve operational decisions:          │
│    - Which orders to fulfill where? (z)          │
│    - How much to replenish? (x)                  │
│    - Inventory levels? (I, B)                    │
│  Returns: Q(y*, ω) = profit in scenario ω        │
└───────────────────────────────────────────────────┘
            │
            │ Returns: Average profit Q(y*) = (1/N)Σ Q(y*, ω)
            │
            ▼
┌───────────────────────────────────────────────────┐
│  CUT GENERATOR                                    │
│  Adds cut to Master Problem:                     │
│  "If y = y*, then θ ≤ Q(y*)"                     │
└───────────────────────────────────────────────────┘
            │
            └──► Feedback to Master Problem
                 Resolve with new cut
```

---

## The Master Problem in Detail

### Mathematical Formulation (Equations 17-20):
```
┌─────────────────────────────────────────────────────┐
│  MASTER PROBLEM                                     │
└─────────────────────────────────────────────────────┘

max  -Σ c^f_ς y_ς + θ                              (17)
     ς∈SF

s.t. Σ y_ς ≤ s_max                                 (18)
     ς∈SF

     θ ≤ (q_S̄ - U)·[Σ y_i - Σ y_i - (|S̄|-1)] + U  (19)
                    i∈S̄   i∉S̄
     
     ∀S̄ ∈ {evaluated solutions}

     y ∈ {0,1}^|SF|                                 (20)

Decision Variables:
  - y_ς: Binary (open store ς or not?) [~10 variables]
  - θ:   Continuous (approximation of expected profit) [1 variable]

Total variables: ~11
Constraints: ~10 + [number of cuts added]
```

**Key characteristics:**
- **Small:** Only ~11 variables (compared to 500,000 in monolithic)
- **Fast to solve:** Binary program with few variables
- **Incomplete:** Doesn't know true profit function yet (uses θ)
- **Dynamic:** Gets refined by adding cuts (constraint 19)

---

## Why Is It Called "Master"?

Think of it like a **manager-worker relationship:**
```
┌─────────────────────────────────────────────┐
│  MASTER PROBLEM (The Manager)               │
│                                             │
│  Role: Make strategic decisions             │
│  Question: "Which stores should we open?"   │
│  Constraint: Limited knowledge about        │
│             operational profitability       │
└─────────────────────────────────────────────┘
            │
            │ Delegates to workers
            ▼
┌─────────────────────────────────────────────┐
│  SUBPROBLEMS (The Workers)                  │
│                                             │
│  Role: Evaluate operational performance     │
│  Question: "Given these stores, how much    │
│            profit can we make in scenario ω?"│
│  Answer: Returns Q(y*, ω)                   │
└─────────────────────────────────────────────┘
            │
            │ Reports back
            ▼
┌─────────────────────────────────────────────┐
│  MASTER PROBLEM (learns from feedback)      │
│                                             │
│  Updates knowledge: "Ah, opening stores     │
│  {1,2} gives $95,000 profit!"              │
│  Adds cut to remember this                 │
│  Makes new decision with better info       │
└─────────────────────────────────────────────┘
```

The Master Problem **orchestrates** the solution process while **delegating** detailed evaluations to subproblems.

---

## Evolution of the Master Problem

### Iteration 0: Initial Master Problem
```
max  -Σ c^f_ς y_ς + θ

s.t. Σ y_ς ≤ 3
     y ∈ {0,1}

[No cuts yet!]
```

**Solution:** y* = [1,1,1], θ* = +∞ (unbounded)
**Interpretation:** "I'll open all stores and claim infinite profit!"

---

### Iteration 1: After First Evaluation

Evaluate y* = [1,1,1] → Q([1,1,1]) = $118,000

Add cut:
```
max  -Σ c^f_ς y_ς + θ

s.t. Σ y_ς ≤ 3
     θ ≤ -32,000·[y₁+y₂+y₃ - 2] + 150,000  ← New cut!
     y ∈ {0,1}
```

**Solution:** y* = [1,1,0], θ* = $105,000 (estimate)
**Interpretation:** "Maybe opening 2 stores is better?"

---

### Iteration 2: After Second Evaluation

Evaluate y* = [1,1,0] → Q([1,1,0]) = $98,000

Add another cut:
```
max  -Σ c^f_ς y_ς + θ

s.t. Σ y_ς ≤ 3
     θ ≤ -32,000·[y₁+y₂+y₃ - 2] + 150,000      (cut 1)
     θ ≤ -52,000·[y₁+y₂-y₃ - 1] + 150,000      (cut 2) ← New!
     y ∈ {0,1}
```

**Solution:** y* = [1,0,1], θ* = $102,000 (estimate)
**Interpretation:** "What about stores 1 and 3?"

---

### Eventually: Converged Master Problem

After many iterations:
```
max  -Σ c^f_ς y_ς + θ

s.t. Σ y_ς ≤ 3
     θ ≤ [cut for opening store 1]
     θ ≤ [cut for opening stores 1,2]
     θ ≤ [cut for opening stores 1,3]
     θ ≤ [cut for opening stores 2,3]
     θ ≤ [cut for opening stores 1,2,3]
     ... [many more cuts]
     y ∈ {0,1}
```

**Solution:** y* = [1,1,0], θ* = $98,000
**Verification:** We've already evaluated this → Q([1,1,0]) = $98,000 ✓
**Conclusion:** OPTIMAL! We've found the best deployment strategy.

---

## Master Problem vs. Subproblems

Let me clarify the relationship:

### Master Problem:
```python
# Small optimization problem
# Variables: ~11 (y₁, y₂, ..., y₁₀, θ)
# Constraints: ~20

Variables:
  y = [y_store1, y_store2, ..., y_FC]  # 10 binary
  θ                                     # 1 continuous

Objective:
  max -10,000·y_store1 - 25,000·y_store2 - ... + θ

Constraints:
  y_store1 + y_store2 + ... ≤ 3      # cardinality
  θ ≤ [cuts...]                       # optimality cuts
  y ∈ {0,1}^10

Solve time: < 1 second
```

### Subproblem for Scenario ω:
```python
# Large optimization problem (per scenario!)
# Variables: ~10,000
# Constraints: ~10,000

Given: y* = [1, 0, 1, 0, ...]  # From master problem

Variables:
  z^o_ς(ω) for all orders o, supply points ς     # ~5,000 binary
  x^p_st(ω) for all products, stores, periods    # ~3,000 continuous
  I^p_st(ω) for all products, stores, periods    # ~3,000 continuous
  B^p_st(ω) for all products, stores, periods    # ~3,000 continuous

Objective:
  max [revenue from fulfilled orders] 
      - [replenishment costs]
      - [holding costs]
      - [backlog costs]

Constraints:
  - Order assignment constraints (10)
  - Capacity constraints (11) ← uses y* here!
  - Inventory balance (5-8)
  - Product availability (12)
  ... thousands of constraints

Solve time: 10-60 seconds (per scenario!)
```

**Key point:** We solve **50 subproblems** (one per scenario) every time we evaluate a y*.

---

## Why Decomposition Helps

### Monolithic Approach:
```
Solve one gigantic problem:
  - 500,000 variables
  - 500,000 constraints
  
CPLEX time: Hours or fails to find good solution
```

### Decomposition Approach:
```
Iteration 1:
  └─ Solve Master (11 vars, <1s)
  └─ Solve 50 Subproblems (50 × 30s = 25 min)
  └─ Add cut
  
Iteration 2:
  └─ Solve Master (11 vars, <1s)
  └─ Solve 50 Subproblems (50 × 30s = 25 min)
  └─ Add cut

...

After ~10 iterations: Found optimal solution
Total time: ~4 hours (but reliably finds good solutions!)
```

**Advantage:** Even though we solve many subproblems, each one is manageable, and we can:
- Solve subproblems in **parallel** (all 50 scenarios simultaneously)
- **Skip** expensive MIP solves when Benders cuts suffice
- Get **good feasible solutions early** (any y with cuts is feasible)

---

## Analogy: Planning a Restaurant Chain

### Master Problem = Corporate Strategy
```
Decision: Which cities should we open restaurants in?
Variables: y_NYC, y_Boston, y_Chicago, ...
Constraint: Budget allows max 3 restaurants

Question: How profitable will each configuration be?
Problem: Don't know yet! Need to evaluate operations.
```

### Subproblems = Operational Simulations
```
Given: Open restaurants in {NYC, Boston}
Simulate: 50 different market scenarios
  - Scenario 1 (recession): Lose $50k
  - Scenario 2 (boom): Make $200k
  - Scenario 3 (normal): Make $100k
  - ...
  - Scenario 50 (competitors enter): Make $75k

Average profit: $98k across all scenarios
```

### Feedback Loop:
```
Master: "What if I open {NYC, Chicago}?"
Subproblems: [simulate 50 scenarios] → "$102k average"
Master: "Oh, that's better! Let me try {Boston, Chicago}..."
Subproblems: [simulate 50 scenarios] → "$95k average"
Master: "OK, {NYC, Chicago} is best so far. Final decision!"
```

The Master Problem makes strategic decisions.
The Subproblems evaluate those decisions under uncertainty.

---

## Summary

### The Master Problem is:

1. The top-level optimization that decides first-stage variables (y)
2. A simplification that uses θ instead of computing exact expected profit
3. Iteratively refined through cuts that teach it about the profit function
4. Small and fast (~11 variables vs. 500,000 in monolithic)
5. The coordinator that delegates detailed evaluations to subproblems

### It's called "Master" because:

- It controls the overall solution strategy
- It coordinates with subproblems (the "workers")
- It makes the final strategic decisions (which stores to open)
- It learns from feedback and adapts

**Key insight:** The Master Problem doesn't solve the entire problem alone. It works together with subproblems in an iterative process, gradually learning what the true profit function looks like through the cuts it accumulates.
