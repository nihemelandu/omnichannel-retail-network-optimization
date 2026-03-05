# config.py
# ============================================================
# Central configuration file for the e-DND model.
# All instance parameters are drawn directly from the paper:
# Arslan, Klibi & Montreuil (2021), Tables 1, 2, 3 and Section 5.1
# ============================================================
# To change instance size or scenario, modify this file only.
# No other file should hardcode parameter values.
# ============================================================


# ------------------------------------------------------------
# INSTANCE SELECTION
# Choose between "City1" (small) and "City2" (large)
# ------------------------------------------------------------
CITY = "City1"

# ------------------------------------------------------------
# INSTANCE SIZES (Table 1)
# ------------------------------------------------------------
INSTANCE_SIZES = {
    "City1": {
        "num_stores":             5,    # |S|
        "num_customer_locations": 10,   # |L|
        "s_max":                  3,    # maximum ship-from points deployable
        "num_fcs":                1,    # one potential urban FC per city
    },
    "City2": {
        "num_stores":             9,
        "num_customer_locations": 20,
        "s_max":                  5,
        "num_fcs":                1,
    },
}

# Derive active instance dimensions from CITY selection
NUM_STORES             = INSTANCE_SIZES[CITY]["num_stores"]
NUM_CUSTOMER_LOCATIONS = INSTANCE_SIZES[CITY]["num_customer_locations"]
S_MAX                  = INSTANCE_SIZES[CITY]["s_max"]
NUM_FCS                = INSTANCE_SIZES[CITY]["num_fcs"]

# ------------------------------------------------------------
# PLANNING HORIZON (Section 5.1)
# ------------------------------------------------------------
NUM_PERIODS = 30        # T = 30 consecutive days (one month)

# ------------------------------------------------------------
# PRODUCTS (Section 5.1)
# ------------------------------------------------------------
NUM_PRODUCTS = 100      # |P| = 100 products (ABC classification)

# ------------------------------------------------------------
# STORE CATEGORIES
# Stores replenished 3x/week = high physical customer traffic
# Stores replenished 1-2x/week = regular
# Paper assigns roughly 1 high-traffic store per 5 stores
# ------------------------------------------------------------
# Replenishment frequencies per store (days between replenishments)
# High traffic: every 2 days (~3x/week); Regular: every 5-7 days
REPLENISHMENT_FREQUENCY = {
    "high":    2,   # days between replenishments for high-traffic stores
    "regular": 5,   # days between replenishments for regular stores
}

# Fraction of stores classified as high physical customer traffic
HIGH_TRAFFIC_FRACTION = 0.2   # 1 out of 5 stores in City1

# ------------------------------------------------------------
# COST PARAMETERS (Table 2)
# All percentage costs are expressed as a fraction of product sales price
# ------------------------------------------------------------

# --- Warehouse ---
WAREHOUSE_TRANSPORT_COST_PER_ORDER = 5.0        # $/order (fixed)
WAREHOUSE_REPLENISHMENT_CHARGE     = 0.15       # 15% of product price
WAREHOUSE_FIXED_CHARGE             = 0.40       # 40% of product price (per order)
WAREHOUSE_HOLDING_CHARGE           = 0.01       # 1% of product price
WAREHOUSE_PICKING_COST_PER_ITEM    = 1.0        # $/item

# Combined per-order warehouse charge (cwo): fixed + holding + replenishment
# Applied as a lump sum per order shipped from warehouse
# Computed at runtime once product prices are known

# --- Stores ---
# Fixed cost to activate a store as a ship-from point
# Ud[3,6] * 1000 for regular stores; Ud[7,10] * 1000 for high-traffic stores
STORE_FIXED_COST_RANGE = {
    "regular": (3000, 6000),    # Ud[3,6] * 1000
    "high":    (7000, 10000),   # Ud[7,10] * 1000
}
STORE_PICKING_COST_MULTIPLIER = 0.25    # store picking cost = 0.25 * warehouse picking cost
STORE_HOLDING_COST             = 0.015  # 1.5% of product price
STORE_BACKLOGGING_COST         = 0.50   # 50% of product price
STORE_REPLENISHMENT_COST       = 0.20   # 20% of product price
STORE_TRANSPORT_COST_RANGE     = (3.0, 5.0)  # Uc[3,5] $/order (on-demand delivery)

# --- Fulfillment Center ---
FC_USAGE_COST              = 20000.0   # flat usage cost per planning horizon
FC_PICKING_COST_MULTIPLIER = 0.50      # FC picking cost = 0.50 * warehouse picking cost
FC_HOLDING_COST            = 0.012     # 1.2% of product price
FC_REPLENISHMENT_COST      = 0.20      # 20% of product price
FC_TRANSPORT_COST_PER_ORDER = 3.5     # $/order (city distribution vehicles)

# --- Products ---
PRODUCT_PRICE_RANGE         = (15.0, 50.0)   # Uc[15,50] $/product
WAREHOUSE_PICKING_COST_BASE = 1.0            # $/item at warehouse (c^p_w)

# ------------------------------------------------------------
# CAPACITY PARAMETERS (Section 5.1)
# ------------------------------------------------------------

# Store daily online order processing capacity
STORE_CAPACITY_RANGE = {
    "regular": (5, 7),    # Ud[5,7] orders/day
    "high":    (10, 14),  # Ud[10,14] orders/day
}

# Urban FC deterministic daily capacity
FC_CAPACITY = 30    # orders/day (deterministic, not affected by physical sales)

# Transportation capacity: 1.2x average daily demand
TRANSPORT_CAPACITY_MULTIPLIER = 1.2

# Initial inventory levels (Section 5.1)
INITIAL_INVENTORY_STORE = 5    # units per product per store
INITIAL_INVENTORY_FC    = 10   # units per product per FC

# ------------------------------------------------------------
# ONLINE ORDER ARRIVAL (Section 3.2)
# Poisson process per customer location
# arrival rate = 0.165 * Ud[1,10] orders/day per location
# ------------------------------------------------------------
ORDER_ARRIVAL_RATE_MULTIPLIER = 0.165
ORDER_ARRIVAL_RATE_RANGE      = (1, 10)    # Ud[1,10]

# ------------------------------------------------------------
# ORDER COMPOSITION (Section 3.2)
# Number of items per order: Ud[kmin, kmax]
# Product inclusion: multinomial with probabilities alpha_p
# Quantity per item: Normal(mu_p, sigma_p)
# ------------------------------------------------------------
ORDER_MIN_ITEMS   = 1
ORDER_MAX_ITEMS   = 6
ORDER_QUANTITY_MEAN = 1.0                  # mu_p for all products
ORDER_QUANTITY_STD_RANGE = (0.7, 1.2)     # sigma_p ~ Uc[0.7, 1.2]

# ------------------------------------------------------------
# RESPONSE TIME OPTIONS (Section 3.2)
# Three delivery speed options in days
# ------------------------------------------------------------
RESPONSE_TIMES = {
    "1D": 1,   # next-day delivery (24h)
    "2D": 2,   # two-day delivery (48h)
    "3D": 3,   # three-day delivery (72h)
}

# Response time expectation distributions (Table 3)
# Keys: "low_RE", "moderate_RE", "high_RE"
# Values: probabilities for [1D, 2D, 3D]
RESPONSE_TIME_DISTRIBUTIONS = {
    "low_RE":      {"1D": 0.1, "2D": 0.2, "3D": 0.7},
    "moderate_RE": {"1D": 0.25, "2D": 0.3, "3D": 0.45},
    "high_RE":     {"1D": 0.6,  "2D": 0.3, "3D": 0.1},
}

# Active response time expectation level
RESPONSE_TIME_EXPECTATION = "high_RE"

# ------------------------------------------------------------
# DEMAND RATIO (Section 5.1)
# Online-to-physical demand ratio
# Controlled by multiplying arrival rate by DR multiplier
# ------------------------------------------------------------
DEMAND_RATIO_MULTIPLIERS = {
    "low_DR":      1.0,
    "moderate_DR": 4/3,
    "high_DR":     2.0,
}

# Active demand ratio level
DEMAND_RATIO = "high_DR"

# ------------------------------------------------------------
# PHYSICAL DEMAND (Section 3.2)
# Expected demand per product per store: lambda_p = 1.3 * Ud[1,6]
# Regular stores use lambda_p directly
# High-traffic stores multiply by 1.2
# ------------------------------------------------------------
PHYSICAL_DEMAND_MULTIPLIER       = 1.3
PHYSICAL_DEMAND_RANGE            = (1, 6)    # Ud[1,6]
HIGH_TRAFFIC_DEMAND_MULTIPLIER   = 1.2

# ------------------------------------------------------------
# MARKET CONDITION PROCESS (Appendix 7.1)
# Truncated normal process governing correlated uncertainty
# across physical demand and store capacity
# ------------------------------------------------------------
MARKET_CONDITION = {
    "m_min":       0.0,    # mmin
    "m_max":       1.0,    # mmax
    "s":           0.1,    # lowest possible standard deviation
    "delta_m_bar": 0.8,    # mean reversion speed
    "delta_s":     0.9,    # std deviation adjustment speed
    "beta":        0.8,    # truncation adjustment parameter
    "m_bar":       0.5,    # steady state mean (mu_bar)
    "s_bar":       0.15,   # steady state standard deviation
    "m0":          0.5,    # initial market condition (= steady state mean)
}

# ------------------------------------------------------------
# WAREHOUSE RESPONSE TIME
# Paper states warehouse allows 2-day response (distance from city)
# ------------------------------------------------------------
WAREHOUSE_RESPONSE_TIME = 2    # days (2D delivery only from warehouse)

# ------------------------------------------------------------
# SAA SAMPLE SIZE (Section 5.2, Table 4)
# Paper validates K=50 scenarios gives 2.97% statistical gap
# ------------------------------------------------------------
N_SCENARIOS = 50

# ------------------------------------------------------------
# SOLVER SETTINGS
# ------------------------------------------------------------
OPTIMALITY_GAP    = 0.001    # 0.1% optimality tolerance
TIME_LIMIT_SEC    = 3600     # 1 hour time limit
SOLVER            = "HiGHS"  # Free solver; swap to "GUROBI" if available

# ------------------------------------------------------------
# RANDOM SEED (for reproducibility)
# ------------------------------------------------------------
RANDOM_SEED = 42
