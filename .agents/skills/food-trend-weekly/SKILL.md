---
name: food-trend-weekly
description: Coordinate direct-browser food video collection, local date archives, deterministic screening, human review and Markdown reports with optional Word/PDF export.
---

Read README.md and [workflow](../../../docs/workflow.md); commands and errors are in [usage](../../../docs/usage.md). Run only the user's requested stage through run.py. Python manages files and deterministic processing; it does not itself browse or log in.

## Collection

1. Fix the user's archive date, otherwise today's date in Asia/Shanghai, separately from issue period and publication dates. Run `python run.py collect init --date YYYY-MM-DD` and `status --show-ids`; resume existing IDs and attempts without resets. Quotas, keywords and complete-field requirements come from config/collection.json, not new Skill rules.
2. Read [collection rules](../../../docs/collection.md) and the relevant platform: [Douyin](../../../docs/collection/douyin.md), [Xiaohongshu](../../../docs/collection/xiaohongshu.md), [Bilibili](../../../docs/collection/bilibili.md). Check existing login first. When needed, show the actual QR/session and let the user sign in, then verify access. Only parallelize browser input across demonstrated independent sessions.
3. Use keyword search and actual supported heat sorting; record comprehensive sorting honestly when heat sorting is unavailable. Video publication dates are unrestricted. Do not substitute channels, use age gates or fall back to MediaCrawler.
4. Before each detail, record an attempt. Observe the current video's ID, title, author, full URL, required counters and capture time together. Preserve approximate/lower-bound displays and necessary access parameters. Use append for complete batches, reject for failed details; do not save incomplete payloads or invent counters/dates. Confirm current page state instead of relying on old selectors.
5. Use actual added counts and existing checkpoints to resume; stop on configured target/attempt limit, CAPTCHA or access restriction. Continue unaffected platforms and report actual gaps. Finish with audit and stop at the requested stage.

## Screening and review

Use `python run.py discovery` to import/freeze existing files and `screen` to call the fixed modules. Screening parameters live in config/screening.json; do not reimplement ranking. Retain original IDs, precision, review flags and the three existing Chinese labels. Review with viewer; when substantive analysis is needed, inspect originals or reliable subtitles and record evidence under docs/data_format.md. A keep mark is not watched-video proof; cumulative counts are not growth or age-adjusted popularity.

## Reporting and export

Confirm the issue period separately from archive/capture dates. With viewer marks only, use review-report for an explicitly labeled draft and referenced title/description editorial input; do not fabricate checks.jsonl. With complete content evidence, use verify/report. Both use templates/weekly_report.md, sections01–06; full details stay tabular. Preserve user-kept rows unless further selection is requested. Do not infer trends from similar titles or one snapshot.

Use export for optional Word output. Automatic PDF requires LibreOffice; if missing, a supported Word export may be used with actual render inspection. Do not claim unrun PDF conversion or publish Google Docs by default.

## Local data and maintenance

Save all raw observations, reviews, run outputs and finished reports under the existing local data/YYYY/MMDD or frozen-run paths. The entire data directory is Git-ignored and must not be uploaded when synchronizing code. Preserve local files, user deletions and frozen manifests; viewer structure stays unchanged. Never commit cookies, tokens, browser sessions or scratch work. Repository maintenance follows AGENTS.md; update references rather than keeping obsolete command aliases.
