# Omnichannel Retail Network Optimization

## Overview
This project develops a scenario-based analytics framework to evaluate omnichannel retail distribution network designs under e-commerce growth. The goal is to support strategic decisions around distribution center (DC) utilization, ship-from-store strategies, and service-level targets while balancing cost to serve and customer experience.

The project is motivated by the challenge retailers face in modernizing traditional logistics networks to meet faster delivery expectations without excessive cost increases.

---

## Problem Statement
Retailers operating hybrid (store + e-commerce) supply chains must decide:
- How to repurpose existing distribution centers to support direct-to-consumer fulfillment
- When to use ship-from-store versus centralized fulfillment
- How network design choices impact cost to serve, delivery speed, and service levels under demand growth

This project evaluates multiple network configurations using scenario and sensitivity analysis to quantify these trade-offs.

---

## Project Scope
### In Scope
- Strategic distribution network design
- Scenario modeling for demand growth and service-level targets
- DC repurposing and ship-from-store strategies
- Cost-to-serve and customer experience evaluation

### Out of Scope
- Tactical routing and last-mile optimization
- Real-time execution systems
- Supplier-side network design

---

## Data Description
The analysis uses **synthetic retail network data**, including:
- Geographic demand zones representing online customer demand
- Distribution center and store locations with capacity constraints
- Transportation cost matrices (DC → customer, store → customer)
- Inventory holding and handling cost parameters
- Delivery-time service level thresholds (e.g., 1–2 day delivery)

Synthetic data is designed to reflect realistic retail network structures while remaining reproducible.

---

## Methodology
The project applies a **scenario-based decision analytics approach**, combining:
- Network flow and facility selection optimization
- Scenario generation for alternative fulfillment strategies
- Sensitivity analysis on demand growth and service-level constraints

Each scenario is evaluated using consistent performance metrics to enable comparison across network designs.

---

## Scenarios Evaluated
- **Baseline Network**: Existing DC network with store-centric fulfillment
- **DC Repurposing**: Selected DCs enabled for direct-to-consumer fulfillment
- **Ship-from-Store Expansion**: Stores used as local fulfillment nodes
- **Demand Growth Stress Test**: 2×–3× increase in online demand with tighter delivery SLAs

---

## Evaluation Metrics
Network designs are compared using:
- Total cost to serve
- Cost per order
- Average and percentile delivery times
- Service-level attainment (% of orders delivered within SLA)
- Inventory utilization across stores and DCs

---

## Key Insights
- Repurposing DCs can significantly improve service levels under demand growth, but increases handling and inventory costs
- Ship-from-store strategies reduce delivery time but introduce higher fulfillment variability
- Optimal network design depends on explicit trade-offs between cost efficiency and customer experience targets

---

## Reference
This project is inspired by research from the **MIT Center for Transportation & Logistics (CTL)** on omnichannel network design and inventory positioning, adapted into a practical, resume-scale analytics project focused on retail decision-making.

---

## Future Work
- Incorporate stochastic demand and lead-time uncertainty
- Extend the model to include inventory placement optimization
- Add dynamic order routing logic for real-time fulfillment decisions
- Integrate emissions or sustainability metrics into network evaluation
- Develop an interactive dashboard for executive scenario exploration

---

## Disclaimer
This project uses synthetic and anonymized data for educational and portfolio purposes and does not represent any specific retailer’s proprietary network.
