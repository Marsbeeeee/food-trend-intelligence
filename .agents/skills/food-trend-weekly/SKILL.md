---
name: food-trend-weekly
description: Discover overseas tough-persona bread-making benchmark accounts on Instagram, TikTok and YouTube, assemble candidate lists, record human selection and compare ordinary versus high-performing videos only after account selection.
---

Read [workflow](../../../docs/workflow.md), [collection](../../../docs/collection.md) and [usage](../../../docs/usage.md). Follow repository AGENTS.md. Use run.py only; do not restore retired video-first commands.

## Discover accounts

Read current config/collection.json. Search Instagram, TikTok and YouTube in configured order; use platform search, public search indexes and verified creator links. Record actual queries and sources. Apply no follower/view threshold or automatic low-view exclusion.

Initialize an explicit archive date with accounts init; use the user's date or current date in their timezone. Read existing accounts and the frozen config_snapshot.json before resuming. Do not clear records or rewrite an existing snapshot.

Inspect profiles and multiple posts to establish tough persona and sustained bread making. Separate direct, adjacent and unverified candidates. Preserve search_only when profile access is unavailable; never label an indexed snippet as a watched video. Preserve missing counters as null with reason and approximate displays unchanged.

Associate cross-platform creator IDs only with identity evidence on every linked account. Keep each platform account separately. Write accounts.jsonl according to [data format](../../../docs/data_format.md), validate, and generate an accounts report to a fresh output folder.

Stop after delivering the candidate list unless the user requests the next stage. Do not automatically choose accounts or start bulk video analysis.

## Human selection and later comparison

Record explicit selection with reasons in reviews.jsonl. Require observed profiles before selected. Accept only videos from selected accounts.

Collect consecutive daily samples separately from historical high performers; document sampling, publication age, pinned posts, paid collaborations and exceptions. Keep YouTube Shorts and long videos separate. Preserve observed URLs, author evidence, timestamps and metric precision.

Record content_evidence only after watching originals or reading reliable transcripts. State when transcripts cannot establish visuals. Do not infer content from title or cover alone. Assign ordinary/high groups with human reasons; run videos validate and videos compare, without ad hoc ranking algorithms.

Review the generated comparison draft, cite original evidence, distinguish observations from inference, and keep suggestions limited. Never claim causation or growth from cumulative snapshots.

## Persistence and delivery

Keep all real observations, reviews, snapshots and reports under Git-ignored data/. Preserve historical files and viewer structure. The existing viewer accepts old video records, not new account JSONL; use the new Markdown tables for account review.

Use export for optional Word output; automatic PDF requires LibreOffice. Check actual rendering before claiming an export complete. Never commit cookies, API keys, browser sessions or data/.

