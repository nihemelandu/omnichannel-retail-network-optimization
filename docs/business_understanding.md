# Distribution Network Optimization for Omnichannel Retail

## Business Question

As e-commerce demand grows, our existing distribution network — built
for bulk store replenishment — is increasingly unable to fulfill online
orders profitably and on time. The central warehouse is too far from
urban customers to meet next-day delivery expectations, stores were
never designed for order picking, and transportation capacity is already
under pressure.

**The question this project answers:** Given our existing network, what
is the profit-maximizing way to restructure our existing distribution
network to serve both physical and online customers simultaneously as
e-commerce scales?

---

## 1. Business Context

Brick-and-mortar retailers are under sustained pressure to integrate
online sales into their existing physical store networks. This pressure
intensified dramatically after 2020, when e-commerce accelerated well
beyond earlier projections. Retailers that once competed purely on
in-store experience now compete on delivery speed, fulfillment
reliability, and cost-to-serve across both physical and online channels
simultaneously.

The core tension is structural. Central warehouses were designed to
replenish stores on scheduled weekly or bi-weekly cycles — not to
fulfill individual online orders rapidly to urban customers. When these
same warehouses are asked to serve the online channel, they operate at
the wrong speed, the wrong granularity, and often the wrong location
relative to urban demand centers. The result is a distribution network
that serves neither channel optimally.

World-class retailers such as Walmart, Target, and Amazon have responded
by deploying advanced fulfillment strategies — ship-from-store, dedicated
urban fulfillment centers, and hybrid configurations. The challenge for
most brick-and-mortar retailers is that these strategies involve
significant capital commitment and operational disruption, and the
conditions under which each strategy pays off are not obvious without
rigorous analysis.

---

## 2. Strategic Business Goals

The business needs answers to three strategic questions:

1. **When does Ship-from-Store (SS) outperform Ship-from-Warehouse (SW)?**
   Under what demand volume, response time profile, and store capacity
   conditions does activating stores for online fulfillment generate more
   profit than continuing to fulfill from the central warehouse?

2. **When does a dedicated urban Fulfillment Center (SF) justify its
   cost?** What is the usage cost threshold below which deploying an
   urban FC becomes profitable, and what demand and response time
   conditions trigger this threshold?

3. **How does omnichannel integration disrupt existing replenishment
   dynamics?** When store inventory is shared between physical and online
   channels, how does this affect transportation capacity utilization,
   replenishment schedules, and overall network stability?

---

## 3. Technical Goal

Identify the profit-maximizing network configuration by evaluating all
64 City1 configurations across N=50 Monte Carlo scenarios using a
two-stage stochastic MIP, and validate that the results are stable,
internally consistent, and robust to scenario sample size.

---

## 4. Fulfillment Strategies Evaluated

Three fulfillment strategies are evaluated, corresponding to increasing
levels of network transformation:

| Strategy | Description | Key Characteristic |
|---|---|---|
| **SW — Ship-from-Warehouse** | All online orders fulfilled from the central warehouse | Baseline; no additional investment; limited fast-delivery capability |
| **SS — Ship-from-Stores** | Selected stores activated as online fulfillment points; shared inventory | Leverages existing infrastructure; capacity-constrained; replenishment-sensitive |
| **SF — Ship-from-Fulfillment Center** | SS plus a dedicated urban FC with online-only inventory | Highest flexibility and capacity; highest fixed and usage cost |

These strategies are not mutually exclusive in the model. Under SS,
some orders may still be fulfilled from the warehouse. Under SF, some
orders may be fulfilled from stores or the warehouse. The model
optimizes the allocation dynamically across scenarios.

---

## 5. Stakeholders

| Stakeholder | Primary Concern |
|---|---|
| **CFO / Finance** | ROI on network investment; fixed cost exposure; margin impact |
| **Chief Supply Chain Officer** | Fulfillment reliability; replenishment disruption; transportation capacity |
| **eCommerce Channel Head** | Lost sales rate; delivery SLA attainment; customer experience |

---

## 6. Business KPIs

These are the metrics that matter to the business, independent of how
the model works technically.

| Business KPI | Definition | Strategic Relevance |
|---|---|---|
| **Net Profit by Strategy** | Total expected profit across scenarios after all costs | Primary decision criterion for capital allocation |
| **Lost Sales Rate** | Percentage of online orders that cannot be fulfilled within the requested response time | Measures revenue leakage and customer attrition risk |
| **Delivery SLA Attainment** | Percentage of online orders fulfilled within the customer's requested response time (1-day, 2-day, 3-day) | Measures competitive positioning on delivery speed |
| **Cost-to-Serve by Channel** | Breakdown of fulfillment, replenishment, holding, transportation, and fixed costs per strategy | Identifies where cost is being incurred and whether investment is justified |
| **FC Deployment Break-Even** | The usage cost threshold at which deploying an urban FC becomes profitable relative to SS | Directly informs the capital investment decision |

---

## 7. Technical Metrics

These metrics evaluate the quality and reliability of the optimization
model, giving us confidence that the business KPIs reported are
trustworthy.

| Technical Metric | Definition | Purpose |
|---|---|---|
| **Statistical Optimality Gap** | 95% confidence interval gap between SAA lower bound and out-of-sample upper bound | Validates that N=50 scenarios produce a stable, trustworthy solution |
| **Scenario Sensitivity (K = 10, 25, 50)** | Comparison of solution quality and strategy ranking across scenario sample sizes | Determines the minimum scenario count sufficient for reliable results |
| **Objective Reconciliation** | Dollar difference between the MIP objective value and the manually reconstructed cost components | Confirms the model is internally consistent |
| **Inventory Conservation** | Verification that inventory balance equations hold across all periods and scenarios | Confirms inventory dynamics are correctly modeled |
| **Objective Value by Configuration** | Expected profit for each of the 64 enumerated network configurations across 50 scenarios | Primary output of the full enumeration approach |
| **Solve Time** | Wall clock time per configuration and total enumeration time | Assesses computational feasibility for City1 and scalability to City2 |

---

## 8. Solution Approach

The project evaluates three fulfillment strategies using a two-stage
stochastic Mixed-Integer Program (MIP).

**Stage 1 — Network Configuration (here-and-now decisions):**
Which stores and FCs to activate for online fulfillment. Made before
demand is observed.

**Stage 2 — Operational Decisions (wait-and-see decisions):**
Order assignment, replenishment quantities, and inventory management.
Made after demand is realized under each scenario.

**Solution Method:**
With 5 stores and 1 FC in the City1 network, there are 2⁵ × 2¹ = 64
possible network configurations. Each configuration is evaluated across
N=50 Monte Carlo scenarios at Stage 2. Full enumeration over this
decision space is exact, transparent, and computationally tractable for
City1.

---

## 9. Success Criteria

**Model Validity**
- Objective reconciliation passes with $0.00 discrepancy on all three
  strategies
- Inventory conservation check passes across all periods and scenarios
- Extreme condition tests pass without infeasibility

**Analytical Completeness**
- All 64 City1 configurations evaluated across N=50 scenarios
- Strategy ranking is stable across demand ratio and response time
  expectation combinations
- Sensitivity analysis completed across four dimensions: fulfillment
  capacity, FC usage cost, replenishment schedule flexibility, and SW
  adjustment cost rates

**Business Communicability**
- Results translate directly to the three strategic questions in
  Section 2
- A business stakeholder reading the output can understand what the
  recommended network configuration is and why

---

## 10. Constraints and Assumptions

- **City1 scope:** 5 stores, 1 FC, 64 configurations. City2 is out of
  scope for the current iteration.
- **N=50 scenarios:** To be validated by our own K = 10, 25, 50
  sensitivity test.
- **Demand and cost parameters:** Based on instance generation
  specifications from the reference paper, inspired by a real European
  cosmetics retailer.
- **No dedicated e-commerce DC:** The model excludes a standalone
  e-commerce distribution center not supplied from the cross-channel
  warehouse.

---

*This document is a living artifact and will be updated as the project
progresses.*
