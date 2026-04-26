#!/usr/bin/env python3
"""Weekly analytics report generator for tom-blogs.top.

Usage:
    uv run python analytics/weekly_report.py          # Print report to stdout
    uv run python analytics/weekly_report.py --json   # Output raw JSON data
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from xml.etree import ElementTree

import requests

from monitor import (
    get_ga4_report,
    get_search_performance,
    get_search_queries,
    inspect_url,
    SITE_URL,
)

SITEMAP_URL = "https://www.tom-blogs.top/sitemap.xml"


def fetch_article_urls() -> list[str]:
    """Parse sitemap and return article URLs only (exclude tag/category/about/home)."""
    resp = requests.get(SITEMAP_URL, timeout=10)
    root = ElementTree.fromstring(resp.text)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//ns:loc", ns)]
    # Filter to article URLs only
    article_urls = []
    for u in urls:
        path = u.replace("https://www.tom-blogs.top/", "/")
        if path in ("/", "/about/index.html"):
            continue
        if "/tags/" in path or "/categories/" in path:
            continue
        article_urls.append(u)
    return article_urls


def check_indexing(article_urls: list[str]) -> dict:
    """Run URL inspection on all articles. Returns summary dict."""
    indexed = []
    not_indexed = []

    for url in article_urls:
        r = inspect_url(url)
        ir = r.get("inspectionResult", {}).get("indexStatusResult", {})
        verdict = ir.get("verdict", "UNKNOWN")
        coverage = ir.get("coverageState", "UNKNOWN")
        crawl_time = ir.get("lastCrawlTime", "")
        short = url.replace("https://www.tom-blogs.top/", "/")

        entry = {"url": short, "full_url": url, "coverage": coverage, "crawl_time": crawl_time}
        if verdict == "PASS":
            indexed.append(entry)
        else:
            not_indexed.append(entry)
        time.sleep(0.3)

    return {
        "total": len(article_urls),
        "indexed_count": len(indexed),
        "indexed": indexed,
        "not_indexed": not_indexed,
    }


def collect_all_data() -> dict:
    """Collect all analytics data for the report."""
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "site": SITE_URL,
    }

    # Indexing
    article_urls = fetch_article_urls()
    data["indexing"] = check_indexing(article_urls)

    # Search Console performance
    data["search_perf"] = get_search_performance(28)
    data["search_queries"] = get_search_queries(28)

    # GA4
    ga4 = get_ga4_report(7)
    if isinstance(ga4, dict) and "error" in ga4:
        data["ga4"] = ga4
    else:
        data["ga4"] = ga4 if ga4 else []

    return data


def format_report(data: dict) -> str:
    """Format collected data into a plain-text Chinese report."""
    lines = []
    lines.append(f"tom-blogs.top 周报  {data['generated_at']}")
    lines.append("=" * 50)

    # ── Indexing ──
    idx = data["indexing"]
    lines.append("")
    lines.append(f"一、收录情况（{idx['indexed_count']}/{idx['total']} 篇已收录）")
    lines.append("-" * 40)

    if idx["indexed"]:
        lines.append("已收录：")
        for e in idx["indexed"]:
            ct = e["crawl_time"][:10] if e["crawl_time"] else "未知"
            lines.append(f"  {e['url']}  （抓取: {ct}）")

    if idx["not_indexed"]:
        lines.append("")
        lines.append("未收录：")
        for e in idx["not_indexed"]:
            lines.append(f"  {e['url']}")

    # ── Search Performance ──
    lines.append("")
    lines.append("二、搜索表现（近28天）")
    lines.append("-" * 40)

    perf = data["search_perf"]
    if isinstance(perf, list) and perf:
        total_clicks = sum(r.get("clicks", 0) for r in perf)
        total_impressions = sum(r.get("impressions", 0) for r in perf)
        avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
        lines.append(f"总展示: {total_impressions}  总点击: {total_clicks}  CTR: {avg_ctr:.1%}")
        lines.append("")
        lines.append("按页面：")
        for r in sorted(perf, key=lambda x: x.get("impressions", 0), reverse=True):
            page = r["keys"][0].replace("https://www.tom-blogs.top", "")
            lines.append(f"  {page}  展示:{r['impressions']} 点击:{r['clicks']} 位置:{r['position']:.1f}")
    else:
        lines.append("暂无搜索数据")

    # Search queries
    queries = data["search_queries"]
    if isinstance(queries, list) and queries:
        lines.append("")
        lines.append("搜索词：")
        for q in queries[:10]:
            lines.append(f"  「{q['keys'][0]}」 展示:{q['impressions']} 点击:{q['clicks']}")
    else:
        lines.append("暂无搜索词数据")

    # ── GA4 Traffic ──
    lines.append("")
    lines.append("三、网站流量（近7天，GA4）")
    lines.append("-" * 40)

    ga4 = data["ga4"]
    if isinstance(ga4, list) and ga4:
        total_views = sum(r.get("views", 0) for r in ga4)
        total_users = sum(r.get("users", 0) for r in ga4)
        lines.append(f"总浏览: {total_views}  总用户: {total_users}")
        lines.append("")
        lines.append("按页面：")
        for r in sorted(ga4, key=lambda x: x.get("views", 0), reverse=True):
            dur = f"{r['avg_duration']:.0f}s" if r.get("avg_duration") else "-"
            lines.append(f"  {r['page']}  浏览:{r['views']} 用户:{r['users']} 平均停留:{dur}")
    elif isinstance(ga4, dict) and "error" in ga4:
        lines.append(f"GA4数据获取失败: {ga4['error']}")
    else:
        lines.append("暂无GA4数据")

    # ── Action Items ──
    lines.append("")
    lines.append("四、待办事项")
    lines.append("-" * 40)

    actions = []
    if idx["not_indexed"]:
        actions.append(f"有 {len(idx['not_indexed'])} 篇文章未被收录，建议在 Search Console 手动请求收录")
        # List the most recent unindexed ones
        for e in idx["not_indexed"][:3]:
            actions.append(f"  - {e['url']}")
        if len(idx["not_indexed"]) > 3:
            actions.append(f"  - ...及另外 {len(idx['not_indexed']) - 3} 篇")

    # High impression, low CTR opportunities
    if isinstance(perf, list):
        for r in perf:
            if r.get("impressions", 0) >= 3 and r.get("ctr", 0) < 0.1:
                page = r["keys"][0].replace("https://www.tom-blogs.top", "")
                actions.append(f"  {page} 展示{r['impressions']}次但CTR仅{r['ctr']:.0%}，可优化标题/描述")

    if actions:
        for a in actions:
            lines.append(a)
    else:
        lines.append("暂无紧急待办")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    json_mode = "--json" in sys.argv
    data = collect_all_data()
    if json_mode:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_report(data))


if __name__ == "__main__":
    main()
