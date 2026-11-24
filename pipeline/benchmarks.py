"""Local account review and video comparison; never browses or logs in."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from statistics import median
from urllib.parse import urlsplit, parse_qs

from pipeline.metrics import observe_metric
from pipeline.paths import ROOT


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def stamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return value


def text_field(row, key):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing text field: ' + key)
    return value.strip()


def platform_url(value, platform, profile=False):
    url = urlsplit(value)
    host = (url.hostname or '').lower()
    domains = {'instagram': ('instagram.com',), 'tiktok': ('tiktok.com',), 'youtube': ('youtube.com', 'youtu.be')}
    if url.scheme != 'https' or url.username or url.password or not any(host == d or host.endswith('.' + d) for d in domains[platform]):
        raise ValueError('Expected HTTPS URL for ' + platform)
    parts = url.path.strip('/').split('/')
    if profile:
        valid = ((platform == 'instagram' and len(parts) == 1 and bool(parts[0]) and parts[0] not in ('p', 'reel', 'reels', 'explore', 'accounts'))
                 or (platform == 'tiktok' and len(parts) == 1 and len(parts[0]) > 1 and parts[0].startswith('@'))
                 or (platform == 'youtube' and host != 'youtu.be' and
                     ((len(parts) == 1 and len(parts[0]) > 1 and parts[0].startswith('@')) or
                      (parts[0] in ('channel', 'c', 'user') and len(parts) == 2 and bool(parts[1])))))
        if not valid:
            raise ValueError('Expected creator profile URL')
    return value


def validate_account(original, config):
    row = dict(original)
    platform = row.get('platform')
    if platform not in config['platforms']:
        raise ValueError('Unsupported platform')
    for key in ('creator_id', 'display_name', 'handle', 'profile_url', 'source_url', 'discovery_query', 'persona_evidence', 'bread_evidence'):
        text_field(row, key)
    platform_url(row['profile_url'], platform, profile=True)
    profile_path = urlsplit(row['profile_url']).path.strip('/').split('/')
    profile_handle = profile_path[-1].lstrip('@').lower()
    if row['handle'].strip().lstrip('@').lower() != profile_handle:
        raise ValueError('handle must match profile URL')
    if urlsplit(row['source_url']).scheme != 'https':
        raise ValueError('source_url must be HTTPS')
    stamp(text_field(row, 'captured_at'))
    if row.get('fit') not in ('direct', 'adjacent', 'unverified'):
        raise ValueError('fit must be direct, adjacent or unverified')
    if row.get('verification') not in ('profile_observed', 'search_only'):
        raise ValueError('verification must be profile_observed or search_only')
    row['followers_observation'] = observe_metric(row.get('followers'), row.get('followers_display'))
    if row['followers_observation']['kind'] == 'missing':
        text_field(row, 'followers_missing_reason')
    row['account_id'] = platform + ':' + row['handle'].strip().lstrip('@').lower()
    return row


def validate_accounts(source, config):
    result, ids, creators = [], set(), {}
    for original in source:
        row = validate_account(original, config)
        if row['account_id'] in ids:
            raise ValueError('Duplicate account: ' + row['account_id'])
        ids.add(row['account_id'])
        creators.setdefault(row['creator_id'], []).append(row)
        result.append(row)
    for group in creators.values():
        if len(group) > 1 and not all(isinstance(r.get('identity_evidence'), str) and r['identity_evidence'].strip() for r in group):
            raise ValueError('Shared creator_id requires identity_evidence on every linked account')
    return result


def validate_reviews(source, accounts):
    by_id = {a['account_id']: a for a in accounts}
    result = {}
    for row in source:
        account_id = row.get('account_id')
        if account_id not in by_id or account_id in result:
            raise ValueError('Unknown or duplicate review account_id')
        if row.get('decision') not in ('selected', 'reserve', 'rejected', 'pending'):
            raise ValueError('Invalid review decision')
        text_field(row, 'reason')
        stamp(text_field(row, 'reviewed_at'))
        if row['decision'] == 'selected' and by_id[account_id]['verification'] != 'profile_observed':
            raise ValueError('Verify profile before selecting account')
        result[account_id] = row
    return result


def video_identity(url, platform):
    platform_url(url, platform)
    parsed = urlsplit(url)
    patterns = {'instagram': r'^/(?:reel|p)/([^/]+)/?$', 'tiktok': r'^/@[^/]+/video/(\d+)/?$', 'youtube': r'^/shorts/([^/]+)/?$'}
    match = re.match(patterns[platform], parsed.path)
    if match:
        return match[1]
    if platform == 'youtube':
        if parsed.hostname == 'youtu.be' and len(parsed.path.strip('/').split('/')) == 1 and parsed.path.strip('/'):
            return parsed.path.strip('/')
        if parsed.path == '/watch' and parse_qs(parsed.query).get('v'):
            return parse_qs(parsed.query)['v'][0]
    raise ValueError('Expected original video permalink')


def validate_videos(source, accounts, reviews):
    by_id = {a['account_id']: a for a in accounts}
    seen, result = set(), []
    for original in source:
        row = dict(original)
        account = by_id.get(row.get('account_id'))
        if account is None or reviews.get(row['account_id'], {}).get('decision') != 'selected':
            raise ValueError('Videos require a selected account')
        platform = account['platform']
        content_id = video_identity(text_field(row, 'url'), platform)
        key = (platform, content_id)
        if key in seen:
            raise ValueError('Duplicate video')
        seen.add(key)
        row.update(platform=platform, creator_id=account['creator_id'], content_id=content_id)
        for name in ('title', 'author_evidence', 'sample_reason'):
            text_field(row, name)
        stamp(text_field(row, 'captured_at'))
        if row.get('published_at') is not None:
            stamp(row['published_at'])
        if row.get('format') not in ('short', 'long') or (platform != 'youtube' and row['format'] != 'short'):
            raise ValueError('Invalid video format')
        if type(row.get('baseline_sample')) is not bool:
            raise ValueError('baseline_sample must be explicit boolean')
        if row.get('content_group') not in ('ordinary', 'high', 'unassigned'):
            raise ValueError('Invalid content_group')
        row['views_observation'] = observe_metric(row.get('views'), row.get('views_display'))
        if row['views_observation']['kind'] == 'missing':
            text_field(row, 'views_missing_reason')
        if row['content_group'] != 'unassigned':
            text_field(row, 'group_reason')
        evidence = row.get('content_evidence')
        if evidence is not None:
            if not isinstance(evidence, dict) or evidence.get('method') not in ('watched', 'transcript'):
                raise ValueError('Invalid content evidence')
            for name in ('reference', 'bread', 'persona', 'opening', 'presentation'):
                text_field(evidence, name)
        result.append(row)
    return result


def compare(videos, policy):
    groups = {}
    for row in videos:
        key = (row['account_id'], row['platform'], row['format'])
        groups.setdefault(key, []).append(row)
    result = []
    for key, group in sorted(groups.items()):
        baseline = [v['views_observation']['comparison_value'] for v in group
                    if v['baseline_sample'] and v['views_observation']['comparison_value'] is not None]
        enough = len(baseline) >= policy['minimum_numeric_sample']
        center = median(baseline) if enough else None
        result.append({'account_id': key[0], 'creator_id': group[0]['creator_id'], 'platform': key[1], 'format': key[2], 'baseline_count': len(baseline),
                       'baseline_median': center, 'status': 'ready' if center and enough else 'insufficient_or_zero_baseline',
                       'videos': [{**v, 'relative_views': v['views_observation']['comparison_value'] / center
                                   if center and v['views_observation']['comparison_value'] is not None else None} for v in group]})
    return result


def cell(value):
    if value is None or value == '':
        return '未见／待补'
    return str(value).replace('\\', '\\\\').replace('|', '\\|').replace('\r', ' ').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;').replace('[', '\\[').replace(']', '\\]')


def link(url):
    safe = url.replace('>', '%3E').replace('<', '%3C').replace('\n', '').replace('\r', '').replace(' ', '%20').replace('(', '%28').replace(')', '%29')
    return '[打开](' + safe + ')'


def render_accounts(accounts, reviews, template):
    header = '| 人物ID | 平台 | 账号 | 主页 | 粉丝快照 | 匹配度 | 人设依据 | 面包依据 | 核验 | 决定／理由 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
    lines = [header]
    for a in accounts:
        review = reviews.get(a['account_id'], {'decision': 'pending', 'reason': '待人工选择'})
        values = [a['creator_id'], a['platform'], a['display_name'], None, a['followers_observation']['display'],
                  a['fit'], a['persona_evidence'], a['bread_evidence'], a['verification'], review['decision'] + ' / ' + review['reason']]
        cells = [cell(v) for v in values]
        cells[3] = link(a['profile_url'])
        lines.append('| ' + ' | '.join(cells) + ' |')
    return template.replace('{{account_count}}', str(len(accounts))).replace('{{creator_count}}', str(len({a['creator_id'] for a in accounts}))).replace('{{account_table}}', '\n'.join(lines))


def render_comparison(groups, template):
    sections = []
    for g in groups:
        lines = [f"### {cell(g['creator_id'])} / {cell(g['account_id'])} / {g['format']}", '',
                 f"基线样本：{g['baseline_count']}；播放中位数：{cell(g['baseline_median'])}；状态：{g['status']}。", '',
                 '| 视频 | 分组／理由 | 播放快照 | 相对基线 | 面包内容 | 人设呈现 | 开头 | 拍摄表达 | 内容证据 |',
                 '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for v in g['videos']:
            e = v.get('content_evidence') or {}
            ratio = f"约 {v['relative_views']:.2f} 倍" if v['relative_views'] is not None else None
            values = [None, v['content_group'] + ' / ' + v.get('group_reason', '待判定'), v['views_observation']['display'],
                      ratio, e.get('bread'), e.get('persona'), e.get('opening'), e.get('presentation'), e.get('reference')]
            cells = [cell(x) for x in values]
            cells[0] = cell(v['title']) + ' ' + link(v['url'])
            lines.append('| ' + ' | '.join(cells) + ' |')
        lines.extend(['', '| 视频 | 快照时间 | 发布时间 | 基线样本／采样理由 |',
                      '| --- | --- | --- | --- |'])
        for v in g['videos']:
            values = [v['title'], v['captured_at'], v.get('published_at'),
                      str(v['baseline_sample']) + ' / ' + v['sample_reason']]
            lines.append('| ' + ' | '.join(cell(x) for x in values) + ' |')
        sections.append('\n'.join(lines))
    return template.replace('{{comparison_sections}}', '\n\n'.join(sections) or '尚无视频样本。')


def initialize(folder, archive_date):
    parsed = date.fromisoformat(archive_date)
    if parsed.isoformat() != archive_date:
        raise ValueError('Use YYYY-MM-DD')
    target = Path(folder) / f'{parsed:%Y}' / f'{parsed:%m%d}' / 'benchmarks'
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / 'config_snapshot.json'
    if not manifest.exists():
        config = {name: read(ROOT / 'config' / (name + '.json')) for name in ('collection', 'screening', 'report')}
        config['created_at'] = datetime.now(timezone.utc).isoformat()
        save_new(manifest, config)
    for name in ('accounts.jsonl', 'reviews.jsonl', 'videos.jsonl'):
        if not (target / name).exists():
            save_new(target / name, '')
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest='kind', required=True)
    for kind in ('accounts', 'videos'):
        stage = stages.add_parser(kind)
        stage.add_argument('action', choices=['init', 'validate', 'report'] if kind == 'accounts' else ['validate', 'compare'])
        stage.add_argument('--date', help='Explicit archive date YYYY-MM-DD (init only)')
        stage.add_argument('--data-root', type=Path, default=ROOT / 'data')
        stage.add_argument('--folder', type=Path, help='Existing benchmarks archive folder')
        stage.add_argument('--output', type=Path, help='Fresh output folder, outside source archive')
    args = parser.parse_args(argv)
    try:
        if args.action == 'init':
            if not args.date:
                parser.error('init requires --date')
            print(initialize(args.data_root, args.date))
            return
        if args.folder is None:
            parser.error('--folder is required')
        config = read(args.folder / 'config_snapshot.json')
        accounts = validate_accounts(rows(args.folder / 'accounts.jsonl'), config['collection'])
        reviews = validate_reviews(rows(args.folder / 'reviews.jsonl'), accounts)
        videos = validate_videos(rows(args.folder / 'videos.jsonl'), accounts, reviews) if args.kind == 'videos' else []
        summary = {'accounts': len(accounts), 'creators': len({a['creator_id'] for a in accounts}),
                   'selected': sum(r['decision'] == 'selected' for r in reviews.values()), 'videos': len(videos)}
        if args.action != 'validate':
            if args.output is None:
                parser.error('--output is required')
            source, output = args.folder.resolve(), args.output.resolve()
            if source == output or source in output.parents or output in source.parents:
                parser.error('Output must be separate from source archive')
            if args.kind == 'accounts':
                template = (ROOT / config['report']['account_template']).read_text(encoding='utf-8')
                rendered = render_accounts(accounts, reviews, template)
                extra = None
            else:
                extra = compare(videos, config['screening']['comparison'])
                template = (ROOT / config['report']['comparison_template']).read_text(encoding='utf-8')
                rendered = render_comparison(extra, template)
            args.output.mkdir(parents=True, exist_ok=False)
            for name in ('config_snapshot.json', 'accounts.jsonl', 'reviews.jsonl', 'videos.jsonl'):
                with (args.output / name).open('xb') as stream:
                    stream.write((args.folder / name).read_bytes())
            save_new(args.output / 'report.md', rendered)
            save_new(args.output / 'template.md', template)
            if extra is not None:
                save_new(args.output / 'comparison.json', extra)
            hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()}
            save_new(args.output / 'manifest.json', {'created_at': datetime.now(timezone.utc).isoformat(), 'summary': summary, 'sha256': hashes})
            summary['output'] = str(args.output)
        print(json.dumps(summary, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
