"""
Prometheus metrics definitions for Recipe Explorer.

All custom application metrics are defined here to keep metric declarations
centralized and avoid scattered Counter/Histogram instances across modules.

Metrics are grouped by subsystem:
- Cache: Redis hit/miss/set/error rates
- MealDB: External API call outcomes and latency
- Search: Recipe search frequency and popular terms
"""

from prometheus_client import Counter, Histogram

# ---------------------------------------------------------------------------
# Cache metrics
# ---------------------------------------------------------------------------
cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations by result type",
    ["operation"],  # hit | miss | set | error
)

# ---------------------------------------------------------------------------
# MealDB external API metrics
# ---------------------------------------------------------------------------
mealdb_requests_total = Counter(
    "mealdb_requests_total",
    "Total requests to TheMealDB API by endpoint and outcome",
    ["endpoint", "status"],  # endpoint: search|lookup, status: success|error|timeout|rate_limited
)

mealdb_request_duration_seconds = Histogram(
    "mealdb_request_duration_seconds",
    "Latency of TheMealDB API calls in seconds",
    ["endpoint"],  # search | lookup
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ---------------------------------------------------------------------------
# Recipe search metrics
# ---------------------------------------------------------------------------
recipe_search_total = Counter(
    "recipe_search_total",
    "Total recipe searches by source",
    ["source"],  # internal | external
)

# TODO(observability): In a high-traffic production system the unbounded
# search-term label would cause label-cardinality explosion.  For this
# portfolio project traffic is low enough that this is acceptable.
recipe_search_terms_total = Counter(
    "recipe_search_terms_total",
    "Search term frequency counter",
    ["term"],
)
