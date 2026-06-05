"""
Tests for Prometheus metrics integration.

Verifies that the /metrics endpoint is exposed and that custom
application metrics are registered and update correctly.
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, CollectorRegistry


def test_metrics_endpoint_returns_200(client):
    """The /metrics endpoint should return HTTP 200 with prometheus text format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Prometheus text format uses text/plain or the OpenMetrics content type
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type or "text/openmetrics" in content_type


def test_metrics_endpoint_contains_http_metrics(client):
    """Auto-instrumented HTTP metrics should appear in /metrics output."""
    # Make a request first so the instrumentator has data
    client.get("/health")
    response = client.get("/metrics")
    body = response.text
    # prometheus-fastapi-instrumentator exposes http_request_duration or similar
    assert "http" in body.lower()


def test_cache_metrics_registered():
    """Custom cache metrics should be registered in the default registry."""
    from app.services.metrics import cache_operations_total

    # The metric should exist and accept the expected labels
    cache_operations_total.labels(operation="hit")
    cache_operations_total.labels(operation="miss")
    cache_operations_total.labels(operation="set")
    cache_operations_total.labels(operation="error")


def test_mealdb_metrics_registered():
    """Custom MealDB metrics should be registered in the default registry."""
    from app.services.metrics import mealdb_requests_total, mealdb_request_duration_seconds

    mealdb_requests_total.labels(endpoint="search", status="success")
    mealdb_requests_total.labels(endpoint="lookup", status="error")
    mealdb_request_duration_seconds.labels(endpoint="search")


def test_search_metrics_registered():
    """Custom search metrics should be registered in the default registry."""
    from app.services.metrics import recipe_search_total, recipe_search_terms_total

    recipe_search_total.labels(source="internal")
    recipe_search_total.labels(source="external")
    recipe_search_terms_total.labels(term="test")


def test_search_increments_metrics(client):
    """Performing a search should increment the recipe_search_total counter."""
    from app.services.metrics import recipe_search_total

    # Capture the counter value before the search
    before = recipe_search_total.labels(source="internal")._value.get()

    # Trigger a search
    client.get("/api/recipes/search?q=chicken")

    after = recipe_search_total.labels(source="internal")._value.get()
    assert after > before


def test_search_term_tracked(client):
    """Searching with a query should increment the term-specific counter."""
    from app.services.metrics import recipe_search_terms_total

    before = recipe_search_terms_total.labels(term="pasta")._value.get()

    client.get("/api/recipes/search?q=Pasta")

    after = recipe_search_terms_total.labels(term="pasta")._value.get()
    assert after == before + 1


def test_custom_metrics_appear_in_output(client):
    """Custom metrics should be visible in the /metrics text output."""
    # Trigger some operations first
    client.get("/api/recipes/search?q=test")

    response = client.get("/metrics")
    body = response.text

    assert "cache_operations_total" in body
    assert "recipe_search_total" in body
    assert "recipe_search_terms_total" in body
    assert "mealdb_requests_total" in body
    assert "mealdb_request_duration_seconds" in body
