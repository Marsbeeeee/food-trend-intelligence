"""Date archives and resumable bookkeeping; this module never opens a browser."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

from pipeline.browser_records import approximate_display, completeness_errors

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    'dy': ('douyin', 'douyin_original.jsonl', 'douyin.com'),
    'xhs': ('xiaohongshu', 'xiaohongshu_original.jsonl', 'xiaohongshu.com'),
    'bili': ('bilibili', 'bilibili_original.jsonl', 'bilibili.com'),
}


def archive_folder(data_root, archive_date):
    parsed = date.fromisoformat(archive_date)
    if parsed.isoformat() != archive_date:
        raise ValueError('Use an explicit archive date: YYYY-MM-DD')
    return Path(data_root) / f'{parsed:%Y}' / f'{parsed:%m%d}'


def read_rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def atomic_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def record_errors(record, short, policy):
    if not isinstance(record, dict):
        return ['not_object']
    if not isinstance(record.get('metrics_display', {}), dict):
        return ['invalid_metrics_display']
    platform, _, domain = PLATFORMS[short]
    errors = completeness_errors({'source_platform': platform, 'raw_record': record}, policy)
    for name in ('url', 'source_url'):
        try:
            value = record.get(name) if isinstance(record.get(name), str) else ''
            host = urlsplit(value).hostname or ''
        except ValueError:
            return sorted(set(errors + ['invalid_' + name]))
        if host != domain and not host.endswith('.' + domain):
            errors.append('wrong_platform_' + name)
    url = urlsplit(record.get('url') if isinstance(record.get('url'), str) else '')
    pattern = {'dy': r'/video/(\d+)', 'xhs': r'/(?:explore|search_result)/([^/]+)', 'bili': r'/video/(BV[^/]+)'}[short]
    match = re.search(pattern, url.path)
    observed_id = match.group(1) if match else None
    if short == 'dy':
        observed_id = parse_qs(url.query).get('modal_id', [observed_id])[0]
    if observed_id != record.get('content_id'):
        errors.append('url_content_id_mismatch')
    conditions = record.get('search_conditions')
    if not isinstance(conditions, dict) or not str(conditions.get('sort') or '').strip():
        errors.append('missing_actual_search_conditions')
    metrics = record.get('metrics') if isinstance(record.get('metrics'), dict) else {}
    displays = record.get('metrics_display') if isinstance(record.get('metrics_display'), dict) else {}
    for key, display in displays.items():
        value = metrics.get(key)
        if approximate_display(display) and value is not None:
            errors.append('approximation_saved_as_exact_' + key)
        if isinstance(display, str) and display.strip().isdigit() and value is not None and int(display) != value:
            errors.append('metric_display_mismatch_' + key)
    return sorted(set(errors))


class Collection:
    def __init__(self, data_root, archive_date, policy):
        self.folder = archive_folder(data_root, archive_date)
        self.state_folder = Path(data_root) / 'collection_state' / archive_date
        self.date = archive_date
        self.policy = policy

    def path(self, short):
        return self.folder / PLATFORMS[short][1]

    def state_path(self, short):
        return self.state_folder / (short + '.json')

    @contextmanager
    def locked(self, short):
        self.state_folder.mkdir(parents=True, exist_ok=True)
        path = self.state_folder / (short + '.lock')
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise ValueError('This platform is already being written. Check the other process; do not remove a live lock.')
        try:
            os.close(fd)
            yield
        finally:
            path.unlink()

    def save_state(self, short, state):
        atomic_text(self.state_path(short), json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def load_state(self, short):
        path = self.state_path(short)
        if not path.exists():
            raise ValueError('Run collection.py init for this archive date first')
        return json.loads(path.read_text(encoding='utf-8'))

    def checked_rows(self, short, policy):
        records = read_rows(self.path(short))
        seen = set()
        for number, record in enumerate(records, 1):
            errors = record_errors(record, short, policy)
            content_id = record.get('content_id') if isinstance(record, dict) else None
            if isinstance(content_id, str) and content_id in seen:
                errors.append('duplicate_content_id')
            if errors:
                raise ValueError(f'Existing archive {short} line {number}: {errors}; source left unchanged')
            seen.add(content_id)
        if len(records) > policy['collection']['target_complete_per_platform']:
            raise ValueError('Existing archive exceeds configured platform quota; source left unchanged')
        return records

    def init(self, target=None):
        for short in PLATFORMS:
            with self.locked(short):
                path = self.state_path(short)
                if path.exists():
                    state = self.load_state(short)
                    if any(state['policy'][section] != self.policy[section] for section in ('collection', 'completeness')):
                        raise ValueError('This date has a frozen collection policy; resume with that policy rather than silently changing it')
                else:
                    records = self.checked_rows(short, self.policy)
                    state = {'archive_date': self.date, 'policy': self.policy, 'target': self.policy['collection']['target_complete_per_platform'],
                             'baseline_records': len(records), 'prior_attempts_known': not records,
                             'attempts': [], 'rejected_records': 0, 'failure_reasons': {}}
                if target is not None:
                    if not 1 <= target <= self.policy['collection']['target_complete_per_platform']:
                        raise ValueError('Target must be positive and at most the configured platform quota')
                    if target < len(read_rows(self.path(short))):
                        raise ValueError('Cannot reduce target below already archived records')
                    state['target'] = target
                if not self.path(short).exists():
                    atomic_text(self.path(short), '')
                self.save_state(short, state)
        return self.status()

    def attempt(self, short, key, keyword, retry=False):
        with self.locked(short):
            state = self.load_state(short)
            policy = state['policy']
            records = self.checked_rows(short, policy)
            if len(records) >= state['target']:
                raise ValueError('Platform target already reached; do not open more details')
            if not state['prior_attempts_known']:
                raise ValueError('Old partial archive has no attempt history. Restore its local checkpoint before resuming; do not reset the attempt budget')
            if keyword not in policy['collection']['keywords']:
                raise ValueError('Keyword is not configured')
            if not isinstance(key, str) or not key.strip():
                raise ValueError('Use a stable observed card URL or keyword/title/author key')
            if any(item['key'] == key for item in state['attempts']) and not retry:
                return {'status': 'already_attempted', 'open_detail': False}
            if len(state['attempts']) >= policy['collection']['max_detail_attempts_per_platform']:
                raise ValueError('Attempt limit reached; stop this platform')
            state['attempts'].append({'key': key, 'keyword': keyword, 'at': datetime.now(timezone.utc).isoformat()})
            self.save_state(short, state)
            return {'status': 'registered', 'open_detail': True, 'attempts': len(state['attempts'])}

    def append(self, short, batch):
        with self.locked(short):
            state = self.load_state(short)
            policy = state['policy']
            if not isinstance(batch, list) or not 1 <= len(batch) <= policy['collection']['batch_size']:
                raise ValueError('Supply one batch within the configured batch_size')
            records = self.checked_rows(short, policy)
            seen = {record['content_id'] for record in records}
            accepted, discarded, duplicates = [], Counter(), 0
            rejected = 0
            for record in batch:
                errors = record_errors(record, short, policy)
                if errors:
                    rejected += 1
                    discarded.update(errors)
                    continue
                if record['content_id'] in seen:
                    duplicates += 1
                    continue
                if len(records) + len(accepted) >= state['target']:
                    raise ValueError('Batch exceeds platform target; source left unchanged')
                accepted.append(record)
                seen.add(record['content_id'])
            available = len(state['attempts']) - (len(records) - state['baseline_records']) - state['rejected_records']
            if len(accepted) + rejected > available:
                raise ValueError('Register each detail attempt before opening it; no records written')
            if accepted:
                original = self.path(short).read_text(encoding='utf-8')
                if original and not original.endswith('\n'):
                    original += '\n'
                atomic_text(self.path(short), original + ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in accepted))
            state['rejected_records'] += rejected
            state['failure_reasons'] = dict(Counter(state['failure_reasons']) + discarded)
            self.save_state(short, state)
            return {'added': len(accepted), 'duplicates': duplicates, 'discarded': rejected, 'discard_reasons': dict(discarded), 'total': len(records) + len(accepted)}

    def reject(self, short, reason):
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', reason):
            raise ValueError('Use a short reason code, e.g. missing_comments or detail_timeout')
        with self.locked(short):
            state = self.load_state(short)
            records = self.checked_rows(short, state['policy'])
            available = len(state['attempts']) - (len(records) - state['baseline_records']) - state['rejected_records']
            if available < 1:
                raise ValueError('No unresolved registered attempt to reject')
            state['rejected_records'] += 1
            state['failure_reasons'][reason] = state['failure_reasons'].get(reason, 0) + 1
            self.save_state(short, state)

    def status(self, include_ids=False):
        result = {'archive_date': self.date, 'archive_folder': str(self.folder), 'platforms': {}}
        for short in PLATFORMS:
            state = self.load_state(short) if self.state_path(short).exists() else None
            policy = state['policy'] if state else self.policy
            records = self.checked_rows(short, policy)
            target = state['target'] if state else policy['collection']['target_complete_per_platform']
            result['platforms'][short] = {'file': str(self.path(short)), 'complete_records': len(records), 'target': target,
                'remaining': max(0, target - len(records)), 'keywords': dict(Counter(r['keyword'] for r in records)),
                'attempts': len(state['attempts']) if state and state['prior_attempts_known'] else None,
                'attempt_limit': policy['collection']['max_detail_attempts_per_platform'],
                'failure_reasons': state['failure_reasons'] if state else {},
                'actual_sorts': dict(Counter(str(r['search_conditions'].get('sort')) for r in records))}
            if include_ids:
                result['platforms'][short]['saved_ids'] = [r['content_id'] for r in records]
                result['platforms'][short]['attempted_keys'] = [item['key'] for item in state['attempts']] if state else []
        result['status'] = 'complete' if all(p['remaining'] == 0 for p in result['platforms'].values()) else 'partial'
        return result


def discover_inputs(input_root, shorts):
    """Read either the date archive or an explicit legacy platform directory."""
    inputs = []
    for short in shorts:
        platform, filename, _ = PLATFORMS[short]
        archive = input_root / filename
        legacy = sorted((input_root / short).rglob('*.jsonl'))
        if archive.exists() and legacy:
            raise ValueError('Ambiguous mixed archive/legacy inputs for ' + short)
        found = [archive] if archive.exists() else legacy
        if not found:
            raise ValueError('Missing ' + filename + '; resolve collection first')
        inputs.extend((path, short, platform) for path in found)
    return inputs


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'status', 'attempt', 'append', 'reject', 'audit'])
    parser.add_argument('--date', required=True, help='Archive date YYYY-MM-DD, not video publication or report period')
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--policy', type=Path, default=ROOT / 'config/discovery_policy.json')
    parser.add_argument('--target', type=int)
    parser.add_argument('--platform', choices=PLATFORMS)
    parser.add_argument('--batch', type=Path)
    parser.add_argument('--keyword')
    parser.add_argument('--key')
    parser.add_argument('--retry', action='store_true')
    parser.add_argument('--reason')
    parser.add_argument('--show-ids', action='store_true')
    args = parser.parse_args()
    try:
        collection = Collection(args.data_root, args.date, json.loads(args.policy.read_text(encoding='utf-8')))
        if args.command == 'init':
            result = collection.init(args.target)
        elif args.command in ('status', 'audit'):
            result = collection.status(args.show_ids)
        else:
            if not args.platform:
                raise ValueError('--platform required')
            if args.command == 'attempt':
                result = collection.attempt(args.platform, args.key, args.keyword, args.retry)
            elif args.command == 'append':
                if not args.batch:
                    raise ValueError('--batch required')
                text = args.batch.read_text(encoding='utf-8')
                batch = json.loads(text) if text.lstrip().startswith('[') else [json.loads(line) for line in text.splitlines() if line.strip()]
                result = collection.append(args.platform, batch)
            else:
                collection.reject(args.platform, args.reason or '')
                result = collection.status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
