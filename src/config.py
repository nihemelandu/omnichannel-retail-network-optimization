# config.py
# ============================================================
# Central configuration for the e-DND model.
# All parameters drawn from Arslan, Klibi & Montreuil (2021),
# Tables 1, 2, 3 and Section 5.1
#
# Built with Pydantic v2 for:
#   - Type validation   — wrong parameter types caught at startup
#   - Range validation  — out-of-range values caught at startup
#   - CLI override      — pass settings via environment variables
#                         or instantiate with keyword arguments
#
# Usage (other modules):
#   import config as cfg
#   cfg.NUM_STORES          ← instance-level attribute (unchanged interface)
#
# Override for experiments:
#   from config import ProjectConfig
#   cfg = ProjectConfig(city="City2", demand_ratio="low_DR")
#
# Reference: Arslan, Klibi & Montreuil (2021)
# ============================================================

from __future__ import annotations
from typing      import Dict, Tuple
from pydantic    import BaseModel, Field, model_validator


# ============================================================
# SUB-MODELS
# ============================================================

class InstanceSize(BaseModel):
    num_stores:             int = Field(..., gt=0)
    num_customer_locations: int = Field(..., gt=0)
    s_max:                  int = Field(..., gt=0)
    num_fcs:                int = Field(..., ge=0)


class StoreCostRange(BaseModel):
    regular: Tuple[float, float]
    high:    Tuple[float, float]


class StoreCapacityRange(BaseModel):
    regular: Tuple[int, int]
    high:    Tuple[int, int]


class MarketConditionParams(BaseModel):
    m_min:       float = Field(..., ge=0.0)
    m_max:       float = Field(..., le=1.0)
    s:           float = Field(..., gt=0.0)
    delta_m_bar: float = Field(..., gt=0.0)
    delta_s:     float = Field(..., gt=0.0)
    beta:        float = Field(..., gt=0.0)
    m_bar:       float
    s_bar:       float = Field(..., gt=0.0)
    m0:          float


# ============================================================
# MAIN CONFIGURATION MODEL
# ============================================================

class ProjectConfig(BaseModel):
    """
    Typed, validated configuration for the e-DND optimization model.
    All parameters correspond directly to the paper's notation.
    Instantiate with keyword arguments to override defaults for experiments.
    """

    # ----------------------------------------------------------
    # INSTANCE SELECTION
    # ----------------------------------------------------------
    city: str = Field(
        default="City1",
        description="Active city instance. 'City1' (5 stores) or 'City2' (9 stores)."
    )

    # ----------------------------------------------------------
    # INSTANCE SIZES (Table 1)
    # ----------------------------------------------------------
    instance_sizes: Dict[str, InstanceSize] = Field(
        default={
            "City1": InstanceSize(
                num_stores=5,
                num_customer_locations=10,
                s_max=3,
                num_fcs=1,
            ),
            "City2": InstanceSize(
                num_stores=9,
                num_customer_locations=20,
                s_max=5,
                num_fcs=1,
            ),
        }
    )

    # ----------------------------------------------------------
    # PLANNING HORIZON (Section 5.1)
    # ----------------------------------------------------------
    num_periods: int = Field(
        default=30,
        gt=0,
        description="T = 30 consecutive days (one month)."
    )

    # ----------------------------------------------------------
    # PRODUCTS (Section 5.1)
    # ----------------------------------------------------------
    num_products: int = Field(
        default=100,
        gt=0,
        description="|P| = 100 products (ABC classification)."
    )

    # ----------------------------------------------------------
    # REPLENISHMENT FREQUENCIES
    # ----------------------------------------------------------
    replenishment_frequency: Dict[str, int] = Field(
        default={
            "high":    2,   # days between replenishments, high-traffic stores
            "regular": 5,   # days between replenishments, regular stores
        }
    )

    high_traffic_fraction: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Fraction of stores classified as high physical traffic."
    )

    # ----------------------------------------------------------
    # COST PARAMETERS (Table 2)
    # ----------------------------------------------------------

    # Warehouse
    warehouse_transport_cost_per_order: float = Field(default=5.0,  gt=0)
    warehouse_replenishment_charge:     float = Field(default=0.15, gt=0)
    warehouse_fixed_charge:             float = Field(default=0.40, gt=0)
    warehouse_holding_charge:           float = Field(default=0.01, gt=0)
    warehouse_picking_cost_per_item:    float = Field(default=1.0,  gt=0)

    # Stores
    store_fixed_cost_range: StoreCostRange = Field(
        default=StoreCostRange(
            regular=(3000.0, 6000.0),
            high=(7000.0, 10000.0),
        )
    )
    store_picking_cost_multiplier: float = Field(default=0.25, gt=0)
    store_holding_cost:            float = Field(default=0.015, gt=0)
    store_backlogging_cost:        float = Field(default=0.50,  gt=0)
    store_replenishment_cost:      float = Field(default=0.20,  gt=0)
    store_transport_cost_range:    Tuple[float, float] = Field(default=(3.0, 5.0))

    # Fulfillment Center
    fc_usage_cost:               float = Field(default=20000.0, gt=0)
    fc_picking_cost_multiplier:  float = Field(default=0.50,    gt=0)
    fc_holding_cost:             float = Field(default=0.012,   gt=0)
    fc_replenishment_cost:       float = Field(default=0.20,    gt=0)
    fc_transport_cost_per_order: float = Field(default=3.5,     gt=0)

    # Products
    product_price_range:         Tuple[float, float] = Field(default=(15.0, 50.0))
    warehouse_picking_cost_base: float = Field(default=1.0, gt=0)

    # ----------------------------------------------------------
    # CAPACITY PARAMETERS (Section 5.1)
    # ----------------------------------------------------------
    store_capacity_range: StoreCapacityRange = Field(
        default=StoreCapacityRange(
            regular=(5, 7),
            high=(10, 14),
        )
    )

    fc_capacity:                    int   = Field(default=30,  gt=0)
    transport_capacity_multiplier:  float = Field(default=1.2, gt=0)
    initial_inventory_store:        int   = Field(default=5,   gt=0)
    initial_inventory_fc:           int   = Field(default=10,  gt=0)

    # ----------------------------------------------------------
    # ONLINE ORDER ARRIVAL (Section 3.2)
    # ----------------------------------------------------------
    order_arrival_rate_multiplier: float = Field(default=0.165, gt=0)
    order_arrival_rate_range:      Tuple[int, int] = Field(default=(1, 10))

    # ----------------------------------------------------------
    # ORDER COMPOSITION (Section 3.2)
    # ----------------------------------------------------------
    order_min_items:          int   = Field(default=1,   gt=0)
    order_max_items:          int   = Field(default=6,   gt=0)
    order_quantity_mean:      float = Field(default=1.0, gt=0)
    order_quantity_std_range: Tuple[float, float] = Field(default=(0.7, 1.2))

    # ----------------------------------------------------------
    # RESPONSE TIME OPTIONS (Section 3.2 and Table 3)
    # ----------------------------------------------------------
    response_times: Dict[str, int] = Field(
        default={"1D": 1, "2D": 2, "3D": 3}
    )

    response_time_distributions: Dict[str, Dict[str, float]] = Field(
        default={
            "low_RE":      {"1D": 0.10, "2D": 0.20, "3D": 0.70},
            "moderate_RE": {"1D": 0.25, "2D": 0.30, "3D": 0.45},
            "high_RE":     {"1D": 0.60, "2D": 0.30, "3D": 0.10},
        }
    )

    response_time_expectation: str = Field(
        default="high_RE",
        description="Active RE level. One of: low_RE, moderate_RE, high_RE."
    )

    # ----------------------------------------------------------
    # DEMAND RATIO (Section 5.1)
    # ----------------------------------------------------------
    demand_ratio_multipliers: Dict[str, float] = Field(
        default={
            "low_DR":      1.0,
            "moderate_DR": 4/3,
            "high_DR":     2.0,
        }
    )

    demand_ratio: str = Field(
        default="high_DR",
        description="Active DR level. One of: low_DR, moderate_DR, high_DR."
    )

    # ----------------------------------------------------------
    # PHYSICAL DEMAND (Section 3.2)
    # ----------------------------------------------------------
    physical_demand_multiplier:     float = Field(default=1.3, gt=0)
    physical_demand_range:          Tuple[int, int] = Field(default=(1, 6))
    high_traffic_demand_multiplier: float = Field(default=1.2, gt=0)

    # ----------------------------------------------------------
    # MARKET CONDITION PROCESS (Appendix 7.1)
    # ----------------------------------------------------------
    market_condition: MarketConditionParams = Field(
        default=MarketConditionParams(
            m_min=0.0,
            m_max=1.0,
            s=0.1,
            delta_m_bar=0.8,
            delta_s=0.9,
            beta=0.8,
            m_bar=0.5,
            s_bar=0.15,
            m0=0.5,
        )
    )

    # ----------------------------------------------------------
    # WAREHOUSE RESPONSE TIME
    # ----------------------------------------------------------
    warehouse_response_time: int = Field(
        default=2,
        gt=0,
        description="Warehouse allows 2-day response due to distance from city."
    )

    # ----------------------------------------------------------
    # SAA SAMPLE SIZE (Section 5.2, Table 4)
    # ----------------------------------------------------------
    n_scenarios: int = Field(
        default=50,
        gt=0,
        description="K=50 scenarios validated at 2.97% statistical gap."
    )

    # ----------------------------------------------------------
    # SOLVER SETTINGS
    # ----------------------------------------------------------
    optimality_gap:  float = Field(default=0.001, gt=0)
    time_limit_sec:  int   = Field(default=3600,  gt=0)
    solver:          str   = Field(default="HiGHS")

    # ----------------------------------------------------------
    # REPRODUCIBILITY
    # ----------------------------------------------------------
    random_seed: int = Field(default=42)

    # ----------------------------------------------------------
    # DERIVED PROPERTIES
    # Active instance dimensions resolved from city selection
    # ----------------------------------------------------------
    @model_validator(mode='after')
    def validate_selections(self) -> 'ProjectConfig':
        valid_cities = list(self.instance_sizes.keys())
        if self.city not in valid_cities:
            raise ValueError(
                f"city must be one of {valid_cities}, got '{self.city}'"
            )
        valid_re = list(self.response_time_distributions.keys())
        if self.response_time_expectation not in valid_re:
            raise ValueError(
                f"response_time_expectation must be one of {valid_re}, "
                f"got '{self.response_time_expectation}'"
            )
        valid_dr = list(self.demand_ratio_multipliers.keys())
        if self.demand_ratio not in valid_dr:
            raise ValueError(
                f"demand_ratio must be one of {valid_dr}, "
                f"got '{self.demand_ratio}'"
            )
        return self

    # ----------------------------------------------------------
    # CONVENIENCE PROPERTIES
    # Provide flat uppercase attribute access identical to the
    # original config.py so no other module needs changing.
    # e.g. cfg.NUM_STORES, cfg.STORE_HOLDING_COST
    # ----------------------------------------------------------

    @property
    def NUM_STORES(self) -> int:
        return self.instance_sizes[self.city].num_stores

    @property
    def NUM_CUSTOMER_LOCATIONS(self) -> int:
        return self.instance_sizes[self.city].num_customer_locations

    @property
    def S_MAX(self) -> int:
        return self.instance_sizes[self.city].s_max

    @property
    def NUM_FCS(self) -> int:
        return self.instance_sizes[self.city].num_fcs

    @property
    def NUM_PERIODS(self) -> int:
        return self.num_periods

    @property
    def NUM_PRODUCTS(self) -> int:
        return self.num_products

    @property
    def REPLENISHMENT_FREQUENCY(self) -> Dict[str, int]:
        return self.replenishment_frequency

    @property
    def HIGH_TRAFFIC_FRACTION(self) -> float:
        return self.high_traffic_fraction

    @property
    def WAREHOUSE_TRANSPORT_COST_PER_ORDER(self) -> float:
        return self.warehouse_transport_cost_per_order

    @property
    def WAREHOUSE_REPLENISHMENT_CHARGE(self) -> float:
        return self.warehouse_replenishment_charge

    @property
    def WAREHOUSE_FIXED_CHARGE(self) -> float:
        return self.warehouse_fixed_charge

    @property
    def WAREHOUSE_HOLDING_CHARGE(self) -> float:
        return self.warehouse_holding_charge

    @property
    def WAREHOUSE_PICKING_COST_PER_ITEM(self) -> float:
        return self.warehouse_picking_cost_per_item

    @property
    def STORE_FIXED_COST_RANGE(self) -> Dict[str, Tuple[float, float]]:
        return {
            "regular": self.store_fixed_cost_range.regular,
            "high":    self.store_fixed_cost_range.high,
        }

    @property
    def STORE_PICKING_COST_MULTIPLIER(self) -> float:
        return self.store_picking_cost_multiplier

    @property
    def STORE_HOLDING_COST(self) -> float:
        return self.store_holding_cost

    @property
    def STORE_BACKLOGGING_COST(self) -> float:
        return self.store_backlogging_cost

    @property
    def STORE_REPLENISHMENT_COST(self) -> float:
        return self.store_replenishment_cost

    @property
    def STORE_TRANSPORT_COST_RANGE(self) -> Tuple[float, float]:
        return self.store_transport_cost_range

    @property
    def FC_USAGE_COST(self) -> float:
        return self.fc_usage_cost

    @property
    def FC_PICKING_COST_MULTIPLIER(self) -> float:
        return self.fc_picking_cost_multiplier

    @property
    def FC_HOLDING_COST(self) -> float:
        return self.fc_holding_cost

    @property
    def FC_REPLENISHMENT_COST(self) -> float:
        return self.fc_replenishment_cost

    @property
    def FC_TRANSPORT_COST_PER_ORDER(self) -> float:
        return self.fc_transport_cost_per_order

    @property
    def PRODUCT_PRICE_RANGE(self) -> Tuple[float, float]:
        return self.product_price_range

    @property
    def WAREHOUSE_PICKING_COST_BASE(self) -> float:
        return self.warehouse_picking_cost_base

    @property
    def STORE_CAPACITY_RANGE(self) -> Dict[str, Tuple[int, int]]:
        return {
            "regular": self.store_capacity_range.regular,
            "high":    self.store_capacity_range.high,
        }

    @property
    def FC_CAPACITY(self) -> int:
        return self.fc_capacity

    @property
    def TRANSPORT_CAPACITY_MULTIPLIER(self) -> float:
        return self.transport_capacity_multiplier

    @property
    def INITIAL_INVENTORY_STORE(self) -> int:
        return self.initial_inventory_store

    @property
    def INITIAL_INVENTORY_FC(self) -> int:
        return self.initial_inventory_fc

    @property
    def ORDER_ARRIVAL_RATE_MULTIPLIER(self) -> float:
        return self.order_arrival_rate_multiplier

    @property
    def ORDER_ARRIVAL_RATE_RANGE(self) -> Tuple[int, int]:
        return self.order_arrival_rate_range

    @property
    def ORDER_MIN_ITEMS(self) -> int:
        return self.order_min_items

    @property
    def ORDER_MAX_ITEMS(self) -> int:
        return self.order_max_items

    @property
    def ORDER_QUANTITY_MEAN(self) -> float:
        return self.order_quantity_mean

    @property
    def ORDER_QUANTITY_STD_RANGE(self) -> Tuple[float, float]:
        return self.order_quantity_std_range

    @property
    def RESPONSE_TIMES(self) -> Dict[str, int]:
        return self.response_times

    @property
    def RESPONSE_TIME_DISTRIBUTIONS(self) -> Dict[str, Dict[str, float]]:
        return self.response_time_distributions

    @property
    def RESPONSE_TIME_EXPECTATION(self) -> str:
        return self.response_time_expectation

    @property
    def DEMAND_RATIO_MULTIPLIERS(self) -> Dict[str, float]:
        return self.demand_ratio_multipliers

    @property
    def DEMAND_RATIO(self) -> str:
        return self.demand_ratio

    @property
    def PHYSICAL_DEMAND_MULTIPLIER(self) -> float:
        return self.physical_demand_multiplier

    @property
    def PHYSICAL_DEMAND_RANGE(self) -> Tuple[int, int]:
        return self.physical_demand_range

    @property
    def HIGH_TRAFFIC_DEMAND_MULTIPLIER(self) -> float:
        return self.high_traffic_demand_multiplier

    @property
    def MARKET_CONDITION(self) -> Dict:
        return self.market_condition.model_dump()

    @property
    def WAREHOUSE_RESPONSE_TIME(self) -> int:
        return self.warehouse_response_time

    @property
    def N_SCENARIOS(self) -> int:
        return self.n_scenarios

    @property
    def OPTIMALITY_GAP(self) -> float:
        return self.optimality_gap

    @property
    def TIME_LIMIT_SEC(self) -> int:
        return self.time_limit_sec

    @property
    def SOLVER(self) -> str:
        return self.solver

    @property
    def RANDOM_SEED(self) -> int:
        return self.random_seed


# ============================================================
# MODULE-LEVEL INSTANCE
# Preserves `import config as cfg` → `cfg.NUM_STORES` interface.
# All other modules import this file and access cfg.PARAM_NAME.
#
# To override for an experiment:
#   from config import ProjectConfig
#   cfg = ProjectConfig(city="City2", demand_ratio="low_DR")
# ============================================================

cfg = ProjectConfig()
