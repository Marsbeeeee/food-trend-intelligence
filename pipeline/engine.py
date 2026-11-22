"""Reproducible fixture pipeline for MediaCrawler food-video exports (v1 MVP)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo


VERSION = "1.0.0"
SCHEMA = "1.0"
PLATFORMS = {"xhs": "xiaohongshu", "dy": "douyin", "bili": "bilibili"}
EXPECTED_RAW = {"xiaohongshu": 40, "douyin": 28, "bilibili": 39}
EXPECTED_BASELINE = {"xiaohongshu": 27, "douyin": 25, "bilibili": 10}
FOOD_TERMS = (
    "美食", "吃", "餐", "饭", "菜", "面", "饼", "肉", "鱼", "虾", "蛋", "甜品", "奶茶",
    "咖啡", "火锅", "烧烤", "小吃", "早餐", "夜市", "厨房", "烘焙", "点心", "饮料",
    "豆皮", "米粉", "牛排", "寿司", "料理", "卤味", "煎", "炒", "炖", "拌", "食谱",
)
META_TERMS = ("博主真实行情", "体验官招募", "博主吗", "拍照分享")
TOPIC_TERMS = {
    "home_cooking": ("家常", "做饭", "跟做", "拌饭", "拌面", "冷面", "菜谱", "食谱", "备餐", "下班回家"),
    "city_food_tour": ("逛吃", "探店", "吃透", "打卡", "街头", "小城", "本地", "旅行", "攻略"),
    "value_check": ("多少钱", "价格", "物价", "值不值", "分量", "菜量", "自助", "划算", "性价比", "对比"),
}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as stream:
        stream.write(data)
    os.replace(temp, path)


def write_json(path: Path, value: object) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    data = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    atomic_bytes(path, data.encode("utf-8"))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def from_epoch(value: object, *, milliseconds: bool, tz: ZoneInfo) -> tuple[str | None, str]:
    if value is None or value == "":
        return None, "missing"
    try:
        numeric = int(value)
        if numeric <= 0:
            return None, "ambiguous"
        timestamp = numeric / (1000 if milliseconds else 1)
        date = datetime.fromtimestamp(timestamp, tz)
        if not 2000 <= date.year <= 2100:
            return None, "ambiguous"
        return date.isoformat(), "parsed"
    except (ValueError, TypeError, OverflowError, OSError):
        return None, "ambiguous"


def metric(value: object) -> int | None:
    if value is None or str(value).strip() in ("", "None", "null"):
        return None
    text = str(value).strip().replace(",", "")
    try:
        if text.endswith("亿"):
            number = float(text[:-1]) * 100_000_000
        elif text.endswith("万"):
            number = float(text[:-1]) * 10_000
        else:
            number = float(text)
        if number < 0 or not number.is_integer():
            return None
        return int(number)
    except ValueError:
        return None


def clean_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def normalize(raw: dict, tz: ZoneInfo) -> dict:
    record = raw["raw_record"]
    platform = raw["source_platform"]
    if platform == "xiaohongshu":
        id_key, url_key, time_key, type_key = "note_id", "note_url", "time", "type"
        mapped_type = {"video": "video", "normal": "image_text"}.get(str(record.get(type_key)), "unknown")
        fields = {"views": None, "likes": "liked_count", "comments": "comment_count", "favorites": "collected_count", "shares": "share_count"}
        milliseconds = True
    elif platform == "douyin":
        id_key, url_key, time_key, type_key = "aweme_id", "aweme_url", "create_time", "aweme_type"
        mapped_type = "video" if str(record.get(type_key)) == "0" else "unknown"
        fields = {"views": None, "likes": "liked_count", "comments": "comment_count", "favorites": "collected_count", "shares": "share_count"}
        milliseconds = False
    else:
        id_key, url_key, time_key, type_key = "video_id", "video_url", "create_time", "video_type"
        mapped_type = "video" if record.get(type_key) == "video" else "unknown"
        fields = {"views": "video_play_count", "likes": "liked_count", "comments": "video_comment", "favorites": "video_favorite_count", "shares": "video_share_count"}
        milliseconds = False

    published, published_status = from_epoch(record.get(time_key), milliseconds=milliseconds, tz=tz)
    captured, _ = from_epoch(record.get("last_modify_ts"), milliseconds=True, tz=tz)
    source = raw["source_ref"]
    record_id = hashlib.sha256(f"{source['sha256']}:{source['line']}".encode()).hexdigest()[:20]
    metrics = {name: metric(record.get(field)) if field else None for name, field in fields.items()}
    content_id = clean_text(record.get(id_key))
    url = clean_text(record.get(url_key))
    return {
        "schema_version": SCHEMA,
        "record_id": record_id,
        "platform": platform,
        "content_id": content_id,
        "url": url,
        "content_type": mapped_type,
        "title": clean_text(record.get("title")),
        "description": clean_text(record.get("desc")),
        "author_id": clean_text(record.get("creator_hash")),
        "author_name": clean_text(record.get("nickname")),
        "published_at_raw": record.get(time_key),
        "published_at": published,
        "published_at_status": published_status,
        "captured_at": captured,
        "metrics": metrics,
        "source_keyword": clean_text(record.get("source_keyword")),
        "source_ref": source,
        "field_provenance": {
            "content_id": id_key,
            "url": url_key,
            "content_type": {"field": type_key, "mapping": mapped_type},
            "published_at": {"field": time_key, "unit": "milliseconds" if milliseconds else "seconds", "timezone": "Unix UTC epoch"},
            "captured_at": {"field": "last_modify_ts", "unit": "milliseconds", "meaning": "MediaCrawler store time"},
            "author_id": {"field": "creator_hash", "meaning": "MediaCrawler anonymized author hash"},
            "author_name": {"field": "nickname", "meaning": "MediaCrawler masked nickname"},
            "metrics": fields,
        },
    }


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def food_relevance(row: dict) -> str:
    text = (row.get("title") or "") + " " + (row.get("description") or "")
    if any(term in text for term in META_TERMS):
        return "uncertain"
    return "yes" if any(term in text for term in FOOD_TERMS) else "uncertain"


def main() -> None:
    project = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=project.parent / "weekly-pilot-2026-11-16_to_2026-11-22")
    parser.add_argument("--run-root", type=Path, default=project / "runs")
    parser.add_argument("--run-id", default="2026-11-16_2026-11-22_fixture_v1")
    parser.add_argument("--verification-overrides", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.config.read_text(encoding='utf-8'))
    run = args.run_root / args.run_id
    if run.exists():
        raise SystemExit(f"Run directory already exists: {run}")
    run.mkdir(parents=True)
    tz = ZoneInfo(settings["timezone"])
    window_start = datetime.fromisoformat(settings["window_start"])
    window_end = datetime.fromisoformat(settings["window_end"])
    cutoff = datetime.fromisoformat(settings["observation_cutoff"])
    events: list[dict] = []
    errors: list[dict] = []
    stages: list[dict] = []

    def event(stage: str, code: str, message: str, severity: str = "info", record_id: str | None = None) -> None:
        events.append({"run_id": args.run_id, "stage": stage, "timestamp": iso_now(), "severity": severity,
                       "record_id": record_id, "code": code, "message": message})

    def finish(stage: str, started: str, inputs: list[Path], outputs: list[Path], counts: dict) -> None:
        stages.append({"stage": stage, "status": "complete", "started_at": started, "finished_at": iso_now(),
                       "config_sha256": file_hash(run / "config.json"), "pipeline_version": VERSION,
                       "input_sha256": {str(p.relative_to(run)) if p.is_relative_to(run) else str(p): file_hash(p) for p in inputs},
                       "output_sha256": {str(p.relative_to(run)): file_hash(p) for p in outputs}, "counts": counts})
        write_json(run / "stage_manifest.json", {"schema_version": SCHEMA, "run_id": args.run_id, "stages": stages})
        event(stage, "stage_complete", f"{stage} complete")

    # Stage 1: immutable source copies and line-level wrappers.
    started = iso_now()
    source_files = []
    raw_rows = []
    raw_counts = Counter()
    for short, platform in PLATFORMS.items():
        files = sorted((args.input_root / short).rglob("*.jsonl"))
        if not files:
            raise SystemExit(f"Missing input JSONL for {platform}")
        for index, source in enumerate(files, start=1):
            destination = run / "source" / platform / (source.name if len(files) == 1 else f"{index}_{source.name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            source_sha = file_hash(source)
            if file_hash(destination) != source_sha:
                raise RuntimeError(f"Source copy hash mismatch: {source}")
            lines = source.read_bytes().splitlines()
            source_files.append({"platform": platform, "input_path": str(source.resolve()),
                                 "copied_path": str(destination.relative_to(run)).replace("\\", "/"),
                                 "sha256": source_sha, "line_count": len(lines)})
            raw_counts[platform] += len(lines)
            for line_number, line in enumerate(lines, start=1):
                ref = {"file": str(destination.relative_to(run)).replace("\\", "/"),
                       "line": line_number, "sha256": source_sha}
                try:
                    record = json.loads(line.decode("utf-8"))
                    if not isinstance(record, dict):
                        raise ValueError("JSONL line is not an object")
                except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
                    errors.append({"run_id": args.run_id, "stage": "discovery", "timestamp": iso_now(),
                                   "severity": "error", "record_id": None, "code": "invalid_source_line",
                                   "message": f"{type(exc).__name__}: {str(exc)[:120]}", "source_ref": ref})
                    continue
                discovered, _ = from_epoch(record.get("last_modify_ts"), milliseconds=True, tz=tz)
                raw_rows.append({"schema_version": SCHEMA, "source_platform": platform,
                                 "source_file": ref["file"], "source_line": line_number,
                                 "source_ref": ref, "discovered_at": discovered,
                                 "discovery_method": "MediaCrawler keyword search export",
                                 "query": clean_text(record.get("source_keyword")), "raw_record": record})
    mc_commit = subprocess.run(["git", "-C", str(project.parent.parent / "work" / "MediaCrawler"), "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=False).stdout.strip() or None
    configuration = {"schema_version": SCHEMA, "run_id": args.run_id, "pipeline_version": VERSION,
                     "pipeline_sha256": file_hash(Path(__file__)), "mediacrawler_commit": mc_commit,
                     "report_timezone": str(tz), "window_start": window_start.isoformat(),
                     "window_end_exclusive": window_end.isoformat(), "observation_cutoff": cutoff.isoformat(),
                     "inputs": source_files, "discovery_queries": ["美食", "探店"],
                     "discovery_scope": "one search result page per query and platform; frozen fixture, no re-crawl",
                     "filter_version": VERSION, "verification_overrides": str(args.verification_overrides) if args.verification_overrides else None,
                     "verification_overrides_sha256": file_hash(args.verification_overrides) if args.verification_overrides else None}
    write_json(run / "config.json", configuration)
    write_jsonl(run / "raw_candidates.jsonl", raw_rows)
    discovery = {"schema_version": SCHEMA, "run_id": args.run_id, "sources": source_files,
                 "raw_lines": dict(raw_counts), "parsed_lines": len(raw_rows), "parse_errors": len(errors),
                 "coverage": {p: "fixture_imported" for p in PLATFORMS.values()}}
    write_json(run / "discovery_manifest.json", discovery)
    if sum(raw_counts.values()) != len(raw_rows) + len(errors):
        raise RuntimeError("Discovery conservation failed")
    finish("discovery", started, [Path(s["input_path"]) for s in source_files],
           [run / "config.json", run / "raw_candidates.jsonl", run / "discovery_manifest.json"],
           {"input_lines": sum(raw_counts.values()), "parsed": len(raw_rows), "errors": len(errors)})

    # Stage 2: one standardized and one screened row per parsed source row.
    started = iso_now()
    normalized = [normalize(raw, tz) for raw in raw_rows]
    screened = []
    seen: dict[tuple[str, str], str] = {}
    baseline_seen: set[tuple[str, str]] = set()
    baseline = Counter()
    reasons = Counter()
    funnel = defaultdict(Counter)
    for row in normalized:
        platform = row["platform"]
        published = datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
        captured = datetime.fromisoformat(row["captured_at"]) if row["captured_at"] else None
        in_week = bool(published and window_start <= published < window_end and published <= cutoff)
        before_cutoff = bool(captured and captured <= cutoff)
        dedupe_value = row["content_id"] or canonical_url(row["url"])
        dedupe_key = (platform, dedupe_value) if dedupe_value else None
        if in_week and before_cutoff and dedupe_key and dedupe_key not in baseline_seen:
            baseline_seen.add(dedupe_key)
            baseline[platform] += 1
        food = food_relevance(row)
        reason_codes = []
        week_status = "unknown" if not published else ("in_window" if in_week else "out_of_window")
        if week_status == "out_of_window":
            reason_codes.append("published_outside_window_or_after_cutoff")
        elif week_status == "unknown":
            reason_codes.append("publication_time_unknown")
        if not captured:
            reason_codes.append("capture_time_unknown")
        elif not before_cutoff:
            reason_codes.append("captured_after_cutoff")
        if row["content_type"] == "image_text":
            reason_codes.append("not_video")
        elif row["content_type"] == "unknown":
            reason_codes.append("content_type_unknown")
        if food == "uncertain":
            reason_codes.append("food_relevance_uncertain")
        duplicate_of = seen.get(dedupe_key) if dedupe_key else None
        if dedupe_key and not duplicate_of:
            seen[dedupe_key] = row["record_id"]
        if duplicate_of:
            reason_codes.append("duplicate_content")
        if not dedupe_key:
            reason_codes.append("dedupe_key_missing")
        hard = {"published_outside_window_or_after_cutoff", "captured_after_cutoff", "not_video", "duplicate_content"}
        decision = "exclude" if hard.intersection(reason_codes) else ("pending" if reason_codes else "keep")
        screened.append({**row, "food_relevance": food, "week_status": week_status,
                         "dedupe_key": f"{platform}:{dedupe_value}" if dedupe_value else None,
                         "dedupe_confidence": "content_id" if row["content_id"] else ("url" if dedupe_value else "none"),
                         "duplicate_of": duplicate_of, "decision": decision,
                         "reason_codes": reason_codes, "filter_version": VERSION})
        funnel[platform][decision] += 1
        reasons.update(reason_codes)
    write_jsonl(run / "normalized_candidates.jsonl", normalized)
    write_jsonl(run / "screened_candidates.jsonl", screened)
    missing = {p: {field: sum(row[field] is None for row in normalized if row["platform"] == p)
                   for field in ("content_id", "url", "published_at", "captured_at", "author_id")}
               for p in PLATFORMS.values()}
    baseline_differences = {p: {"expected": EXPECTED_BASELINE[p], "actual": baseline[p]}
                            for p in PLATFORMS.values() if baseline[p] != EXPECTED_BASELINE[p]}
    summary = {"schema_version": SCHEMA, "run_id": args.run_id, "input_rows": len(raw_rows),
               "normalized_rows": len(normalized), "screened_rows": len(screened),
               "baseline_date_dedupe": dict(baseline), "baseline_differences": baseline_differences,
               "decision_counts": {p: dict(funnel[p]) for p in PLATFORMS.values()},
               "reason_counts": dict(reasons), "missing_field_counts": missing,
               "content_type_counts": dict(Counter(f"{r['platform']}:{r['content_type']}" for r in normalized))}
    write_json(run / "filter_summary.json", summary)
    if len(normalized) != len(raw_rows) or len(screened) != len(normalized):
        raise RuntimeError("Normalization conservation failed")
    finish("normalization_filtering", started, [run / "raw_candidates.jsonl"],
           [run / "normalized_candidates.jsonl", run / "screened_candidates.jsonl", run / "filter_summary.json"],
           {"processed": len(normalized), "decisions": dict(Counter(r["decision"] for r in screened))})

    # Stage 3: deterministic topic candidates; no growth inference from one snapshot.
    started = iso_now()
    groups = defaultdict(list)
    for row in screened:
        if row["decision"] != "keep":
            continue
        text = (row["title"] or "") + " " + (row["description"] or "")
        for topic, terms in TOPIC_TERMS.items():
            if any(term in text for term in terms):
                groups[topic].append(row)
    topics = []
    for topic, rows in sorted(groups.items()):
        authors = sorted({f"{r['platform']}:{r['author_id']}" for r in rows if r["author_id"]})
        platforms = sorted({r["platform"] for r in rows})
        topics.append({"topic_id": topic, "label": topic.replace("_", " "),
                       "classification": "emerging_pattern" if len(authors) >= 2 else "single_hit",
                       "case_record_ids": sorted(r["record_id"] for r in rows),
                       "independent_author_keys": authors, "platforms": platforms,
                       "evidence": {"candidate_count": len(rows), "independent_author_count": len(authors)},
                       "limitations": ["fixed keyword sample", "one metric snapshot", "external link and metric verification pending"],
                       "confidence": "low"})
    trend = {"schema_version": SCHEMA, "run_id": args.run_id, "topics": topics}
    write_json(run / "trend_candidates.json", trend)
    finish("trend_intelligence", started, [run / "screened_candidates.jsonl"],
           [run / "trend_candidates.json"], {"topics": len(topics), "eligible_rows": sum(r["decision"] == "keep" for r in screened)})

    # Stage 4: snapshot-only records stay partial until independent checks are logged.
    started = iso_now()
    overrides = {}
    if args.verification_overrides:
        for line in args.verification_overrides.read_text(encoding="utf-8").splitlines():
            if line.strip():
                override = json.loads(line)
                overrides[(override["platform"], str(override["content_id"]))] = override
    cases = []
    verification_log = []
    topic_by_record = defaultdict(list)
    for topic in topics:
        for record_id in topic["case_record_ids"]:
            topic_by_record[record_id].append(topic["topic_id"])
    for row in screened:
        if row["decision"] != "keep":
            continue
        found_metric = next(((name, value) for name, value in row["metrics"].items() if value is not None), None)
        override = overrides.get((row["platform"], row["content_id"]))
        fields = {name: "snapshot_only" for name in ("url", "published_at", "content_type", "food_relevance", "author", "metric")}
        if override:
            if override.get("evidence_source") == row["url"] and override.get("observed_title") == row["title"]:
                fields["url"] = "verified"
            if override.get("observed_content_type") == "video":
                fields["content_type"] = "verified"
            if fields["url"] == "verified" and any(term in (override.get("observed_title") or "") for term in FOOD_TERMS):
                fields["food_relevance"] = "verified"
            if override.get("observed_author_name") and override.get("observed_author_url", "").startswith("https://space.bilibili.com/"):
                fields["author"] = "verified"
            try:
                observed_time = datetime.fromisoformat(override["observed_published_at"])
                if observed_time.tzinfo and observed_time.astimezone(tz) == datetime.fromisoformat(row["published_at"]):
                    fields["published_at"] = "verified"
            except (KeyError, TypeError, ValueError):
                pass
            observed_metric = override.get("observed_metric") or {}
            if observed_metric.get("name") in row["metrics"] and observed_metric.get("value") == row["metrics"][observed_metric["name"]] and isinstance(observed_metric.get("value"), int):
                fields["metric"] = "verified"
                found_metric = (observed_metric["name"], observed_metric["value"])
        complete = bool(row["url"] and row["published_at"] and row["content_type"] == "video" and found_metric)
        verified = complete and all(value == "verified" for value in fields.values())
        status = "verified" if verified else ("partial" if complete else "pending")
        case = {"record_id": row["record_id"], "topic_ids": sorted(topic_by_record[row["record_id"]]),
                "verification_status": status, "verified_fields": fields, "source_url": row["url"],
                "metric_snapshot": {"name": found_metric[0], "value": found_metric[1],
                                    "captured_at": row["captured_at"]} if found_metric else None,
                "evidence_grade": "C" if verified else "D", "checked_at": override.get("checked_at") if override else None,
                "evidence_source": override.get("evidence_source") if override else None,
                "observed_published_at": override.get("observed_published_at") if override else None,
                "observed_metric": override.get("observed_metric") if override else None,
                "observed_author_name": override.get("observed_author_name") if override else None,
                "observed_author_url": override.get("observed_author_url") if override else None,
                "operator": override.get("operator") if override else None,
                "notes": override.get("notes") if override else "Export snapshot only; original link and fields not independently checked."}
        cases.append(case)
        verification_log.append({"schema_version": SCHEMA, "run_id": args.run_id, **case})
    verified_cases = {"schema_version": SCHEMA, "run_id": args.run_id, "cases": cases}
    write_json(run / "verified_cases.json", verified_cases)
    write_jsonl(run / "verification_log.jsonl", verification_log)
    finish("verification", started, [run / "trend_candidates.json", run / "screened_candidates.jsonl"] + ([args.verification_overrides] if args.verification_overrides else []),
           [run / "verified_cases.json", run / "verification_log.jsonl"],
           {"cases": len(cases), "status": dict(Counter(c["verification_status"] for c in cases))})

    # Stage 5: no unverified lead is promoted to a formal weekly case.
    started = iso_now()
    formal = [case for case in cases if case["verification_status"] == "verified"]
    lines = ["# 美食短视频热点情报周报（固定样本流程测试）", "",
             "**性质：**流程回归产物，不代表本周全平台热点。", "",
             f"**观察窗口：**{window_start.isoformat()} 至 {window_end.isoformat()}（结束时刻不含）。",
             f"**观察截止：**{cutoff.isoformat()}。", "",
             "## 样本范围与覆盖", "",
             "输入为 MediaCrawler 的固定 JSONL 导出；每个平台仅来自“美食”“探店”各一页搜索结果，未重新采集。", "",
             "| 平台 | 导出行 | 日期及 ID 去重基线 | 保留视频 | 排除 | 待核验 |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for platform in PLATFORMS.values():
        counts = funnel[platform]
        lines.append(f"| {platform} | {raw_counts[platform]} | {baseline[platform]} | {counts['keep']} | {counts['exclude']} | {counts['pending']} |")
    lines += ["", f"**正式核验案例：{len(formal)} 条。**目标为 20–30 条；本次不足时不降低核验标准。", "",
              "## 经核验案例", ""]
    if formal:
        by_id = {row["record_id"]: row for row in screened}
        for case in formal:
            row = by_id[case["record_id"]]
            metric_data = case["metric_snapshot"]
            metric_name = {"shares": "分享", "favorites": "收藏", "likes": "点赞", "comments": "评论", "views": "播放"}.get(metric_data["name"], metric_data["name"])
            lines.append(f"- [{row['title'] or row['content_id']}]({row['url']})：{row['platform']}，"
                         f"作者 [{case['observed_author_name']}]({case['observed_author_url']})；"
                         f"发布于 {row['published_at']}（原页显示 {case['observed_published_at']}）；"
                         f"{metric_name} {metric_data['value']} "
                         f"（导出快照 {metric_data['captured_at']}；原页核验 {case['checked_at']}）。")
    else:
        lines.append("无。导出快照已整理，但原链接、发布时间和指标尚未完成独立核验；候选内容不升格为正式案例。")
    lines += ["", "## 待核验与局限", "",
              f"- {sum(c['verification_status'] != 'verified' for c in cases)} 条保留视频仍为部分核验或待核验。",
              "- 关键词与每词一页的发现范围未经覆盖率评估；抓不到不等于没有热点。",
              "- 小红书图文已排除于短视频案例；平台间的播放、点赞等指标不合并排名。",
              "- 只有单次采集快照，不计算增长率，也不使用“本周升温”等措辞。",
              "- 本次原页核验发生在观察截止后；核验时部分指标已变动，报告仅引用与导出快照仍一致的单项指标。",
              "- 简单主题分组只是候选线索，固定搜索页样本不足以认定本周话题趋势。",
              "- 逐条决定、来源行、源文件哈希和字段映射见同目录的 JSONL 与清单。", ""]
    atomic_bytes(run / "weekly_report.md", ("\n".join(lines)).encode("utf-8"))
    report_manifest = {"schema_version": SCHEMA, "run_id": args.run_id, "pipeline_version": VERSION,
                       "formal_case_ids": [c["record_id"] for c in formal],
                       "evidence_grades": {c["record_id"]: c["evidence_grade"] for c in formal},
                       "input_sha256": {str(p.relative_to(run)): file_hash(p) for p in (run / "verified_cases.json", run / "filter_summary.json", run / "config.json")},
                       "report_sha256": file_hash(run / "weekly_report.md")}
    write_json(run / "report_manifest.json", report_manifest)
    finish("reporting", started, [run / "verified_cases.json", run / "filter_summary.json"],
           [run / "weekly_report.md", run / "report_manifest.json"], {"formal_cases": len(formal)})
    write_jsonl(run / "logs" / "events.jsonl", events)
    write_jsonl(run / "logs" / "errors.jsonl", errors)
    print(json.dumps({"run": str(run), "raw_lines": sum(raw_counts.values()),
                      "baseline": dict(baseline), "decisions": {p: dict(funnel[p]) for p in PLATFORMS.values()},
                      "formal_cases": len(formal), "baseline_differences": baseline_differences}, ensure_ascii=False))


if __name__ == "__main__":
    main()
