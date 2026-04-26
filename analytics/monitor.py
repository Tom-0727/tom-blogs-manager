#!/usr/bin/env python3
"""Blog analytics monitor — Search Console + GA4 data collection and analysis."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account

SA_KEY_PATH = Path(__file__).parent.parent / ".secrets" / "tom-blogs-sa.json"
SITE_URL = "https://www.tom-blogs.top/"
GA4_PROPERTY_ID = "properties/533036655"
GA4_MEASUREMENT_ID = "G-6D1EK1NGE0"

SCOPES_SC = ["https://www.googleapis.com/auth/webmasters.readonly"]
SCOPES_GA = ["https://www.googleapis.com/auth/analytics.readonly"]


def _get_credentials(scopes: list[str]):
    """Load service account credentials."""
    creds = service_account.Credentials.from_service_account_file(
        str(SA_KEY_PATH), scopes=scopes
    )
    return creds


# ── Search Console ─────────────────────────────────────────────

def get_search_console_service():
    from googleapiclient.discovery import build
    creds = _get_credentials(SCOPES_SC)
    return build("searchconsole", "v1", credentials=creds)


def list_sites():
    """List all sites in Search Console."""
    svc = get_search_console_service()
    result = svc.sites().list().execute()
    return result.get("siteEntry", [])


def get_index_status():
    """Get URL inspection data via sitemap check."""
    svc = get_search_console_service()
    # List sitemaps to check submission status
    try:
        sitemaps = svc.sitemaps().list(siteUrl=SITE_URL).execute()
        return {"sitemaps": sitemaps.get("sitemap", [])}
    except Exception as e:
        return {"error": str(e)}


def get_search_performance(days: int = 28):
    """Get search performance data (queries, clicks, impressions)."""
    svc = get_search_console_service()
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    # By page
    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["page"],
        "rowLimit": 100,
    }
    try:
        result = svc.searchanalytics().query(
            siteUrl=SITE_URL, body=request_body
        ).execute()
        return result.get("rows", [])
    except Exception as e:
        return {"error": str(e)}


def get_search_queries(days: int = 28):
    """Get top search queries."""
    svc = get_search_console_service()
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 50,
    }
    try:
        result = svc.searchanalytics().query(
            siteUrl=SITE_URL, body=request_body
        ).execute()
        return result.get("rows", [])
    except Exception as e:
        return {"error": str(e)}


def inspect_url(url: str):
    """Inspect a specific URL's index status."""
    svc = get_search_console_service()
    try:
        result = svc.urlInspection().index().inspect(
            body={
                "inspectionUrl": url,
                "siteUrl": SITE_URL,
            }
        ).execute()
        return result
    except Exception as e:
        return {"error": str(e)}


# ── Google Analytics 4 ─────────────────────────────────────────

def discover_ga4_property():
    """Discover GA4 property ID from the admin API."""
    from googleapiclient.discovery import build
    creds = _get_credentials(["https://www.googleapis.com/auth/analytics.readonly"])
    # Try admin API to list accounts/properties
    try:
        admin_svc = build("analyticsadmin", "v1alpha", credentials=creds)
        accounts = admin_svc.accounts().list().execute()
        return accounts
    except Exception as e:
        return {"error": str(e)}


def get_ga4_report(days: int = 7):
    """Get GA4 page view report."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest
    )

    creds = _get_credentials(SCOPES_GA)
    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=GA4_PROPERTY_ID,
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="totalUsers"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        limit=50,
    )
    try:
        response = client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "page": row.dimension_values[0].value,
                "views": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "avg_duration": float(row.metric_values[2].value),
            })
        return rows
    except Exception as e:
        return {"error": str(e)}


# ── Report Generation ──────────────────────────────────────────

def generate_report():
    """Generate a comprehensive analytics report."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": SITE_URL,
    }

    # Search Console
    print("=== Search Console ===")
    sites = list_sites()
    print(f"Sites: {json.dumps(sites, indent=2, default=str)}")
    report["sc_sites"] = sites

    index_status = get_index_status()
    print(f"Sitemaps: {json.dumps(index_status, indent=2, default=str)}")
    report["sc_sitemaps"] = index_status

    perf = get_search_performance()
    print(f"Search performance (by page): {json.dumps(perf, indent=2, default=str)}")
    report["sc_performance"] = perf

    queries = get_search_queries()
    print(f"Top queries: {json.dumps(queries, indent=2, default=str)}")
    report["sc_queries"] = queries

    # URL inspection for a few key pages
    test_urls = [
        "https://www.tom-blogs.top/2026/04/12/agent-engineering/agent-continual-learning/",
        "https://www.tom-blogs.top/2026/04/08/agent-engineering/openclaw-is-not-the-end/",
        "https://www.tom-blogs.top/2026/03/15/agent-product/openclaw-feishu-blog-automation/",
    ]
    inspections = {}
    for url in test_urls:
        print(f"\nInspecting: {url}")
        result = inspect_url(url)
        print(json.dumps(result, indent=2, default=str))
        inspections[url] = result
    report["url_inspections"] = inspections

    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sites":
        print(json.dumps(list_sites(), indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "sitemaps":
        print(json.dumps(get_index_status(), indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "inspect":
        url = sys.argv[2] if len(sys.argv) > 2 else test_urls[0]
        print(json.dumps(inspect_url(url), indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "perf":
        print(json.dumps(get_search_performance(), indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "queries":
        print(json.dumps(get_search_queries(), indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "ga4-discover":
        print(json.dumps(discover_ga4_property(), indent=2, default=str))
    else:
        generate_report()
