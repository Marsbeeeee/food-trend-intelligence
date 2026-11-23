"""Within-platform editorial shortlists, not causal quality or age-adjusted scores."""
from collections import Counter, defaultdict
import math

from pipeline.metrics import observe_metrics

LABELS = {'views': '播放', 'likes': '点赞', 'favorites': '收藏', 'coins': '投币', 'shares': '分享', 'comments': '评论'}
TIER_LABELS = {'multi_metric': '多项数据靠前', 'lower_bound_review': '数据模糊',
               'single_metric_backup': '一项数据靠前', 'not_highlighted': '未进入前列'}


def author_key(record):
    value = record.get('author_id')
    if value:
        return 'id:' + str(value), 'id'
    return 'name:' + (record.get('author_name') or '').strip().casefold(), 'name_only'


def prioritize(records, policy):
    cfg = policy['ranking']
    groups = defaultdict(list)
    for record in records:
        if record['decision'] in ('keep', 'review'):
            groups[record['platform']].append(record)
    selected, reserve, manual = [], [], []
    summary = {'method': 'multi_metric_sample_shortlist', 'platforms': {},
               'limitations': ['Cumulative snapshot only; no publication-age, exposure or account adjustment',
                               'Approximate displays support coarse ordering, not exact ranks or significance',
                               'Sample-relative thresholds are not platform-wide hit thresholds']}
    for platform, cohort in sorted(groups.items()):
        primary = cfg['platform_metrics'][platform]
        observations = {r['record_id']: observe_metrics(r['metrics'], r.get('metrics_display', {})) for r in cohort}
        distributions = {}
        for name in primary:
            values = [observations[r['record_id']][name]['comparison_value'] for r in cohort
                      if observations[r['record_id']][name]['comparison_value'] is not None]
            values.sort(reverse=True)
            size = len(values)
            slots = math.ceil(size * cfg['top_fraction']) if size >= cfg['min_cohort'] and len(set(values)) > 1 else 0
            distributions[name] = {'values': values, 'size': size, 'slots': slots,
                                   'cutoff': values[slots - 1] if slots else None}
        candidates = []
        non_highlighted = 0
        for record in cohort:
            obs = observations[record['record_id']]
            evidence, flags, hits, bounds = [], [], [], []
            if record['decision'] == 'review':
                flags.append('food_relevance_uncertain')
            for name in primary:
                observation, dist = obs[name], distributions[name]
                value, lower, cutoff = observation['comparison_value'], observation['lower_bound'], dist['cutoff']
                item = {'metric': name, **observation, 'cohort_size': dist['size'],
                        'coarse_sample_rank': None, 'sample_percentile': None,
                        'cutoff': cutoff, 'top_fraction_hit': False, 'boundary_tie': False}
                if observation['kind'] == 'lower_bound':
                    flags.append('lower_bound_' + name)
                    # A lower bound can warrant manual attention, but never counts as a ranked hit.
                    item['lower_bound_above_cutoff'] = cutoff is not None and lower > 0 and lower >= cutoff
                    if item['lower_bound_above_cutoff']:
                        bounds.append(name)
                elif value is not None and dist['slots']:
                    rank = 1 + sum(other > value for other in dist['values'])
                    item['coarse_sample_rank'] = rank
                    item['sample_percentile'] = (dist['size'] - rank + 1) / dist['size']
                    item['top_fraction_hit'] = value > 0 and rank <= dist['slots']
                    item['boundary_tie'] = value > 0 and value == cutoff and dist['values'].count(value) > 1
                    if item['top_fraction_hit']:
                        hits.append(name)
                    if item['boundary_tie']:
                        flags.append('cutoff_tie_' + name)
                evidence.append(item)
            if len(hits) >= cfg['min_primary_hits']:
                tier, tier_order = 'multi_metric', 0
            elif bounds and len(hits) + len(bounds) >= cfg['min_primary_hits']:
                tier, tier_order = 'lower_bound_review', 1
            elif hits:
                tier, tier_order = 'single_metric_backup', 2
            elif bounds:
                tier, tier_order = 'lower_bound_review', 3
            else:
                tier, tier_order = 'not_highlighted', 4
                non_highlighted += 1
            if record['decision'] == 'review':
                tier_order += 4
            key, quality = author_key(record)
            reasons = []
            if hits:
                reasons.append('样本主要指标前列：' + '、'.join(LABELS[n] for n in hits))
            if bounds:
                reasons.append('页面数值带“+”，具体数量不确定：' + '、'.join(LABELS[n] for n in bounds))
            if record['decision'] == 'review':
                reasons.append('标题相关性不确定，核验后再选例')
            item = {**record, 'metric_observations': obs, 'priority_tier': tier,
                    'priority_label': TIER_LABELS[tier],
                    'primary_hit_count': len(hits), 'primary_hits': hits,
                    'metric_evidence': evidence, 'review_flags': sorted(set(flags)),
                    'selection_reasons': reasons, 'author_key': key, 'author_identity_quality': quality,
                    'auxiliary_metrics': {name: obs[name] for name in cfg['supplemental_metrics']},
                    'status': 'review_priority_only'}
            if flags:
                manual.append(item)
            if tier != 'not_highlighted':
                best = max((e['sample_percentile'] or 0 for e in evidence), default=0)
                candidates.append(((tier_order, -len(hits), -best, record['record_id']), item))
        candidates.sort(key=lambda pair: pair[0])
        authors = Counter()
        platform_selected, platform_reserve = [], []
        for _, item in candidates:
            reason = None
            if item['priority_tier'] == 'single_metric_backup' and not cfg['fill_with_single_metric_backups']:
                reason = 'single_metric_backup'
            elif authors[item['author_key']] >= cfg['max_per_author']:
                reason = 'author_limit'
            elif len(platform_selected) >= cfg['max_candidates_per_platform']:
                reason = 'platform_shortlist_limit'
            if reason:
                platform_reserve.append({**item, 'not_selected_reason': reason})
            else:
                authors[item['author_key']] += 1
                platform_selected.append({**item, 'selection_order': len(platform_selected) + 1})
        selected.extend(platform_selected)
        reserve.extend(platform_reserve)
        summary['platforms'][platform] = {
            'eligible': len(cohort), 'selected': len(platform_selected),
            'reserve': len(platform_reserve), 'not_highlighted': non_highlighted,
            'selected_tiers': dict(Counter(item['priority_tier'] for item in platform_selected)),
            'metric_cohorts': {name: {k: v for k, v in dist.items() if k != 'values'} for name, dist in distributions.items()},
            'metric_precision': {name: dict(Counter(obs[name]['kind'] for obs in observations.values())) for name in primary},
            'author_identity_note': 'Prefer author_id; name-only groups may combine namesakes and require review',
        }
    selected_ids = {item['record_id'] for item in selected}
    manual = [{**item, 'in_priority_queue': item['record_id'] in selected_ids} for item in manual]
    return {'selected': selected, 'reserve': reserve, 'needs_review': manual, 'summary': summary}


def render_summary(priority, decisions, total):
    """Readable labels share one mapping with JSONL exports; no selection changes."""
    platforms = {'bilibili': 'B站', 'douyin': '抖音', 'xiaohongshu': '小红书'}
    lines = ['# 清洗与候选筛选结果', '',
             '本文件是待核验清单，不是正式周报；累计互动未按发布年龄、曝光量或账号规模校正。',
             f'输入 {total} 条；明确排除 {decisions.get("exclude", 0)} 条；相关性待确认 {decisions.get("review", 0)} 条。', '',
             '标签说明：多项数据靠前＝至少两项主要指标进入样本前20%；一项数据靠前＝单项突出，作为补充候选；数据模糊＝页面显示“10万+”等带“+”的数值，具体数量不确定，不是漏采字段。', '',
             '| 平台 | 多项数据靠前 | 数据模糊 | 一项数据靠前 | 优先核验合计 | 候补 | 未触发亮点规则 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for platform, stats in priority['summary']['platforms'].items():
        tiers = stats['selected_tiers']
        lines.append(f'| {platforms.get(platform, platform)} | {tiers.get("multi_metric", 0)} | {tiers.get("lower_bound_review", 0)} | {tiers.get("single_metric_backup", 0)} | {stats["selected"]} | {stats["reserve"]} | {stats["not_highlighted"]} |')
    lines += ['', '## 优先核验条目', '']
    for item in priority['selected']:
        label = TIER_LABELS[item['priority_tier']]
        lines.append(f'- {platforms.get(item["platform"], item["platform"])} / {item["selection_order"]} [{item["title"]}]({item["url"]}) — ' + '；'.join(item['selection_reasons']) + f'；标签：{label}。')
    lines += ['', '指标约数只支持粗排；“数据模糊”的记录没有精确排名。评论仅作辅助。作者无ID时按名称暂分组，同名情况须核验。未进入优先清单不表示内容没有价值；完整数据与候补仍可追溯。']
    return '\n'.join(lines) + '\n'

