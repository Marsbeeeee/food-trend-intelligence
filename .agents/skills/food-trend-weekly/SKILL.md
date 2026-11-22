---
name: food-trend-weekly
description: Process existing MediaCrawler food-video exports into reproducible weekly reports and verification records. Use for fixed-sample weekly reporting, not discovering or collecting new videos.
---

Run from the food-trend-intelligence repository root. Read README.md and config/weekly.json. Confirm xhs, dy and bili JSONL inputs and requested period before running.

Use the existing command: `python run_pipeline.py --input-root <exports> --run-id <unique-id>`. Never rewrite filtering or infer new thresholds during a run. Rule changes require versioned code/config and a new regression run.

Check stage_manifest.json, filter_summary.json, logs/errors.jsonl and report_manifest.json. Every input must have a normalized record or explicit parse error; every parsed record must have a screening decision. Keep unknown metrics null and uncertain fields pending. Do not promote a single case into a trend or combine platform metrics into a ranking.

Use `python verify_reproducibility.py --input-root <exports>` to compare two fresh runs. Run directories cannot be overwritten. Missing platform data, invalid configuration or stage failures stop reporting; explain the concrete failure and preserve completed diagnostics.

Manual original-page checks belong in separate verification override JSONL records with operator, checked_at and evidence_source. Never change imported source lines. Login/access failures stay pending; do not bypass them or invent values.

Local report.md is mandatory. Its numbered sections follow the current 01–08 report structure. Google Docs is optional, only on user request after local output passes checks; copy the user-supplied current template and read it before editing. Failure to publish must not invalidate local output. Do not modify the master template.
