---
name: food-trend-weekly
description: Find high-performing food videos by keyword across three platforms, record source evidence, run Python screening and produce Markdown reports in explicit stages.
---

Read README.md, COLLECTION_STANDARD.md, DATA_FORMAT.md and current configs. Follow the user's requested stage and quantity; do not automatically expand a small test.

1. Discovery: use the configured keywords on every platform. Prefer most-liked on Douyin/Xiaohongshu and most-played on Bilibili where actually available; select video type. Record actual search conditions, including unavailable or unsuccessful controls. No publication-time filters, minimum age, or age cohorts. Do not default to recommendation channels or reinstall MediaCrawler.
2. Batch-review cards, skip explicit image posts, irrelevant items and known IDs. Open details to confirm video, complete working URL, author, title and required engagement observations. Follow DATA_FORMAT.md; preserve approximate displays, never invent exact values. Dates are optional background; retain unknown/edited/relative date text honestly. Save batches of at most five locally immediately, then import and screen using existing Python commands. Do not reimplement filtering.
3. Verification: inspect originals/video or reliable subtitles, record comparison evidence and reusable form observations in checks.jsonl. Use priority_queue first, then manually assess approximate counts. Cumulative counts reflect capture time, not growth; old videos may benefit from longer accumulation. Do not label collected old content a new weekly hit or infer platform-wide ranking. Stop at CAPTCHA/access limits.
4. Reporting: run verify/report, follow existing MD master. The issue date range is for report naming only, never a publication constraint. Review accuracy; no default Google Docs publishing.

Keywords, quotas and core metrics have one source: config/discovery_policy.json. Real data, token-bearing URLs and sessions stay local; GitHub contains code/rules/master only. Report IDs use date ranges; entry IDs add -001, while original video identity remains platform:ID. Handle repo maintenance under AGENTS.md by replacing obsolete rules rather than layering conflicting instructions.
