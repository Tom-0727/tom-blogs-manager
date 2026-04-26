---
id: ep.20260415T035500Z.blog.analytics-monitoring-setup
task_id: task.blog.data-analytics-monitoring
domain: blog
title: Set up analytics monitoring and diagnose indexing issue
objective: Configure GA4, set up Search Console API, diagnose why only homepage+about are indexed, build monitoring script.
status: completed
last_edited_at: 2026-04-15
---

## Objective

Human provided GA4 Measurement ID (G-6D1EK1NGE0) and Service Account credentials. Need to configure GA4, build monitoring pipeline, and diagnose the indexing problem.

## Actions Taken

1. Saved Service Account key to .secrets/tom-blogs-sa.json (chmod 600, gitignored)
2. Configured GA4 in Hexo Fluid theme (_config.fluid.yml: web_analytics.google.measurement_id), pushed to blog
3. Built analytics/monitor.py with Search Console API and GA4 API integration
4. Ran diagnostic via Search Console API:
   - list_sites(): confirmed www.tom-blogs.top has siteFullUser access
   - sitemaps(): 36 URLs submitted, 0 indexed from sitemap
   - inspect_url(): homepage=PASS (indexed), about=PASS (indexed), articles="URL is unknown to Google"
   - search_performance(): only homepage (5 impressions, 1 click) and about (4 impressions) in 28 days
5. Refreshed writing ideas data (new 04-15 date appeared)

## Key Evidence

- Root cause confirmed: Google has crawled the homepage (April 10) but hasn't followed links to article pages. All articles are "URL is unknown to Google". This is a crawl budget issue typical of new/low-authority sites.
- Homepage has 20 server-rendered article links — no JS rendering issue
- No technical blockers (robots.txt, noindex, x-robots-tag all clean)
- Indexing API needs to be enabled in Google Cloud for batch URL notification
- GA4 Admin API needs to be enabled for analytics data retrieval

## Outcome

- GA4 live on blog (pending Vercel deploy to start collecting data)
- Search Console API monitoring working
- Clear diagnosis: crawl budget issue, not technical SEO issue
- Human needs to: (1) manually request indexing in Search Console, (2) enable Indexing API and Analytics Admin API in Google Cloud
- Sent detailed findings and action items to human, awaiting reply

## Follow-up Actions

- Once Indexing API enabled: batch notify Google about all article URLs
- Once GA4 Admin API enabled: discover property ID, start pulling traffic data
- Build automated weekly report script
- Consider structured data (JSON-LD Article schema) for richer search results
